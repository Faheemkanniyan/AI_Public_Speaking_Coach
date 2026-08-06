def global_settings(request):
    """
    Context processor to pass global settings and theme info to templates.
    """
    is_dark_mode = True
    if request.user.is_authenticated:
        try:
            from .models import Setting
            setting = Setting.objects.filter(user=request.user).first()
            if setting:
                is_dark_mode = setting.dark_mode
        except Exception:
            pass
    return {
        "APP_NAME": "SpeakPro AI",
        "APP_TAGLINE": "AI Public Speaking Coach",
        "USER_DARK_MODE": is_dark_mode,
    }
