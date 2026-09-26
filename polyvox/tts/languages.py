"""Static language/voice metadata for the API and UI.

Importing `supertonic.config` is cheap (plain constants, no model weights),
so the language list is read live from the package. The voice list is a
static constant instead: the `web` process never loads the ONNX model (only
`worker` does), and Supertonic-3's 10 built-in voice styles are fixed and
documented (M1-M5, F1-F5).
"""

from supertonic.config import SUPPORTED_LANGUAGES

LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "ko": "Korean",
    "ja": "Japanese",
    "ar": "Arabic",
    "bg": "Bulgarian",
    "cs": "Czech",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "es": "Spanish",
    "et": "Estonian",
    "fi": "Finnish",
    "fr": "French",
    "hi": "Hindi",
    "hr": "Croatian",
    "hu": "Hungarian",
    "id": "Indonesian",
    "it": "Italian",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "nl": "Dutch",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sv": "Swedish",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "vi": "Vietnamese",
}

LANGUAGES: list[dict[str, str]] = [
    {"code": code, "name": LANGUAGE_NAMES.get(code, code)} for code in SUPPORTED_LANGUAGES
]

VOICE_IDS: list[str] = ["M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5"]

VOICES: list[dict[str, str]] = [
    {"id": voice_id, "label": f"{'Male' if voice_id.startswith('M') else 'Female'} {voice_id[1]}"}
    for voice_id in VOICE_IDS
]
