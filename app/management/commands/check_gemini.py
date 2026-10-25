import sys
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from app.services.gemini_service import GeminiEvaluationError, map_gemini_exception

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Validates Gemini API configuration: key presence, model existence, and end-to-end call."

    def handle(self, *args, **options):
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        model_name = getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash")

        # 1. Key presence check
        if not api_key:
            err = GeminiEvaluationError(code="no_key", message="GEMINI_API_KEY is not set")
            self.stdout.write(self.style.ERROR(f"FAIL: {err.message} (code: {err.code})"))
            sys.exit(1)

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            self.stdout.write(self.style.ERROR("FAIL: google-genai package is not installed (code: unavailable)"))
            sys.exit(1)

        # 2. Client initialization
        try:
            client = genai.Client(api_key=api_key)
        except Exception as e:
            err = map_gemini_exception(e, model_name=model_name)
            self.stdout.write(self.style.ERROR(f"FAIL: {err.message} (code: {err.code})"))
            sys.exit(1)

        # 3. Model existence check via models.list()
        try:
            available_models = [m.name.replace("models/", "") for m in client.models.list()]
            clean_target = model_name.replace("models/", "")
            if clean_target not in available_models:
                err = GeminiEvaluationError(
                    code="model_not_found",
                    message=f"Model '{model_name}' not found, check GEMINI_MODEL"
                )
                self.stdout.write(self.style.ERROR(f"FAIL: {err.message} (code: {err.code})"))
                sys.exit(1)
        except Exception as e:
            err = map_gemini_exception(e, model_name=model_name)
            self.stdout.write(self.style.ERROR(f"FAIL: {err.message} (code: {err.code})"))
            sys.exit(1)

        # 4. Tiny generateContent call
        try:
            thinking = types.ThinkingConfig(thinking_budget=0) if hasattr(types, "ThinkingConfig") else None
            config_kwargs = {"temperature": 0.0}
            if thinking:
                config_kwargs["thinking_config"] = thinking
            config = types.GenerateContentConfig(**config_kwargs)

            response = client.models.generate_content(
                model=model_name,
                contents="ping",
                config=config
            )
            if not response or not (response.text or "").strip():
                err = GeminiEvaluationError(
                    code="invalid_response",
                    message="Gemini returned an unusable response"
                )
                self.stdout.write(self.style.ERROR(f"FAIL: {err.message} (code: {err.code})"))
                sys.exit(1)
        except Exception as e:
            err = map_gemini_exception(e, model_name=model_name)
            self.stdout.write(self.style.ERROR(f"FAIL: {err.message} (code: {err.code})"))
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS(f"PASS: Gemini API is healthy and connected to model '{model_name}'."))
        return
