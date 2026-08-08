# Platform Support

dazzle-loglib is pure Python with no platform-specific code paths and no dependencies beyond `dazzle-lib` (itself stdlib-only). Everything it does — integer comparison gating, string formatting, writing to a stream — is portable by construction.

| Platform | Status | Notes |
|---|---|---|
| Windows 10/11 | Tested | Primary development platform. Channel-spec parsing explicitly handles drive-letter paths (`timing::file:C:\logs\out.log`); library-emitted strings (warnings, errors, channel listings) are ASCII-only so they render correctly under codepage 437/1252. |
| Linux | Expected | No platform-specific code; CI builds run on ubuntu-latest. |
| macOS | Expected | Same. |

| Python | Status |
|---|---|
| 3.9 – 3.13 | Supported (`requires-python = ">=3.9"`; CI matrix covers 3.10–3.13) |

## Notes for embedders

- **Output destination** defaults to `stderr`. The `'stdout'`/`'stderr'` sentinel strings are resolved at emit time rather than at construction, so hosts that rebind streams after import (notably `pythonw.exe`, where both start as `None`) get the stream that exists when the message is written.
- **Terminal width and color** are not the library's concern — it never wraps or colorizes. Both belong in a renderer callable supplied via `init_output(renderer=...)`.
