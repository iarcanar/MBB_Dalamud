"""
trial_config.py — central build-time toggles for trial-pack distribution.

Flip these when packaging a build, then rebuild. They are baked into the frozen exe so
end users cannot edit them (unlike settings.json).

*** CURRENT PHASE: initial free distribution ***
    TRIAL_PACK = False, TRIAL_TOKEN_LIMIT = 0
    →  UNLIMITED translation (nothing blocked, nothing locked, full editable Model panel)
       BUT token usage is still counted and stored per machine/user (encrypted, local),
       so each install accumulates its own running total — visible in the Model panel as
       "ใช้ไป N tokens (ไม่จำกัด)". This gives us per-user usage data now, with zero
       friction, and lets us turn on a real cap later by flipping the two values below.

Later — trial-pack build (one flip):
    TRIAL_PACK = True
    TRIAL_TOKEN_LIMIT = 500_000   (or whatever quota the trial grants)
    →  model fixed to FORCED_MODEL, parameters fixed to FORCED_PARAMS (sliders shown but
       disabled, RESET/APPLY hidden), translation blocked once the quota is spent.

The Model panel always shows the API-key card + the usage card — users supply their own
Gemini key; any future cap is on top of Google's own free quota.
"""

# Master switch — one flag arms the whole trial lockdown. (Initial distribution: False)
TRIAL_PACK = False

# Lifetime token quota (tokens). 0 = unlimited. Read by usage_tracker.
# Initial distribution = 0 (count only, never block). Set > 0 to arm a real trial cap.
TRIAL_TOKEN_LIMIT = 0

# Derived locks (default to the master switch; override individually only if needed).
LOCK_MODEL = TRIAL_PACK
LOCK_PARAMETERS = TRIAL_PACK

# Values forced when locked — the current quality-tuned configuration.
FORCED_MODEL = "gemini-3.1-flash-lite"
FORCED_PARAMS = {
    "max_tokens": 500,
    "temperature": 0.8,
    "top_p": 0.9,
}
