"""
secure_usage_store.py — Phase 2 tamper-evident backend for the trial token counter.

Medium-grade anti-tamper for small-community release. Defeats: editing settings.json,
deleting one store, copying another machine's file, backup-then-restore rollback.
Does NOT defeat: reverse-engineering the frozen exe to extract the embedded secret
(acceptable for this tier — Phase 3 would move enforcement server-side).

Mechanism:
  • Counter stored as a Fernet blob (AES-128-CBC + HMAC-SHA256) — encrypted (number
    hidden) AND authenticated (edits fail to verify).
  • Key = SHA256(embedded_app_secret + Windows MachineGuid) → a blob from machine A
    cannot decrypt on machine B (sharing a "fresh" file fails closed).
  • Dual store: a file in %LOCALAPPDATA%/MBB_Dalamud/.usage  AND  registry
    HKCU\\Software\\MBB_Dalamud\\u. Deleting one is healed from the other.
  • Anti-rollback: a monotonic `seq`; load() takes max(seq) across both stores, so
    restoring an old copy of one store is overridden by the newer one.
  • Fail-closed: if a store exists but nothing decrypts → status "tamper" (caller locks
    translation). Only a genuinely empty machine (no store anywhere) → status "fresh".

trial_limit is NOT stored here — it is a build-time constant in usage_tracker.py, so a
user cannot raise their own cap by editing any file.
"""
import os
import json
import base64
import hashlib
import logging

log = logging.getLogger("mbb")

try:
    from cryptography.fernet import Fernet, InvalidToken
    _HAVE_CRYPTO = True
except Exception:  # cryptography not bundled (dev env) → caller falls back to Phase 1
    _HAVE_CRYPTO = False

# Embedded app secret — obfuscated as two XOR halves so it is not a plaintext string
# in the binary. Regenerate for each public build if desired. This is the weakest link
# (extractable by a determined RE); medium tier accepts that.
_S1 = bytes([0x4d, 0x42, 0x42, 0x5f, 0x44, 0x6c, 0x6d, 0x64, 0x5f, 0x55, 0x73, 0x67, 0x5f, 0x76, 0x32, 0x21])
_S2 = bytes([0x37, 0x91, 0xa3, 0x5c, 0x1e, 0xc8, 0x44, 0x7b, 0x09, 0xd2, 0x6f, 0x33, 0xb5, 0x80, 0x12, 0xee])

_REG_PATH = r"Software\MBB_Dalamud"
_REG_VALUE = "u"
_FILE_NAME = ".usage"


def _app_secret() -> bytes:
    return bytes(a ^ b for a, b in zip(_S1, _S2))


def _machine_id() -> bytes:
    """Stable per-OS-install id (Windows MachineGuid). Falls back to a constant off-Windows."""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography"
        ) as k:
            guid, _ = winreg.QueryValueEx(k, "MachineGuid")
            return str(guid).encode()
    except Exception as e:
        log.debug(f"[usage] machine id fallback: {e}")
        return b"mbb-fallback-machine-id"


def _derive_key() -> bytes:
    digest = hashlib.sha256(_app_secret() + _machine_id()).digest()
    return base64.urlsafe_b64encode(digest)  # 32-byte → valid Fernet key


def _file_path() -> str:
    from resource_utils import get_user_data_dir
    return os.path.join(get_user_data_dir(), _FILE_NAME)


class SecureUsageStore:
    """Encrypted, machine-bound, dual-location counter store. status from load():
    'fresh' (no store anywhere), 'ok' (at least one store decrypts), 'tamper' (a store
    exists but none decrypt)."""

    def __init__(self):
        self.available = _HAVE_CRYPTO
        self._fernet = Fernet(_derive_key()) if _HAVE_CRYPTO else None
        self._seq = 0

    # ── crypto ──

    def _encrypt(self, data: dict) -> bytes:
        raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
        return self._fernet.encrypt(raw)

    def _decrypt(self, blob):
        if not blob:
            return None
        try:
            raw = self._fernet.decrypt(blob)
            return json.loads(raw.decode("utf-8"))
        except (InvalidToken, ValueError, Exception):
            return None  # wrong machine / edited / corrupt

    # ── file store ──

    def _read_file(self):
        try:
            with open(_file_path(), "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None
        except Exception as e:
            log.debug(f"[usage] file read failed: {e}")
            return None

    def _write_file(self, blob: bytes):
        try:
            path = _file_path()
            tmp = path + ".tmp"
            with open(tmp, "wb") as f:
                f.write(blob)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except Exception as e:
            log.warning(f"[usage] file write failed: {e}")

    # ── registry store ──

    def _read_reg(self):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH) as k:
                val, _ = winreg.QueryValueEx(k, _REG_VALUE)
                return bytes(val) if val else None
        except FileNotFoundError:
            return None
        except Exception as e:
            log.debug(f"[usage] reg read failed: {e}")
            return None

    def _write_reg(self, blob: bytes):
        try:
            import winreg
            k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, _REG_PATH)
            try:
                winreg.SetValueEx(k, _REG_VALUE, 0, winreg.REG_BINARY, blob)
            finally:
                winreg.CloseKey(k)
        except Exception as e:
            log.debug(f"[usage] reg write failed: {e}")

    # ── public ──

    def load(self):
        """Return (data_dict_or_None, status)."""
        if not self.available:
            return None, "fresh"

        fblob = self._read_file()
        rblob = self._read_reg()
        if fblob is None and rblob is None:
            return None, "fresh"

        fdata = self._decrypt(fblob)
        rdata = self._decrypt(rblob)
        datas = [d for d in (fdata, rdata) if isinstance(d, dict)]
        if not datas:
            # A store exists but nothing decrypts → tampered or different machine.
            return None, "tamper"

        best = max(datas, key=lambda d: int(d.get("seq", 0)))
        self._seq = int(best.get("seq", 0))
        return best, "ok"

    def save(self, data: dict):
        """Encrypt + write both stores with an incremented monotonic seq."""
        if not self.available:
            return
        payload = dict(data)
        self._seq += 1
        payload["seq"] = self._seq
        blob = self._encrypt(payload)
        self._write_file(blob)
        self._write_reg(blob)

    def clear(self):
        """Dev reset path — wipe both stores (e.g. after an OS reinstall changed the
        MachineGuid and falsely locked a legit user)."""
        try:
            os.remove(_file_path())
        except FileNotFoundError:
            pass
        except Exception as e:
            log.debug(f"[usage] file clear failed: {e}")
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE
            ) as k:
                winreg.DeleteValue(k, _REG_VALUE)
        except FileNotFoundError:
            pass
        except Exception as e:
            log.debug(f"[usage] reg clear failed: {e}")
        self._seq = 0
        log.info("[usage] secure store cleared (dev reset)")


if __name__ == "__main__":
    # Dev reset CLI:  python secure_usage_store.py --reset
    import sys
    logging.basicConfig(level=logging.INFO)
    if "--reset" in sys.argv:
        SecureUsageStore().clear()
        print("Secure usage store reset.")
    else:
        store = SecureUsageStore()
        data, status = store.load()
        print("available:", store.available, "status:", status, "data:", data)
