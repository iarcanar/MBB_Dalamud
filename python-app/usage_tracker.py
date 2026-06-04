"""
usage_tracker.py — Cumulative Gemini token usage tracking for the free-trial limit.

Counts ONLY real API calls (cache hits are excluded — they don't hit Gemini).

Two persistence backends, chosen automatically:
  • Phase 2 (secure): `secure_usage_store.SecureUsageStore` — Fernet-encrypted,
    machine-bound, dual-location (file + registry), anti-rollback, fail-closed.
    Used whenever the `cryptography` lib is importable (i.e. real builds).
  • Phase 1 (settings): plaintext `settings.json["usage_stats"]`. Fallback only when
    cryptography is unavailable (dev env without the lib).

trial_limit:
  In secure mode it is the build-time constant TRIAL_LIMIT (0 = unlimited) so a user
  cannot raise their own cap by editing a file. A dev-only env override
  MBB_TRIAL_LIMIT is honoured ONLY in non-frozen runs (ignored in a release exe).
  In settings mode the editable settings.json value applies (soft gate).

Persistence is debounced: flushed every FLUSH_EVERY recorded calls and once on app
exit (MBB.exit_program → flush()).
"""
import os
import sys
import time
import logging

log = logging.getLogger("mbb")

# Build-time trial cap in tokens. 0 = unlimited. Sourced from the central trial_config
# (set TRIAL_TOKEN_LIMIT there when packaging a trial build).
try:
    from trial_config import TRIAL_TOKEN_LIMIT as TRIAL_LIMIT
except Exception:
    TRIAL_LIMIT = 0


def _effective_trial_limit():
    # Dev-only override for testing; ignored in a frozen release so it can't be abused.
    if not getattr(sys, "frozen", False):
        env = os.environ.get("MBB_TRIAL_LIMIT")
        if env and env.isdigit():
            return int(env)
    return TRIAL_LIMIT


class UsageTracker:
    FLUSH_EVERY = 5

    def __init__(self, settings):
        self.settings = settings
        self._dirty = 0
        self.tampered = False
        self.trial_limit = _effective_trial_limit()

        # Prefer the secure (Phase 2) backend when cryptography is available.
        self._store = None
        try:
            from secure_usage_store import SecureUsageStore
            store = SecureUsageStore()
            if store.available:
                self._store = store
        except Exception as e:
            log.debug(f"[usage] secure store unavailable: {e}")

        if self._store is not None:
            self._init_secure()
        else:
            self._init_settings()

    # ── init helpers ──

    def _zero(self):
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_requests = 0
        self.per_model = {}
        self.first_use_at = None

    def _load_dict(self, d):
        self.total_tokens = int(d.get("total_tokens", 0))
        self.input_tokens = int(d.get("input_tokens", 0))
        self.output_tokens = int(d.get("output_tokens", 0))
        self.total_requests = int(d.get("total_requests", 0))
        self.per_model = dict(d.get("per_model", {}) or {})
        self.first_use_at = d.get("first_use_at")

    def _counters(self):
        return {
            "total_tokens": self.total_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_requests": self.total_requests,
            "per_model": self.per_model,
            "first_use_at": self.first_use_at,
        }

    def _init_secure(self):
        data, status = self._store.load()
        if status == "ok":
            self._load_dict(data)
        elif status == "tamper":
            self._zero()
            self.tampered = True
            log.warning("[usage] secure store tamper/foreign — translation locked (fail-closed)")
        else:  # "fresh" — migrate any Phase 1 plaintext counter, then own it securely
            self._zero()
            try:
                old = (self.settings.get("usage_stats", {}) or {}) if self.settings else {}
                if int(old.get("total_tokens", 0)) > 0:
                    self._load_dict(old)
                    log.info(f"[usage] migrated {self.total_tokens} tokens from settings.json")
            except Exception as e:
                log.debug(f"[usage] migration skipped: {e}")
            # Seed the secure store so subsequent launches load as "ok", not "fresh".
            self._store.save(self._counters())

    def _init_settings(self):
        stats = {}
        try:
            stats = (self.settings.get("usage_stats", {}) or {}) if self.settings else {}
        except Exception as e:
            log.warning(f"[usage] could not read usage_stats: {e}")
        self._load_dict(stats)
        # Soft-gate mode: the editable settings.json trial_limit applies.
        self.trial_limit = int(stats.get("trial_limit", self.trial_limit) or 0)

    # ── query ──

    def is_over_limit(self):
        if self.tampered:
            return True
        return self.trial_limit > 0 and self.total_tokens >= self.trial_limit

    def remaining(self):
        if self.tampered:
            return 0
        if self.trial_limit <= 0:
            return None
        return max(0, self.trial_limit - self.total_tokens)

    def snapshot(self):
        d = self._counters()
        d["trial_limit"] = self.trial_limit
        d["tampered"] = self.tampered
        return d

    # ── mutate ──

    def add(self, input_t, output_t, model):
        """Accumulate one real API call's token usage; debounced flush to backend."""
        input_t = int(input_t or 0)
        output_t = int(output_t or 0)
        total = input_t + output_t
        if total <= 0:
            return

        self.input_tokens += input_t
        self.output_tokens += output_t
        self.total_tokens += total
        self.total_requests += 1

        m = self.per_model.setdefault(model, {"tokens": 0, "requests": 0})
        m["tokens"] += total
        m["requests"] += 1

        if not self.first_use_at:
            self.first_use_at = time.strftime("%Y-%m-%dT%H:%M:%S")

        self._dirty += 1
        if self._dirty >= self.FLUSH_EVERY:
            self.flush()

    def flush(self):
        """Persist accumulated counters to the active backend (no-op if unchanged)."""
        if self._dirty == 0:
            return
        try:
            if self._store is not None:
                self._store.save(self._counters())
            else:
                self.settings.set("usage_stats", self.snapshot(), save_immediately=True)
            self._dirty = 0
        except Exception as e:
            log.warning(f"[usage] flush failed: {e}")
