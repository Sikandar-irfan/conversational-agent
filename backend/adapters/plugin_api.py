# rose/compiler/plugin_api.py
# Nexsora Voice Compiler (NVC) - Plugin API Interface
# Declares base classes, capabilities checks, and registry gates.

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Type, AsyncIterable, Optional
from loguru import logger

class PluginCapability:
    """Declared capabilities supported by voice compiler plugins."""
    TRAINING = "training"
    INFERENCE = "inference"
    STREAMING = "streaming"
    QUANTIZATION = "quantization"
    EMOTION = "emotion"
    MULTILINGUAL = "multilingual"
    EVALUATION = "evaluation"
    SPEECH_TO_SPEECH = "speech_to_speech"
    VOICE_CONVERSION = "voice_conversion"


class VoiceABI(ABC):
  """
  Stable Voice Application Binary Interface (v1.0).
  All synthesis backends (OmniVoice, XTTS, Seed-VC) implement exactly this interface.
  """
  @abstractmethod
  def load(self, rvp_path: str) -> bool:
      """Loads voice package files and returns success state."""
      pass

  @abstractmethod
  def unload(self) -> None:
      """Unloads weights and frees memory."""
      pass

  @abstractmethod
  def get_capabilities(self) -> List[str]:
      """Returns list of active capabilities supported by this plugin."""
      pass

  @abstractmethod
  def synthesize(self, text: str, language: str, **kwargs) -> Dict[str, Any]:
      """Synthesizes text/guide audio to PCM/float32 output format."""
      pass


class BaseModelPlugin(VoiceABI):
    """Abstract Base Class for voice models (e.g., XTTS, Seed-VC, FreeVC)."""
    
    @abstractmethod
    def train(self, dataset_path: str, config: Dict[str, Any], output_dir: str) -> str:
        """Trains the model on preprocessed datasets. Returns path to checkpoint."""
        pass

    @abstractmethod
    def optimize(self, checkpoint_dir: str, output_dir: str, config: Dict[str, Any]) -> str:
        """Applies pruning, merging of adapter weights, and quantization."""
        pass

    @abstractmethod
    def generate_fingerprint(self, checkpoint_dir: str) -> Dict[str, Any]:
        """Extracts speaker identity embeddings and acoustic characteristics."""
        pass


class BaseEvaluationPlugin(ABC):
    """Abstract Base Class for voice evaluation engines (e.g., ECAPA, WavLM, WER)."""
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Returns the list of evaluation capabilities."""
        pass

    @abstractmethod
    def calculate_metrics(self, test_audio_paths: List[str], 
                          ref_audio_paths: List[str]) -> Dict[str, float]:
        """Calculates raw audio quality metrics returning float values."""
        pass


class PluginRegistry:
    """Manages registered model and evaluation extensions dynamically."""
    _models: Dict[str, Type[BaseModelPlugin]] = {}
    _evaluators: Dict[str, Type[BaseEvaluationPlugin]] = {}

    @classmethod
    def register_model(cls, name: str, plugin_cls: Type[BaseModelPlugin]):
        cls._models[name.lower()] = plugin_cls
        logger.info(f"Registered Voice Model Plugin: {name}")

    @classmethod
    def register_evaluator(cls, name: str, plugin_cls: Type[BaseEvaluationPlugin]):
        cls._evaluators[name.lower()] = plugin_cls
        logger.info(f"Registered Voice Evaluator Plugin: {name}")

    @classmethod
    def get_model(cls, name: str) -> BaseModelPlugin:
        name_lower = name.lower()
        if name_lower not in cls._models:
            raise KeyError(f"Voice Model Plugin '{name}' is not registered.")
        return cls._models[name_lower]()

    @classmethod
    def get_evaluator(cls, name: str) -> BaseEvaluationPlugin:
        name_lower = name.lower()
        if name_lower not in cls._evaluators:
            raise KeyError(f"Voice Evaluator Plugin '{name}' is not registered.")
        return cls._evaluators[name_lower]()

