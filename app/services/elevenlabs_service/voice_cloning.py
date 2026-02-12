"""
ElevenLabs Voice Cloning Service for Rain Check.
Handles professional voice cloning (PVC) and voice management.
"""

import os
import logging
import httpx
from typing import List, Dict, Optional
from app.config import ELEVENLABS_API_KEY

logger = logging.getLogger(__name__)

class VoiceCloningService:
    """
    Service for managing custom voice models using ElevenLabs.
    """
    
    BASE_URL = "https://api.elevenlabs.io/v1/voices"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or ELEVENLABS_API_KEY
        self.headers = {"xi-api-key": self.api_key}

    async def list_voices(self) -> List[Dict]:
        """List all available voices (pre-built + cloned)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(self.BASE_URL, headers=self.headers)
            response.raise_for_status()
            return response.json().get('voices', [])

    async def clone_voice(self, name: str, audio_files: List[str], description: str = "") -> str:
        """
        Initiate a professional voice cloning process.
        
        Args:
            name: Name for the custom voice
            audio_files: List of paths to audio samples
            description: Optional description of the voice
            
        Returns:
            The newly created voice_id
        """
        url = f"{self.BASE_URL}/add"
        
        # Prepare multipart/form-data
        files = [
            ('files', (os.path.basename(f), open(f, 'rb'), 'audio/mpeg')) 
            for f in audio_files
        ]
        
        data = {
            'name': name,
            'description': description,
            'labels': '{"category": "cloned", "use_case": "workplace_callout"}'
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=self.headers, data=data, files=files)
                response.raise_for_status()
                result = response.json()
                voice_id = result.get('voice_id')
                logger.info(f"Successfully initiated cloning for '{name}': {voice_id}")
                return voice_id
        finally:
            # Explicitly close file handles
            for _, (_, f_obj, _) in files:
                f_obj.close()

    async def delete_voice(self, voice_id: str) -> bool:
        """Delete a cloned voice model."""
        url = f"{self.BASE_URL}/{voice_id}"
        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=self.headers)
            return response.status_code == 200
