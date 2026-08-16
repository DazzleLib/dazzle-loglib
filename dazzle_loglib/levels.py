"""
THAC0 verbosity level constants — the 10-rung scale (SD-FQCN-4 re-rung).

These are informational — the system uses raw integers, not these constants.
They exist for readability and documentation. The emit rule is simple:

    message.level <= threshold  →  message is shown

The threshold is either the global verbosity or a per-channel override.

Level assignments (re-runged 2026-08-08, adopting the 2026-06-29 SD-FQCN-4
request; the user's verbatim scale):

    ←── quieter ─────────────── default ─────────────────────── louder ──→
    -4    -3     -2       -1      0       1     2           3      4          5
    wall  errors warnings minimal default extra diagnostics config lite-debug debug

Historical note: the pre-0.2.0 scale was 8 rungs (-4..+3) with timing=1,
config=2, debug=3. The gate is unchanged; the MAP changed: config moved 2→3,
debug moved 3→5 (full debug), and rank 1 was renamed timing→extra (deprecated
alias below). Consumers of the old vendored copies re-map at their cutover
(DazzleTools/dazzlecmd#118).
"""

# Positive levels (verbose output, shown with -v .. -vvvvv)
DEBUG = 5          # Full debug — internal state, evaluation/call tracing
LITE_DEBUG = 4     # Light debug detail
CONFIG = 3         # Configuration, algorithm selection
DIAGNOSTICS = 2    # Diagnostic detail (decision inputs, guard math)
EXTRA = 1          # Progress, timing, summary info
DEFAULT = 0        # Default output, result-context hints

# Negative levels (quiet suppression, activated with -Q/-QQ/-QQQ/-QQQQ)
MINIMAL = -1       # Suppress hints
WARNING = -2       # Suppress progress
ERROR = -3         # Errors only
NOTHING = -4       # Hard wall — exit code only (CI/headless)

# Deprecated alias — pre-0.2.0 name for rank 1 (the rung is now "extra").
TIMING = EXTRA


# One-line gloss per rung, keyed by the CONTINUUM's rung name (not the constant
# name). These are library-owned: the rung names and ranks are locked API, so
# only this library can canonically say what each one means -- consumers that
# explain the scale to users (a `--help` table, a `verbosity` sub-command)
# should render these rather than re-author ten strings apiece.
#
# ASCII only, deliberately: this text is printed to terminals, including
# Windows codepage 437/1252 consoles.
# Voice: every gloss answers "what do I GET at this level?", not "what is
# suppressed" -- the question a user reads the table to answer. (The negative
# rungs were originally phrased as suppression, which read backwards once the
# rungs were rendered together.)
RUNG_GLOSSES = {
    "nothing":    "Nothing at all -- exit code only (CI/headless)",
    "error":      "Errors only",
    "warning":    "Errors and warnings",
    "minimal":    "Results only -- no hints",
    "default":    "Default output, result-context hints",
    "extra":      "Progress, timing, summary info",
    "diagnostics": "Diagnostic detail (decision inputs, guard math)",
    "config":     "Configuration, algorithm selection",
    "lite-debug": "Light debug detail",
    "debug":      "Full debug -- internal state, evaluation/call tracing",
}
