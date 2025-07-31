"""
TTS Handler Module
Handles all interactions with Azure TTS API and future caching functionality.
"""
import logging
import requests
import hashlib
import re
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from .audio_helper import AudioProcessor

if TYPE_CHECKING:
    from .tts_stream import SSMLFormatter

try:
    from .org_config import TTSModel
    from .azure_storage_handler import azure_storage_handler
except ImportError:
    # Handle case where module is imported from different context
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from src.org_config import TTSModel
    from src.azure_storage_handler import azure_storage_handler

logger = logging.getLogger(__name__)

class TTSHandler:
    """
    Handles all TTS API interactions with Azure Cognitive Services.
    Centralizes TTS generation and provides caching capabilities.
    """
    
    def __init__(self, subscription_key: str, region: str = "southeastasia", silence_threshold: float = 0.05, enable_trimming: bool = True):
        """
        Initialize TTS handler with Azure configuration
        
        Args:
            subscription_key: Azure subscription key
            region: Azure region (default: southeastasia)
            silence_threshold: Energy threshold for silence detection (0.05 = 5% of max energy)
            enable_trimming: Whether to enable audio trimming (can be disabled for speed)
        """
        self.subscription_key = subscription_key
        self.region = region
        self.base_url = f"https://{self.region}.tts.speech.microsoft.com"
        
        # Initialize audio processor
        self.audio_processor = AudioProcessor(silence_threshold=silence_threshold, enable_trimming=enable_trimming)
    
    def _trim_silence(self, audio_data: bytes) -> bytes:
        """
        Trim silence from the beginning and end of audio data
        Delegates to AudioProcessor for actual processing
        
        Args:
            audio_data: Raw PCM audio data as bytes (16-bit, 16kHz, mono)
            
        Returns:
            Trimmed audio data as bytes
        """
        return self.audio_processor.trim_silence(audio_data)
    
    def _convert_pcm_to_wav(self, pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
        """
        Convert raw PCM audio data to WAV format
        Delegates to AudioProcessor for actual processing
        
        Args:
            pcm_data: Raw PCM audio data as bytes (16-bit, signed)
            sample_rate: Sample rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1 for mono)
            sample_width: Sample width in bytes (default: 2 for 16-bit)
            
        Returns:
            WAV formatted audio data as bytes
        """
        return self.audio_processor.convert_pcm_to_wav(pcm_data, sample_rate, channels, sample_width)
    
    def generate_speech(self, text: str, ssml_formatter: "SSMLFormatter", model: TTSModel, chunk_order: int = 0) -> Optional[bytes]:
        """
        Generate speech using Azure TTS API with caching
        
        Args:
            text: Plain text content to convert to speech
            ssml_formatter: SSMLFormatter instance to create SSML
            model: TTSModel instance containing voice configuration
            chunk_order: Order number for SSML generation
            
        Returns:
            Audio data as bytes, or None if failed
        """
        try:
            # Create SSML using the formatter
            ssml, phoneme_text = ssml_formatter.create_ssml(text, model, chunk_order)
            
            # Extract language and model info for caching
            language = getattr(model, 'language', 'en-US')
            model_name = getattr(model, 'name', 'unknown')
            
            # Generate cache key
            cache_key = self._generate_cache_key(phoneme_text, language, model_name)
            logger.info("Checking cache for audio: text='%s', language='%s', model='%s'", text[:50], language, model_name)
            # Try to get cached audio first
            cached_audio = azure_storage_handler.get_cached_audio(cache_key)
            if cached_audio:
                logger.info(f"Using cached audio: {cache_key}")
                return cached_audio
            
            # Generate new audio via Azure TTS API
            logger.debug(f"Generating new audio for: {cache_key}")
            audio_data = self._call_azure_tts_api(ssml)
            
            if audio_data:
                # Trim silence from the generated audio if enabled
                if self.audio_processor.enable_trimming:
                    trimmed_audio = self._trim_silence(audio_data)
                    logger.info(f"Generated and trimmed audio: {cache_key}")
                else:
                    trimmed_audio = audio_data
                    logger.info(f"Generated audio (no trimming): {cache_key}")
                
                # Convert PCM to WAV format for easier client playback
                wav_audio = self._convert_pcm_to_wav(trimmed_audio)
                logger.info(f"Converted to WAV format and cached: {cache_key}")
                
                # Cache the WAV audio asynchronously (fire and forget)
                azure_storage_handler.save_audio_async(cache_key, wav_audio)
                return wav_audio
            else:
                logger.error("Failed to generate speech via Azure TTS API")
                return None
                
        except Exception as e:
            logger.error(f"Error in generate_speech: {str(e)}")
            return None
    
    def _generate_cache_key(self, text_content: str, language: str, model_name: str) -> str:
        """
        Generate cache key for the audio file
        
        Args:
            text_content: Plain text content to be spoken
            language: Language code
            model_name: TTS model name (e.g., "en-US-AriaNeural")
            
        Returns:
            Cache key in format: language/model_name/hash.wav (WAV format)
        """
        # Sanitize model name for use in file path (remove invalid characters)
        safe_model_name = re.sub(r'[^\w\-_.]', '_', model_name)
        
        # Create hash from text content (including language and model for uniqueness)
        hash_input = f"{text_content}|{language}|{model_name}".encode('utf-8')
        text_hash = hashlib.sha256(hash_input).hexdigest()[:16]  # Use first 16 chars for shorter filename
        
        # Create cache key in the format: language/model_name/hash.wav (WAV format)
        cache_key = f"{language}/{safe_model_name}/{text_hash}.wav"
        return cache_key
    
    def _call_azure_tts_api(self, ssml: str) -> Optional[bytes]:
        """
        Make the actual call to Azure TTS API
        
        Args:
            ssml: SSML content to convert to speech
            
        Returns:
            Audio data as bytes, or None if failed
        """
        try:
            # Make TTS request
            headers = {
                'Ocp-Apim-Subscription-Key': self.subscription_key,
                'Content-Type': 'application/ssml+xml',
                'X-Microsoft-OutputFormat': 'raw-16khz-16bit-mono-pcm',  # Use raw PCM for fastest processing
                'User-Agent': 'robotics-core-python'
            }
            
            url = f"{self.base_url}/cognitiveservices/v1"
            
            logger.debug(f"Making TTS request to {url}")
            logger.info(f"SSML content: {ssml}")
            response = requests.post(url, headers=headers, data=ssml.encode('utf-8'), timeout=30)
            
            if response.status_code == 200:
                logger.info(f"TTS generation successful, audio size: {len(response.content)} bytes")
                return response.content
            else:
                logger.error(f"TTS API error: {response.status_code} - {response.text or response.reason}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling Azure TTS API: {str(e)}")
            return None
    
    def get_available_voices(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of available voices from Azure TTS API
        
        Returns:
            List of voice information or None if failed
        """
        try:
            headers = {
                'Ocp-Apim-Subscription-Key': self.subscription_key
            }
            
            url = f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/voices/list"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get voices list: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting voices list: {str(e)}")
            return None
    
    def clear_cache_for_text(self, text: str, language: str = "en-US", model_name: str = "en-US-AriaNeural") -> bool:
        """
        Clear cached audio for specific text
        
        Args:
            text: The text content
            language: Language code
            model_name: TTS model name
            
        Returns:
            True if cache was cleared successfully
        """
        try:
            cache_key = self._generate_cache_key(text, language, model_name)
            return azure_storage_handler.delete_cached_audio(cache_key)
        except Exception as e:
            logger.error(f"Error clearing cache for text: {str(e)}")
            return False
    
    def get_cache_info(self, text: str, language: str = "en-US", model_name: str = "en-US-AriaNeural") -> Dict[str, Any]:
        """
        Get cache information for specific text
        
        Args:
            text: The text content
            language: Language code
            model_name: TTS model name
            
        Returns:
            Dictionary with cache information
        """
        try:
            cache_key = self._generate_cache_key(text, language, model_name)
            cached_audio = azure_storage_handler.get_cached_audio(cache_key)
            
            return {
                "cache_key": cache_key,
                "is_cached": cached_audio is not None,
                "audio_size": len(cached_audio) if cached_audio else 0
            }
        except Exception as e:
            logger.error(f"Error getting cache info: {str(e)}")
            return {
                "cache_key": None,
                "is_cached": False,
                "audio_size": 0,
                "error": str(e)
            }