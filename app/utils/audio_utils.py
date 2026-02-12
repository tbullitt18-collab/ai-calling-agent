"""
Audio processing utilities for Rain Check.
Handles validation and feature extraction for voice cloning samples.
"""

import os
import logging
import wave
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class AudioValidator:
    """
    Validates audio samples for quality and format requirements.
    Target: 16kHz+ sample rate, Mono channel, minimum duration.
    """
    
    @staticmethod
    def validate_wav(file_path: str) -> Tuple[bool, str]:
        """
        Validate a WAV file's properties.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            with wave.open(file_path, 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                frames = wav_file.getnframes()
                duration = frames / float(sample_rate)
                
                if sample_rate < 16000:
                    return False, f"Sample rate too low ({sample_rate}Hz). Minimum 16000Hz required."
                
                if channels > 1:
                    return False, "Audio must be Mono channel."
                
                if duration < 10:
                    return False, f"Sample too short ({duration:.1f}s). Minimum 10 seconds per file."
                    
                return True, ""
        except Exception as e:
            logger.error(f"Validation error for {file_path}: {e}")
            return False, f"Could not parse audio file: {e}"

    @staticmethod
    def get_metadata(file_path: str) -> Dict:
        """Extract basic metadata from audio file."""
        # For prototype, only WAV is handled via wave module
        # In production, use pydub/ffmpeg for multi-format support
        if not file_path.lower().endswith('.wav'):
            return {"format": "unsupported", "info": "Detailed metadata requires WAV format"}
            
        try:
            with wave.open(file_path, 'rb') as wav_file:
                return {
                    "sample_rate": wav_file.getframerate(),
                    "channels": wav_file.getnchannels(),
                    "duration_seconds": wav_file.getnframes() / wav_file.getframerate(),
                    "extension": "wav"
                }
        except:
            return {"error": "failed to read metadata"}
