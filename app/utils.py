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


import os
import time
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse, HttpResponse


def get_client_ip(request):
    """
    Retrieves the client's IP address from the request headers or remote address.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def ratelimit_view(rate="10/m", block=True):
    """
    Lightweight cache-based rate limiting decorator.
    Format: '10/m' (10 per minute), '100/h', '5/s'.
    Tracks per user if authenticated, or per client IP otherwise.
    """
    count_str, period_str = rate.split("/")
    max_requests = int(count_str)
    period_seconds = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
    }.get(period_str.lower(), 60)

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.method == "POST":
                if request.user.is_authenticated:
                    identifier = f"user_{request.user.id}"
                else:
                    identifier = f"ip_{get_client_ip(request)}"

                func_name = f"{view_func.__module__}.{view_func.__name__}"
                cache_key = f"ratelimit:{func_name}:{identifier}"

                now = time.time()
                timestamps = cache.get(cache_key, [])
                valid_timestamps = [t for t in timestamps if now - t < period_seconds]

                if len(valid_timestamps) >= max_requests:
                    if block:
                        is_json = (
                            request.path.startswith("/api/")
                            or request.headers.get("accept", "").startswith("application/json")
                            or request.content_type == "application/json"
                        )
                        if is_json:
                            return JsonResponse(
                                {
                                    "status": "error",
                                    "message": f"Rate limit exceeded. Maximum {rate} requests allowed.",
                                },
                                status=429,
                            )
                        else:
                            return HttpResponse(
                                f"Rate limit exceeded. Maximum {rate} requests allowed. Please wait before retrying.",
                                status=429,
                            )

                valid_timestamps.append(now)
                cache.set(cache_key, valid_timestamps, timeout=period_seconds + 5)

            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_AUDIO_EXTENSIONS = {".webm", ".wav", ".mp3", ".ogg", ".m4a"}
ALLOWED_AUDIO_CONTENT_TYPES = {
    "audio/webm",
    "video/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "application/ogg",
    "audio/m4a",
    "audio/x-m4a",
    "audio/mp4",
}


def validate_audio_file(audio_file):
    """
    Validates uploaded audio file size (<= 25 MB) and format (webm, wav, mp3, ogg, m4a).
    Returns (is_valid, error_message).
    """
    if not audio_file:
        return True, ""

    if audio_file.size > MAX_AUDIO_SIZE_BYTES:
        return False, "Audio file exceeds maximum allowed size of 25 MB."

    ext = os.path.splitext(audio_file.name)[1].lower()
    if ext and ext not in ALLOWED_AUDIO_EXTENSIONS:
        return False, f"Unsupported audio format '{ext}'. Allowed formats: webm, wav, mp3, ogg, m4a."

    content_type = getattr(audio_file, "content_type", "")
    if content_type:
        base_ct = content_type.split(";")[0].strip().lower()
        if base_ct not in ALLOWED_AUDIO_CONTENT_TYPES and base_ct != "application/octet-stream":
            return False, f"Unsupported audio content type '{content_type}'."

    return True, ""


def validate_and_clean_visual_metrics(metrics_data):
    """
    Validates visual metrics dictionary and ensures all metric scores are
    valid integers clamped within [0, 100].
    """
    if not isinstance(metrics_data, dict):
        return None

    cleaned = {}
    metric_keys = [
        "eye_contact_pct",
        "expression_variety_score",
        "posture_score",
        "face_detected_pct",
        "gesture_activity_score",
    ]

    for key in metric_keys:
        val = metrics_data.get(key)
        if val is not None:
            cleaned[key] = safe_int(val, default=0, min=0, max=100, clamp=True)
        else:
            cleaned[key] = 0

    for key in ["face_count_violations_json", "gaze_away_events_json"]:
        if key in metrics_data:
            cleaned[key] = metrics_data[key]

    return cleaned

