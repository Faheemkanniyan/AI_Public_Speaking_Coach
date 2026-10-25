import os
import json
import pprint
from django.core.management.base import BaseCommand, CommandError
from app.services.gemini_service import (
    GeminiSpeechAnalyzer,
    compute_objective_speech_metrics,
    GeminiEvaluationError
)


class Command(BaseCommand):
    help = "Evaluates a raw speech transcript using Gemini structured output and prints metrics, raw JSON, and validated report."

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, required=True, help="Path to text file containing candidate speech transcript")
        parser.add_argument("--topic", type=str, default="General Practice", help="Topic given for the speech")
        parser.add_argument("--audio", type=str, default="", help="Optional path to recorded audio file (.webm, .wav, .mp3)")
        parser.add_argument("--duration", type=int, default=0, help="Optional duration in seconds (computed if 0)")

    def handle(self, *args, **options):
        file_path = options["file"]
        topic = options["topic"]
        audio_path = options.get("audio", "").strip()
        duration = options.get("duration", 0)

        if not os.path.isfile(file_path):
            raise CommandError(f"Transcript file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            transcript = f.read().strip()

        if not transcript:
            raise CommandError("Transcript file is empty.")

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== 1. RAW INPUT ==="))
        self.stdout.write(f"Topic: {topic}")
        self.stdout.write(f"Transcript Length: {len(transcript)} chars ({len(transcript.split())} words)")
        self.stdout.write(f"Audio Path: {audio_path or '(None - Delivery marked not measurable)'}")

        # Compute objective metrics in Python
        metrics = compute_objective_speech_metrics(transcript, duration_seconds=duration)
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== 2. OBJECTIVE PYTHON METRICS ==="))
        self.stdout.write(json.dumps(metrics, indent=2))

        # Run Gemini Evaluation
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== 3. CALLING GEMINI STRUCTURED EVALUATION ==="))
        analyzer = GeminiSpeechAnalyzer()
        try:
            result = analyzer.analyze_speech(
                transcript=transcript,
                topic=topic,
                duration_seconds=metrics["duration_seconds"],
                audio_path=audio_path if (audio_path and os.path.isfile(audio_path)) else None,
                visual_context=""
            )
        except GeminiEvaluationError as gee:
            self.stdout.write(self.style.ERROR(f"Evaluation Failed: [{gee.code}] {gee.message}"))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Unexpected Evaluation Error: {e}"))
            return

        # Raw model JSON
        raw_json = result.get("raw_model_json", {})
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== 4. RAW GEMINI JSON RESPONSE ==="))
        self.stdout.write(json.dumps(raw_json, indent=2))

        # Final validated report
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== 5. FINAL VALIDATED REPORT ==="))
        display_dict = {k: v for k, v in result.items() if k != "raw_model_json"}
        self.stdout.write(json.dumps(display_dict, indent=2))
        self.stdout.write(self.style.SUCCESS(f"\nOverall Score: {result.get('overall_score')}/100 ({result.get('rating_label', 'Evaluated')})"))
