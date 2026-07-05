# dazzle-loglib

Channel/verbosity-aware CLI output management, built on `dazzle-lib` continua.

Extracted from the dazzlecmd `_vendor/log_lib` canonical copy (origin: wtf-windows, plus the DWP-B continuum redesign: `VERBOSITY_CONTINUUM` with 8 named rungs, the `shows()` gate, named-rank channel specs, the channels x verbosity `VERBOSITY_SPACE`, opt-in cold-start declared via the Continuum).

Modules: `manager` (OutputManager / init_output / get_output), `channels`, `verbosity`, `hints`, `levels`, `trace`.

Part of the DazzleLib collection. Alpha; API settling alongside the dazzlecmd FQCN arc (channel identities are becoming derived FQCN tree nodes).
