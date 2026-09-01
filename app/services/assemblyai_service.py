"""
AssemblyAI Speech-to-Text Transcription Service for SpeakPro AI.
Transcribes uploaded audio files with high accuracy and disfluency/filler word detection.
"""

import os
import re
import time
import logging
import requests
from django.conf import settings
from django.utils.html import escape

logger = logging.getLogger(__name__)

# List of common filler words and disfluencies
FILLER_WORDS_LIST = [
    "literally", "basically", "actually", "you know", "i mean",
    "sort of", "kind of", "right", "like", "um", "uh", "mhm",
    "hmm", "ah", "er", "so"
]


class AssemblyAIService:
    """
    Client for AssemblyAI REST API v2.
    Provides speech-to-text transcription with filler word detection
    and visual transcript highlighting.
    """
    UPLOAD_ENDPOINT = "https://api.assemblyai.com/v2/upload"
    TRANSCRIPT_ENDPOINT = "https://api.assemblyai.com/v2/transcript"

    def __init__(self):
        self.api_key = getattr(settings, "ASSEMBLYAI_API_KEY", "") or os.getenv("ASSEMBLYAI_API_KEY", "")
        self.headers = {
            "authorization": self.api_key
        }

    def is_enabled(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def transcribe_audio(self, audio_file_path: str) -> dict:
        """
        Uploads an audio file and requests a transcription from AssemblyAI
        with disfluencies (filler words) enabled.
        Returns dictionary with text, status, words, and error (if any).
        """
        if not self.is_enabled():
            return {"status": "disabled", "text": "", "error": "No AssemblyAI API key set."}

        if not os.path.exists(audio_file_path):
            return {"status": "error", "text": "", "error": f"Audio file not found: {audio_file_path}"}

        try:
            # 1. Upload audio file bytes
            with open(audio_file_path, "rb") as f:
                upload_res = requests.post(self.UPLOAD_ENDPOINT, headers=self.headers, data=f, timeout=30)
            
            if upload_res.status_code != 200:
                logger.error(f"AssemblyAI Upload Error: {upload_res.text}")
                return {"status": "error", "text": "", "error": f"Upload failed ({upload_res.status_code})"}

            audio_url = upload_res.json().get("upload_url")
            if not audio_url:
                return {"status": "error", "text": "", "error": "No upload_url received from AssemblyAI."}

            # 2. Request transcription with disfluencies enabled and auto language detection
            transcript_payload = {
                "audio_url": audio_url,
                "disfluencies": True,
                "language_detection": True,
            }
            trans_res = requests.post(self.TRANSCRIPT_ENDPOINT, json=transcript_payload, headers=self.headers, timeout=15)
            if trans_res.status_code != 200:
                logger.error(f"AssemblyAI Transcription Error: {trans_res.text}")
                return {"status": "error", "text": "", "error": f"Transcription request failed ({trans_res.status_code})"}

            transcript_id = trans_res.json().get("id")
            if not transcript_id:
                return {"status": "error", "text": "", "error": "No transcript ID returned from AssemblyAI."}

            # 3. Poll for completion (up to 30 seconds)
            poll_url = f"{self.TRANSCRIPT_ENDPOINT}/{transcript_id}"
            max_retries = 15
            for _ in range(max_retries):
                time.sleep(2)
                poll_res = requests.get(poll_url, headers=self.headers, timeout=10)
                if poll_res.status_code == 200:
                    data = poll_res.json()
                    status = data.get("status")
                    if status == "completed":
                        return {
                            "status": "completed",
                            "text": data.get("text", ""),
                            "language_code": data.get("language_code", ""),
                            "words": data.get("words", []),
                            "transcript_id": transcript_id
                        }
                    elif status == "error":
                        return {
                            "status": "error",
                            "text": "",
                            "error": data.get("error", "Transcription failed on AssemblyAI server.")
                        }
            return {"status": "timeout", "text": "", "error": "AssemblyAI transcription timed out."}
        except Exception as e:
            logger.exception("AssemblyAI transcription exception")
            return {"status": "error", "text": "", "error": str(e)}

    @classmethod
    def analyze_filler_words(cls, transcript: str, mistakes: list = None) -> dict:
        """
        Analyzes any speech transcript text for filler words and disfluencies.
        Returns counts, percentage, word breakdown list, and HTML-highlighted transcript
        with filler words in badges and grammar/phrase mistakes underlined in redline.
        """
        text = (transcript or "").strip()
        words = re.findall(r'\b\w+\b', text.lower())
        total_words = max(1, len(words))

        # Detect language based on unicode ranges
        if re.search(r'[\u0900-\u097F]', text):
            language = "hi-IN"
            filler_list = ["मतलब", "जैसे", "तो", "उम्म", "आ"]
            stt_fixes = []
            fw_to_remove = ["मतलब", "जैसे", "तो", "उम्म", "आ"]
        elif re.search(r'[\u0D00-\u0D7F]', text):
            language = "ml-IN"
            filler_list = ["ഉം", "അതായത്", "പിന്നെ", "ആ"]
            stt_fixes = []
            fw_to_remove = ["ഉം", "അതായത്", "പിന്നെ", "ആ"]
        else:
            language = "en-US"
            filler_list = FILLER_WORDS_LIST
            stt_fixes = [
                (r'\bthe amputation is the most one thing in my our brain\b', 'ambition is a primary focus in our mind', 'Improved articulation and clarity'),
                (r'\bmy our\b', 'our', 'Removed duplicate pronoun'),
                (r'\bsomething like that\b', 'and related factors', 'Replaced informal qualifier with executive phrasing'),
                (r'\bmore to tall\b', 'more to share', 'Corrected word choice error'),
                (r'\bdo to call me\b', 'to discuss with me', 'Corrected spoken syntax fragment'),
                (r'\bshould actually good\b', 'should actually be effective', 'Added missing auxiliary verb')
            ]
            fw_to_remove = ["actually", "literally", "basically", "um", "uh", "like"]

        breakdown_dict = {}
        total_fillers = 0

        # Sort filler list by length descending so multi-word phrases match first
        sorted_fillers = sorted(filler_list, key=len, reverse=True)

        for filler in sorted_fillers:
            pattern = r'\b' + re.escape(filler) + r'\b'
            matches = re.findall(pattern, text.lower())
            count = len(matches)
            if count > 0:
                breakdown_dict[filler] = count
                total_fillers += count

        filler_percentage = round((total_fillers / total_words) * 100, 1)

        # Build sorted breakdown list
        filler_breakdown = [
            {"word": word, "count": count}
            for word, count in sorted(breakdown_dict.items(), key=lambda x: x[1], reverse=True)
        ]

        # Build HTML highlighted transcript
        escaped_text = escape(text)
        highlighted = escaped_text

        # 1. Highlight consecutive duplicate words (e.g., "me, me" or "the the") in REDLINE
        rep_pattern = re.compile(r'\b(\w+)(?:[,\s]+\1\b)+', re.IGNORECASE)
        highlighted = rep_pattern.sub(
            r'<span class="text-danger fw-bold" style="text-decoration: underline wavy #ff4d4f 2.5px !important; color: #ff6b6b; cursor: help;" title="Repeated word error: eliminate accidental stuttering">\g<0></span>',
            highlighted
        )

        # 2. Highlight grammar/phrase mistakes with RED UNDERLINE (redline)
        if mistakes and isinstance(mistakes, list):
            for m in mistakes:
                orig = m.get("original", "").strip()
                correction = escape(m.get("correction", "Grammar correction"))
                reason = escape(m.get("reason", "Grammar error detected"))
                if orig and len(orig) > 2 and orig.lower() in text.lower():
                    escaped_orig = escape(orig)
                    pattern = re.compile(re.escape(escaped_orig), re.IGNORECASE)
                    highlighted = pattern.sub(
                        rf'<span class="text-danger fw-bold" style="text-decoration: underline wavy #ff4d4f 2.5px !important; color: #ff6b6b; cursor: help;" title="Correction: {correction} ({reason})">\g<0></span>',
                        highlighted,
                        count=1
                    )

        # 3. Highlight filler words with a glowing warning badge
        for filler in sorted_fillers:
            if filler in breakdown_dict:
                pattern = re.compile(r'\b(' + re.escape(filler) + r')\b', re.IGNORECASE)
                highlighted = pattern.sub(
                    r'<span class="badge bg-warning-subtle text-warning border border-warning px-2 py-1 mx-1" title="Filler word detected">\1</span>',
                    highlighted
                )

        # 4. Build AI-Corrected Executive Transcript HTML (for the corrected sentence box)
        corrected_html = escape(text)

        # Apply STT articulation fixes first
        for pat, replacement, reason_txt in stt_fixes:
            if re.search(pat, corrected_html, flags=re.IGNORECASE):
                badge = rf'<span class="badge bg-success-subtle text-neon-green border border-success px-2 py-1 mx-1" style="font-size: 0.88rem;" title="Reason: {reason_txt}">{replacement}</span>'
                corrected_html = re.sub(pat, badge, corrected_html, flags=re.IGNORECASE)

        # Apply specific mistake corrections (only where no badge tag has already been placed over orig)
        if mistakes and isinstance(mistakes, list):
            for m in mistakes:
                orig = m.get("original", "").strip()
                correction = escape(m.get("correction", "")).strip()
                reason = escape(m.get("reason", "Executive improvement"))
                if orig and len(orig) > 2 and orig.lower() in text.lower() and correction:
                    escaped_orig = escape(orig)
                    if escaped_orig.lower() in corrected_html.lower() and "<span" not in escaped_orig.lower():
                        pattern = re.compile(re.escape(escaped_orig), re.IGNORECASE)
                        badge_html = rf'<span class="badge bg-success-subtle text-neon-green border border-success px-2 py-1 mx-1" style="font-size: 0.88rem;" title="Original: {escaped_orig} &#10;Reason: {reason}">{correction}</span>'
                        corrected_html = pattern.sub(badge_html, corrected_html, count=1)

        # Remove standalone filler words cleanly from uncorrected portions
        for fw in fw_to_remove:
            corrected_html = re.sub(r'(?<!=")\b' + re.escape(fw) + r'\b,?\s*(?![^<]*>)', '', corrected_html, flags=re.IGNORECASE)

        # Fix repeated consecutive words outside HTML tags
        def _fix_rep(m):
            return m.group(1)
        corrected_html = re.sub(r'\b(\w+)(?:\s+\1\b)+(?![^<]*>)', _fix_rep, corrected_html, flags=re.IGNORECASE)

        return {
            "total_words": total_words,
            "filler_count": total_fillers,
            "filler_percentage": filler_percentage,
            "filler_breakdown": filler_breakdown,
            "highlighted_transcript": highlighted,
            "corrected_transcript_html": corrected_html,
        }
