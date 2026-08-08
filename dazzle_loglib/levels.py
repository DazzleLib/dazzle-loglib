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
