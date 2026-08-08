"""
Function tracing decorator.

Routes trace output through the OutputManager singleton at the full-debug
rung (DEBUG=5) on the 'trace' channel, rather than using its own global
verbosity. (Pre-0.2.0 this was rung 3 — the re-runged scale moved full
debug to 5.)
"""

import functools
import inspect
from pathlib import Path

from .levels import DEBUG


def trace(func):
    """Decorator to trace function calls via the OutputManager.

    Shows function entry/exit with arguments and return values when the
    'trace' CHANNEL's threshold reaches full debug (DEBUG=5). Note the
    channel starts opt-in-COLD on the legacy path, so a global ``-vvvvv``
    alone does not activate it — raise the channel explicitly with a spec
    (``--show trace:debug``), or declare a hot ``ChannelDef('trace')``
    (follows global verbosity) and run at ``-vvvvv``.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Lazy import to avoid circular dependency
        from .manager import get_output

        out = get_output()
        threshold = out.channel_overrides.get('trace', out.verbosity)

        if threshold >= DEBUG:
            # Get function signature info
            module = inspect.getmodule(func)
            module_name = module.__name__ if module else "unknown"
            func_name = func.__name__

            # Format arguments
            args_repr = []

            # Handle self/cls for methods
            if args and hasattr(args[0], '__class__'):
                if func_name != '__init__':
                    args_repr.append('self')
                    remaining_args = args[1:]
                else:
                    remaining_args = args
            else:
                remaining_args = args

            # Add remaining positional arguments
            for arg in remaining_args:
                if isinstance(arg, Path):
                    args_repr.append(f"Path('{arg}')")
                elif isinstance(arg, str) and len(arg) > 50:
                    args_repr.append(f"'{arg[:47]}...'")
                elif isinstance(arg, list) and len(arg) > 3:
                    args_repr.append(f"[...{len(arg)} items...]")
                else:
                    args_repr.append(repr(arg))

            # Add keyword arguments
            for key, value in kwargs.items():
                if isinstance(value, Path):
                    args_repr.append(f"{key}=Path('{value}')")
                elif isinstance(value, str) and len(value) > 50:
                    args_repr.append(f"{key}='{value[:47]}...'")
                else:
                    args_repr.append(f"{key}={repr(value)}")

            args_str = ', '.join(args_repr)

            # Print entry
            out.emit(DEBUG, "[TRACE] >> {mod}.{fn}({args})",
                     channel='trace', mod=module_name, fn=func_name, args=args_str)

            try:
                result = func(*args, **kwargs)

                # Print exit with return value (if not None)
                if result is not None:
                    if isinstance(result, list) and len(result) > 3:
                        result_repr = f"[...{len(result)} items...]"
                    elif isinstance(result, str) and len(result) > 50:
                        result_repr = f"'{result[:47]}...'"
                    else:
                        result_repr = repr(result)
                    out.emit(DEBUG, "[TRACE] << {mod}.{fn} returned: {val}",
                             channel='trace', mod=module_name, fn=func_name, val=result_repr)

                return result

            except Exception as e:
                out.emit(DEBUG, "[TRACE] !! {mod}.{fn} raised: {exc}: {msg}",
                         channel='trace', mod=module_name, fn=func_name,
                         exc=type(e).__name__, msg=str(e))
                raise
        else:
            return func(*args, **kwargs)

    return wrapper
