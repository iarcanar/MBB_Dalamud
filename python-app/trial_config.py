"""
trial_config.py — central build-time toggles for trial-pack distribution.

Flip these when packaging a free-trial build, then rebuild. They are baked into the
frozen exe so end users cannot edit them (unlike settings.json).

Normal / full build (default):
    TRIAL_PACK = False  →  nothing locked, token counter unlimited.

Trial-pack build:
    TRIAL_PACK = True
    TRIAL_TOKEN_LIMIT = 500_000   (or whatever quota the trial grants)
    →  model fixed to FORCED_MODEL, parameters fixed to FORCED_PARAMS (sliders + the
       RESET/APPLY buttons hidden in the Model panel), translation blocked once the
       token quota is spent.

The Model panel still always shows the API-key card + the usage card — a trial user
supplies their own Gemini key; the cap is on top of Google's own free quota.
"""

# Master switch — one flag arms the whole trial lockdown.
TRIAL_PACK = False

# Lifetime token quota (tokens). 0 = unlimited. Read by usage_tracker.
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
