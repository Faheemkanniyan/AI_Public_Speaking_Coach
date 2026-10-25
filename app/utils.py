"""
Utility helper functions for SpeakPro AI.
"""

def safe_int(value, default=None, min=None, max=None, clamp=False):
    """
    Safely converts value to int and validates or clamps within [min, max].

    If value is None or an empty/whitespace string, returns default.
    If value cannot be parsed to an int, returns default.
    If clamp is True:
        clamps the integer to [min, max].
    If clamp is False:
        if value < min or value > max, returns default.
    """
    if value is None:
        return default
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return default
    try:
        val = int(value)
    except (ValueError, TypeError, OverflowError):
        return default

    if clamp:
        if min is not None and val < min:
            val = min
        if max is not None and val > max:
            val = max
        return val
    else:
        if min is not None and val < min:
            return default
        if max is not None and val > max:
            return default
        return val
