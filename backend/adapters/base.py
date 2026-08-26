# rose/adapters/base.py
# ROSE Backend Adapters — Base Adapter Class
# Defines the standard interface mapping generic voice packages to synthesizers.

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import sys
from pathlib import Path

from .plugin_api import VoiceABI

class BaseAdapter(VoiceABI):
    """
    Abstract interface that all target backend adapters must implement,
    complying with Voice ABI v1.0.
    """
    def load(self, rvp_path: str) -> bool:
        """ABI wrapper for load_voice_package."""
        try:
            self.load_voice_package(rvp_path)
            return True
        except Exception:
            return False

    def unload(self) -> None:
        """ABI interface method to clean up memory."""
        pass

    def get_capabilities(self) -> List[str]:
        """ABI interface method returning active model capabilities."""
        return ["tts", "voice_conversion"]
    
    @abstractmethod
    def load_voice_package(self, vc_path: str) -> None:
        """Loads the generic voice package files and configures internal state."""
        pass
        
    @abstractmethod
    def synthesize(self, text: str, language: str, **kwargs) -> Dict[str, Any]:
        """Generates waveform audio for the input text using the loaded voice package."""
        pass

