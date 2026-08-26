# backend/tts_helper.py
# Standalone TTS Helper for Dr. Vishnuvardhan Voice Package

import os
import sys
import argparse
from pathlib import Path

# Add project root directory to path for imports
CURRENT_DIR = Path(__file__).parent.resolve()
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from adapters.seedvc_adapter import SeedVCAdapter

class VishnuvardhanTTS:
    def __init__(self, voice_pack_dir: str = None):
        if voice_pack_dir is None:
            default_vc = CURRENT_DIR / "voice_packs" / "bandhana_voice.vc"
            voice_pack_dir = os.getenv("VOICE_PACK_PATH", str(default_vc))
            
        if not os.path.exists(voice_pack_dir):
            raise FileNotFoundError(f"Voice package directory not found: {voice_pack_dir}")
            
        print(f"Loading Dr. Vishnuvardhan Voice Package from: {voice_pack_dir}")
        self.adapter = SeedVCAdapter()
        # Direct Flow-Matching with pitch-aligned base voice
        self.adapter._xtts_adapter = False
        self.adapter.load_voice_package(voice_pack_dir)

    def speak(self, text: str, language: str = "kn", output_file: str = "output.wav") -> str:
        """
        Synthesizes text into natural speech.
        Supported languages: 'kn' (Kannada), 'hi' (Hindi), 'ta' (Tamil), 'en' (English)
        """
        base_voice_map = {
            "kn": "kn-IN-GaganNeural",
            "hi": "hi-IN-MadhurNeural",
            "ta": "ta-IN-ValluvarNeural",
            "en": "en-IN-PrabhatNeural"
        }
        base_voice = base_voice_map.get(language, "kn-IN-GaganNeural")

        result = self.adapter.synthesize(
            text=text,
            language=language,
            base_voice=base_voice,
            temperature=0.70,
            speed=1.0
        )

        generated_wav = result.get("audio_path")
        if output_file and generated_wav != output_file:
            import shutil
            shutil.copy(generated_wav, output_file)
            return os.path.abspath(output_file)

        return generated_wav

def main():
    parser = argparse.ArgumentParser(description="Dr. Vishnuvardhan Voice TTS CLI")
    parser.add_argument("--text", type=str, required=True, help="Text to speak")
    parser.add_argument("--lang", type=str, default="kn", choices=["kn", "hi", "ta", "en"], help="Target language")
    parser.add_argument("--out", type=str, default="vishnuvardhan_speech.wav", help="Output WAV file path")
    
    args = parser.parse_args()
    
    tts = VishnuvardhanTTS()
    saved_path = tts.speak(text=args.text, language=args.lang, output_file=args.out)
    print("=" * 60)
    print(" SYNTHESIS COMPLETE")
    print(f" Saved Audio File: {saved_path}")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        # Quick test
        tts = VishnuvardhanTTS()
        out = tts.speak(
            text="ನಮಸ್ಕಾರ! ಇದು ಡಾಕ್ಟರ್ ವಿಷ್ಣುವರ್ಧನ್ ಅವರ ಧ್ವನಿಯಲ್ಲಿ ಮೂಡಿಬಂದಿದೆ.",
            language="kn",
            output_file="test_kannada.wav"
        )
        print(f"Generated test audio at: {out}")
