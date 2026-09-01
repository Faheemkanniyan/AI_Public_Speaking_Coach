"""
Forms for SpeakPro AI user authentication, profile editing, and settings.
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import UserProfile, Setting


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        "class": "form-control bg-dark border-secondary text-light",
        "placeholder": "Enter your email address"
    }))
    username = forms.CharField(required=True, widget=forms.TextInput(attrs={
        "class": "form-control bg-dark border-secondary text-light",
        "placeholder": "Choose a username"
    }))

    class Meta:
        model = User
        fields = ("username", "email")


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        "class": "form-control bg-dark border-secondary text-light",
        "placeholder": "Username or Email"
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": "form-control bg-dark border-secondary text-light",
        "placeholder": "Password"
    }))


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={
        "class": "form-control bg-dark border-secondary text-light",
        "placeholder": "First Name"
    }))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={
        "class": "form-control bg-dark border-secondary text-light",
        "placeholder": "Last Name"
    }))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        "class": "form-control bg-dark border-secondary text-light",
        "placeholder": "Email Address"
    }))

    class Meta:
        model = UserProfile
        fields = ("bio", "profile_photo")
        widgets = {
            "bio": forms.Textarea(attrs={
                "class": "form-control bg-dark border-secondary text-light",
                "rows": 3,
                "placeholder": "Tell us about your speaking goals..."
            }),
            "profile_photo": forms.FileInput(attrs={
                "class": "form-control bg-dark border-secondary text-light"
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["email"].initial = user.email


class SettingForm(forms.ModelForm):
    class Meta:
        model = Setting
        fields = ("dark_mode", "notifications_enabled")
        widgets = {
            "dark_mode": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notifications_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "microphone_device": forms.TextInput(attrs={
                "class": "form-control bg-dark border-secondary text-light",
                "placeholder": "Default Microphone"
            }),
            "language": forms.Select(
                choices=[
                    ("English (US)", "English (US)"),
                    ("English (UK)", "English (UK)"),
                    ("Spanish", "Spanish"),
                    ("French", "French"),
                    ("German", "German"),
                ],
                attrs={"class": "form-select bg-dark border-secondary text-light"}
            ),
        }
