import argparse

from cli.main import run_cli
from services.gemini_speech import DEFAULT_GEMINI_MODEL


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BAT autocomplete with optional Google voice input.")
    parser.add_argument("--data-dir", default="Archive", help="Directory containing searchable .txt files")
    parser.add_argument("--voice-language", default="en-US", help="Speech language code (default: en-US)")
    parser.add_argument("--voice-provider", choices=("gemini", "cloud-speech"), default="gemini",
                        help="Transcription provider (default: gemini)")
    parser.add_argument("--voice-model", default=DEFAULT_GEMINI_MODEL,
                        help="Gemini audio/text model ID (default: %(default)s)")
    args = parser.parse_args()
    run_cli(args.data_dir, voice_language=args.voice_language,
            voice_provider=args.voice_provider, voice_model=args.voice_model)
