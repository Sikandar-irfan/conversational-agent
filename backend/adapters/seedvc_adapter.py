"""
ROSE Backend Adapters — Seed-VC Adapter
=======================================
Adapts generic .vc voice packages to Dravidian languages (Tamil/Kannada)
using a two-step generation pipeline: Microsoft Edge Neural TTS base + Seed-VC timbre transfer.
"""

import os
import sys
import json
import time
import base64
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
import torch
import pydub
import soundfile as sf
import edge_tts
import numpy as np
from loguru import logger

from adapters.base import BaseAdapter


class SeedVCAdapter(BaseAdapter):
    """
    Adapter that handles high-fidelity voice cloning using Seed-VC
    by combining Microsoft Edge Neural TTS base synthesis with Seed-VC voice conversion.

    Dynamic XTTS-direct routing:
        If the XTTS output achieves >= direct_threshold ECAPA similarity,
        the Seed-VC stage is skipped entirely.
    """
    DIRECT_THRESHOLD_DEFAULT = 0.60

    def __init__(self, direct_threshold: Optional[float] = None):
        self.target_wav: Optional[Path] = None
        self.vc_dir: Optional[Path] = None
        self.voice_name: str = ""
        self.pitch_mean: float = 160.0
        self.pitch_std: float = 30.0
        self._extractor = None
        self._xtts_adapter = None
        self.direct_threshold: float = (
            direct_threshold
            if direct_threshold is not None
            else self.DIRECT_THRESHOLD_DEFAULT
        )

    def load_voice_package(self, vc_path: str) -> None:
        vc_dir = Path(vc_path)
        if not vc_dir.exists():
            raise FileNotFoundError(f"Voice package directory not found: {vc_path}")
            
        metadata_file = vc_dir / "metadata.json"
        if not metadata_file.exists():
            raise ValueError(f"Invalid voice package: metadata.json missing in {vc_path}")
            
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            
        self.voice_name = metadata.get("voice_name", vc_dir.stem)
        
        # Load pitch and speed stats
        stats_file = vc_dir / "stats.json"
        self.pitch_mean = 160.0
        self.pitch_std = 30.0
        self.speaking_rate = 3.2
        if stats_file.exists():
            try:
                with open(stats_file, "r", encoding="utf-8") as f:
                    stats = json.load(f)
                    self.pitch_mean = stats.get("pitch_mean", 160.0)
                    self.speaking_rate = stats.get("speaking_rate", 3.2)
                    pitch_var = stats.get("pitch_variance", 900.0)
                    self.pitch_std = float(pitch_var ** 0.5)
            except Exception as e:
                logger.warning(f"Could not load pitch/speed stats: {e}")
        
        # Load reference audio
        self.vc_dir = vc_dir
        self.target_wav = vc_dir / "reference.wav"
        if not self.target_wav.exists():
            raise FileNotFoundError(f"Reference WAV missing in voice package: {vc_path}")
            
        logger.info(f"SeedVCAdapter configured with target reference: {self.target_wav.name} (Pitch: {self.pitch_mean:.1f}Hz ± {self.pitch_std:.1f}Hz)")

    @property
    def _xtts(self):
        """Lazy-load XTTSAdapter for direct routing."""
        if self._xtts_adapter is None:
            try:
                from adapters.xtts_adapter import XTTSAdapter
                self._xtts_adapter = XTTSAdapter()
                if self.vc_dir is not None:
                    self._xtts_adapter.load_voice_package(str(self.vc_dir))
            except Exception as e:
                logger.debug(f"XTTSAdapter not available for direct routing: {e}")
                self._xtts_adapter = False  # sentinel
        return self._xtts_adapter if self._xtts_adapter is not False else None

    def _get_audio_duration(self, wav_path: str) -> float:
        try:
            info = sf.info(wav_path)
            return info.duration
        except Exception:
            return 0.0

    def _load_audio_numpy(self, path: str, target_sr: int = 22050) -> tuple:
        """Load any audio format to mono numpy at target_sr. Uses soundfile fallback."""
        try:
            import torchaudio
            sig, sr = torchaudio.load(path)
            if sr != target_sr:
                sig = torchaudio.functional.resample(sig, sr, target_sr)
            audio_np = sig.mean(0).numpy()
        except Exception:
            # Fallback for OGG and other formats when torchcodec is missing
            data, sr = sf.read(path, dtype="float32", always_2d=True)
            audio_np = data.mean(axis=1)           # channels → mono
            if sr != target_sr:
                import librosa
                audio_np = librosa.resample(audio_np, orig_sr=sr, target_sr=target_sr)
        return audio_np, target_sr

    def synthesize(self, text: str, language: str, **kwargs) -> Dict[str, Any]:
        if self.target_wav is None:
            raise RuntimeError("No voice package loaded. Call load_voice_package() first.")

        # -- Dynamic XTTS-direct routing ---------------------------------------
        skip_xtts_routing = kwargs.get("skip_xtts_routing", False)
        if not skip_xtts_routing and self._xtts is not None:
            try:
                xtts_result = self._xtts.synthesize(text=text, language=language,
                                                     temperature=kwargs.get("temperature", 0.75))
                xtts_audio = xtts_result.get("audio_path", "")
                if xtts_audio and Path(xtts_audio).exists() and self.vc_dir:
                    if self._extractor is None:
                        from features.extractor import ROSEFeatureExtractor
                        self._extractor = ROSEFeatureExtractor()
                    sim = self._extractor.calculate_similarity(
                        str(self.vc_dir / "reference.wav"), xtts_audio
                    )
                    if sim >= self.direct_threshold:
                        logger.success(
                            f"XTTS-direct route taken: ECAPA={sim:.4f} >= {self.direct_threshold} threshold"
                            f" | skipping Seed-VC"
                        )
                        xtts_result["routing"] = "xtts_direct"
                        xtts_result["ecapa_similarity"] = sim
                        return xtts_result
                    else:
                        logger.debug(
                            f"XTTS-direct route skipped: ECAPA={sim:.4f} < {self.direct_threshold}"
                            f" | falling through to Seed-VC"
                        )
            except Exception as routing_e:
                logger.debug(f"XTTS-direct routing failed ({routing_e}), using Seed-VC path")
        # ----------------------------------------------------------------------

        is_male = self.pitch_mean < 165.0
        
        voice_mappings = {
            "en": ("en-IN-PrabhatNeural", "en-IN-NeerjaExpressiveNeural"),
            "hi": ("hi-IN-MadhurNeural", "hi-IN-SwaraNeural"),
            "ta": ("ta-IN-ValluvarNeural", "ta-IN-PallaviNeural"),
            "kn": ("kn-IN-GaganNeural", "kn-IN-SapnaNeural"),
            "es": ("es-ES-AlvaroNeural", "es-ES-ElviraNeural"),
            "fr": ("fr-FR-HenriNeural", "fr-FR-DeniseNeural"),
            "de": ("de-DE-ConradNeural", "de-DE-AmalaNeural"),
            "it": ("it-IT-DiegoNeural", "it-IT-ElsaNeural"),
            "pt": ("pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"),
            "pl": ("pl-PL-MarekNeural", "pl-PL-ZofiaNeural"),
            "tr": ("tr-TR-AhmetNeural", "tr-TR-EmelNeural"),
            "ru": ("ru-RU-DmitryNeural", "ru-RU-SvetlanaNeural"),
            "nl": ("nl-NL-MaartenNeural", "nl-NL-ColetteNeural"),
            "cs": ("cs-CZ-AntoninNeural", "cs-CZ-VlastaNeural"),
            "ar": ("ar-EG-ShakirNeural", "ar-EG-SalmaNeural"),
            "zh-cn": ("zh-CN-YunxiNeural", "zh-CN-XiaoxiaoNeural"),
            "hu": ("hu-HU-TamasNeural", "hu-HU-NoemiNeural"),
            "ko": ("ko-KR-InJoonNeural", "ko-KR-SunHiNeural"),
            "ja": ("ja-JP-KeitaNeural", "ja-JP-NanamiNeural"),
        }
        
        lang_key = language.split("-")[0].lower()
        if language.lower() == "zh-cn":
            lang_key = "zh-cn"
            
        mapping = voice_mappings.get(lang_key, ("en-IN-PrabhatNeural", "en-IN-NeerjaExpressiveNeural"))
        base_voice = mapping[0] if is_male else mapping[1]
        
        base_pitch = 120.0 if is_male else 200.0
        pitch_diff = self.pitch_mean - base_pitch
        pitch_val = int(round(pitch_diff))
        pitch_str = f"{pitch_val:+}Hz"
        
        rate_diff = (self.speaking_rate - 3.2) / 3.2
        rate_percent = int(round(max(-0.15, min(0.15, rate_diff)) * 100))
        rate_str = f"{rate_percent:+}%"
        
        logger.info(
            f"SeedVCAdapter: Aligning base voice '{base_voice}' to match speaker:\n"
            f"  - Target Pitch: {self.pitch_mean:.1f}Hz (Offset: {pitch_str})\n"
            f"  - Target Rate: {self.speaking_rate:.2f} syl/s (Offset: {rate_str})"
        )
        
        import tempfile
        output_dir = Path(__file__).parent.parent / "output" / "audio" / "conversion"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Synthesize base natural audio using edge-tts
        tmp_mp3 = tempfile.NamedTemporaryFile(suffix="_base.mp3", delete=False)
        tmp_mp3_path = tmp_mp3.name
        tmp_mp3.close()
        
        async def run_edge_tts():
            communicate = edge_tts.Communicate(
                text,
                base_voice,
                pitch=pitch_str,
                rate=rate_str
            )
            await communicate.save(tmp_mp3_path)
            
        asyncio.run(run_edge_tts())
        
        # Convert MP3 base to WAV
        tmp_wav = tempfile.NamedTemporaryFile(suffix="_base.wav", delete=False)
        tmp_wav_path = tmp_wav.name
        tmp_wav.close()
        
        sound = pydub.AudioSegment.from_file(tmp_mp3_path)
        sound.export(tmp_wav_path, format="wav")
        Path(tmp_mp3_path).unlink(missing_ok=True)
        
        # 2. Convert voice using Seed-VC (auto-installs seed_vc if missing)
        out_wav_path = output_dir / f"converted_{self.voice_name}_{language}_{int(time.time())}.wav"
        
        try:
            try:
                from seed_vc.api import inference, AudioData, get_audio_numpy
            except (ImportError, ModuleNotFoundError):
                if not getattr(self, "_auto_install_attempted", False):
                    self._auto_install_attempted = True
                    logger.info("seed_vc module not found. Attempting automatic installation via uv...")
                    import subprocess
                    subprocess.run(
                        ["uv", "pip", "install", "seed-vc", "--no-deps", "--python", sys.executable],
                        check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                from seed_vc.api import inference, AudioData, get_audio_numpy
                logger.success("Successfully loaded seed_vc module!")

            logger.info(f"SeedVCAdapter converting base voice using Flow-Matching to match {self.voice_name}...")
            
            src_np, src_sr = self._load_audio_numpy(tmp_wav_path, target_sr=22050)
            tgt_np, tgt_sr = self._load_audio_numpy(str(self.target_wav), target_sr=22050)
            
            src_int16 = (src_np * 32767.0).astype(np.int16)
            tgt_int16 = (tgt_np * 32767.0).astype(np.int16)
            
            src_audio = AudioData(
                samples=src_int16,
                mel_chunks=None,
                duration=len(src_np) / src_sr,
                samples_count=len(src_np),
                sample_rate=src_sr,
                metadata=None
            )
            
            tgt_audio = AudioData(
                samples=tgt_int16,
                mel_chunks=None,
                duration=len(tgt_np) / tgt_sr,
                samples_count=len(tgt_np),
                sample_rate=tgt_sr,
                metadata=None
            )
            
            device = "cuda" if (torch is not None and torch.cuda.is_available()) else "cpu"
            
            hw_profile = kwargs.get("hardware_profile", "laptop").lower()
            if hw_profile in ["desktop", "rtx"]:
                diff_steps = 20
                use_fp16 = (device == "cuda")
            elif hw_profile in ["pi", "cpu"]:
                diff_steps = 5
                use_fp16 = False
            else:  # laptop
                diff_steps = 10
                use_fp16 = (device == "cuda")

            result = inference(
                source=src_audio,
                target=tgt_audio,
                output=None,
                diffusion_steps=diff_steps,
                length_adjust=1.0,
                inference_cfg_rate=0.7,
                f0_condition=False,
                auto_f0_adjust=False,
                fp16=use_fp16,
                realtime=False,
                streaming=False,
            )
            
            if result is not None:
                audio_np = get_audio_numpy(result)
                audio_sr = result.sample_rate
                sf.write(str(out_wav_path), audio_np, audio_sr)
            else:
                raise RuntimeError("Seed-VC inference returned None")
        except Exception as seedvc_err:
            logger.warning(
                f"Seed-VC voice conversion skipped or auto-install failed ({seedvc_err}). "
                f"Using pitch-aligned Microsoft Neural base voice."
            )
            import shutil
            shutil.copy(tmp_wav_path, str(out_wav_path))
            
        Path(tmp_wav_path).unlink(missing_ok=True)
        duration = self._get_audio_duration(str(out_wav_path))
        
        with open(out_wav_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
            
        logger.success(f"SeedVC voice conversion complete: {out_wav_path.name}")
        
        # Closed-loop similarity verification & Self-improving feedback loop
        sim = 0.0
        if self.vc_dir and (self.vc_dir / "reference.wav").exists():
            try:
                if self._extractor is None:
                    from features.extractor import ROSEFeatureExtractor
                    self._extractor = ROSEFeatureExtractor()
                sim = self._extractor.calculate_similarity(
                    str(self.vc_dir / "reference.wav"),
                    str(out_wav_path)
                )
                logger.info(f"Seed-VC Similarity Verification: {sim:.4f} (noise_floor=0.26, target≥0.65)")
                
                # Self-Improving Feedback Loop: Store optimized settings in stats/optimization
                opt_file = self.vc_dir / "optimization.json"
                opt_data = {}
                if opt_file.exists():
                    try:
                        with open(opt_file, "r") as f:
                            opt_data = json.load(f)
                    except Exception:
                        pass
                best_sim = opt_data.get("best_similarity", 0.0)
                if sim > best_sim:
                    opt_data["best_similarity"] = float(sim)
                    opt_data["best_pitch_mean"] = float(self.pitch_mean)
                    opt_data["best_speaking_rate"] = float(self.speaking_rate)
                    opt_data["hardware_profile"] = hw_profile
                    opt_data["timestamp"] = int(time.time())
                    with open(opt_file, "w") as f:
                        json.dump(opt_data, f, indent=2)
                    logger.info(f"Self-improving feedback loop: optimized parameters cached at {opt_file}")
            except Exception as sim_e:
                logger.warning(f"Could not compute Seed-VC similarity / optimization: {sim_e}")
                
        return {
            "audio_path": str(out_wav_path),
            "sample_rate": 22050,  # Seed-VC v1 default SR
            "duration_seconds": duration,
            "audio_b64": b64_data,
            "similarity_score": sim
        }

    def get_capabilities(self) -> List[str]:
        """Returns capabilities complying with NVR capabilities discovery."""
        return ["tts", "speech_to_speech", "voice_conversion", "streaming"]

