"""
Text-to-Speech Streaming Module
Simplified version that buffers text in chunks and sends them for speech generation when ready.
Integrates with Azure Cognitive Services TTS API.
"""
import logging
import requests
import time
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass

from src.org_config import OrgConfigData, TTSModel

logger = logging.getLogger(__name__)

@dataclass
class TTSChunk:
    """Represents a chunk of text to be converted to speech"""
    text: str
    word_count: int = 0
    
    def __post_init__(self):
        self.word_count = len(self.text.split(" "))
    
    def append_text(self, text: str) -> None:
        """Append text to this chunk"""
        self.text += text
        self.word_count = len(self.text.split(" "))
    
    def has_minimum_words(self, min_words: int = 3) -> bool:
        """Check if chunk has minimum word count"""
        return self.word_count >= min_words
    
    def is_empty(self) -> bool:
        """Check if chunk is empty"""
        return not self.text.strip()

class TTSStreamer:
    """
    Main TTS streaming class that manages text chunks and triggers TTS generation
    """
    
    def __init__(self, org_config: OrgConfigData, language: str, 
                 audio_callback: Optional[Callable[[str, bytes], None]] = None,
                 min_words: int = 3):
        """
        Initialize TTS streamer with organization configuration for a specific language
        
        Args:
            org_config: Organization configuration containing TTS settings
            language: Language code for all text chunks
            audio_callback: Callback for when audio chunks are ready (text, audio_data)
            min_words: Minimum words before triggering TTS (default: 3)
        """
        self.language = language
        self.audio_callback = audio_callback
        self.min_words = min_words
        
        # Validate TTS config
        if not org_config.tts or not org_config.tts.azure:
            raise ValueError("Azure TTS configuration not found in organization config")
        
        self.azure_config = org_config.tts.azure
        self.subscription_key = self.azure_config.subscriptionKey
        self.region = "southeastasia"
        self.base_url = f"https://{self.region}.tts.speech.microsoft.com"
        
        # Get model for the specified language
        self.model = self._get_model_for_language(language)
        if not self.model:
            raise ValueError(f"No TTS model found for language: {language}")
        
        # Current chunk being built
        self.current_chunk = TTSChunk("")
        
        logger.info(f"Initialized TTS streamer for language: {language}, model: {self.model.name}, min_words: {min_words}")
    
    def _get_model_for_language(self, language: str) -> Optional[TTSModel]:
        """
        Get the TTS model for a specific language
        
        Args:
            language: Language code (e.g., 'en-US', 'th-TH')
            
        Returns:
            TTSModel if found, None otherwise
        """
        for model in self.azure_config.models:
            if model.language == language:
                return model
        logger.debug(f"No TTS model found for language: {language}, returning default")
        # Return a default model structure if none found
        return type('TTSModel', (), {
            'language': language,
            'name': "en-US-AriaNeural",  # Fallback to a common model
            'pitch': None,
            'phonemeUrl': None
        })()
    
    def append_text(self, text: str) -> None:
        """
        Append text to current chunk. If chunk reaches minimum word count,
        process it and start a new chunk.
        
        Args:
            text: Text to append
        """
        logger.debug(f"Appending text: '{text}'")
        
        # Append text to current chunk
        self.current_chunk.append_text(text)
        
        # Check if we should process the current chunk
        if self.current_chunk.has_minimum_words(self.min_words):
            self._process_current_chunk()
    
    def flush(self) -> None:
        """
        Process any remaining text in the current chunk
        """
        if not self.current_chunk.is_empty():
            logger.info(f"Flushing remaining text: '{self.current_chunk.text}'")
            # During flush, we want to process ALL text, including the last word
            text_to_process = self.current_chunk.text.strip()
            
            # Generate speech for remaining text
            audio_data = self._generate_speech(text_to_process)
            
            # Trigger callback if audio was generated successfully
            if audio_data and self.audio_callback:
                self.audio_callback(text_to_process, audio_data)
            
            # Clear the chunk
            self.current_chunk = TTSChunk("")
    
    def _process_current_chunk(self) -> None:
        """
        Process the current chunk by converting it to speech and creating a new chunk
        """
        if self.current_chunk.is_empty():
            return
        
        text_to_process = self.current_chunk.text.strip()
        words = text_to_process.split(" ")
        
        # If we have more than one word, keep the last word for the next chunk
        # to ensure it's complete before processing
        if len(words) > 1:
            words_to_process = words[:-1]
            last_word = words[-1]
            text_to_process = " ".join(words_to_process)
        else:
            # If only one word, process it (this happens during flush)
            last_word = ""
        
        logger.info(f"Processing chunk: '{text_to_process[:100]}...' ({len(words_to_process) if len(words) > 1 else len(words)} words)")
        
        # Generate speech for this chunk
        audio_data = self._generate_speech(text_to_process)
        
        # Trigger callback if audio was generated successfully
        if audio_data and self.audio_callback:
            self.audio_callback(text_to_process, audio_data)
        
        # Create new chunk starting with the last word (if any)
        self.current_chunk = TTSChunk(last_word if last_word else "")

    def _generate_speech(self, text: str) -> Optional[bytes]:
        """
        Generate speech using Azure TTS API
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Audio data as bytes, or None if failed
        """
        try:
            # Create SSML
            ssml = self._create_ssml(text)
            
            # Make TTS request
            headers = {
                'Ocp-Apim-Subscription-Key': self.subscription_key,
                'Content-Type': 'application/ssml+xml',
                'X-Microsoft-OutputFormat': 'audio-16khz-128kbitrate-mono-mp3',
                'User-Agent': 'robotics-core-python'
            }
            
            url = f"{self.base_url}/cognitiveservices/v1"
            
            logger.debug(f"Making TTS request to {url}")
            logger.debug(f"SSML content: {ssml}")
            response = requests.post(url, headers=headers, data=ssml.encode('utf-8'), timeout=30)
            
            if response.status_code == 200:
                logger.info(f"TTS generation successful, audio size: {len(response.content)} bytes")
                return response.content
            else:
                logger.error(f"TTS API error: {response.status_code} - {response.text or response.reason}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            return None
    
    def _create_ssml(self, text: str) -> str:
        """
        Create SSML for the text
        
        Args:
            text: Text to convert
            
        Returns:
            SSML string
        """
        # Build SSML
        ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{self.language}">
    <voice name="{self.model.name}">'''
        
        # Add pitch if specified
        if hasattr(self.model, 'pitch') and self.model.pitch:
            ssml += f'<prosody pitch="{self.model.pitch}">'
        
        ssml += text
        
        if hasattr(self.model, 'pitch') and self.model.pitch:
            ssml += '</prosody>'
        
        ssml += '''
    </voice>
</speak>'''
        
        return ssml
    
    
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
            
            url = f"https://southeastasia.tts.speech.microsoft.com/cognitiveservices/voices/list"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get voices list: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting voices list: {str(e)}")
            return None