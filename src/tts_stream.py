"""
Text-to-Speech Streaming Module
Buffers incoming text chunks and sends them for speech generation when ready.
Integrates with Azure Cognitive Services TTS API.
"""
import json
import logging
import requests
import time
from typing import Generator, Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from threading import Thread, Lock

from src.org_config import OrgConfigData, TTSModel

logger = logging.getLogger(__name__)

import asyncio
import time
import logging
import json
import requests
from typing import Generator, Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from threading import Thread, Lock
import xml.etree.ElementTree as ET

from src.org_config import OrgConfigData, TTSModel

logger = logging.getLogger(__name__)

@dataclass
class TTSChunk:
    """Represents a chunk of text to be converted to speech"""
    text: str
    timestamp: float
    language: str
    model: TTSModel

class TTSBuffer:
    """
    Buffers text chunks and triggers TTS generation when conditions are met:
    - Text has 3 or more words
    - Chunk has waited for more than 2 seconds
    """
    
    def __init__(self, subscription_key: str, region: str = "southeastasia", 
                 min_words: int = 3, max_wait_seconds: float = 2.0,
                 chunk_callback: Optional[Callable[[str, bytes], None]] = None,
                 completion_callback: Optional[Callable[[], None]] = None):
        """
        Initialize TTS buffer
        
        Args:
            subscription_key: Azure TTS subscription key
            region: Azure region (defaults to southeastasia)
            min_words: Minimum words before triggering TTS (default: 3)
            max_wait_seconds: Maximum wait time before triggering TTS (default: 2.0)
            chunk_callback: Optional callback for when audio chunks are ready
            completion_callback: Optional callback when all processing is complete
        """
        self.subscription_key = subscription_key
        self.region = region
        self.base_url = f"https://{region}.tts.speech.microsoft.com"
        self.min_words = min_words
        self.max_wait_seconds = max_wait_seconds
        self.chunk_callback = chunk_callback
        self.completion_callback = completion_callback
        
        # Buffer state
        self._buffer = ""
        self._buffer_timestamp = None
        self._lock = Lock()
        self._processing = False
        self._has_pending_text = False
        
        # Timer for max wait
        self._timer_thread = None
        
        logger.info(f"Initialized TTS buffer with region: {region}, min_words: {min_words}, max_wait: {max_wait_seconds}s")
    
    def add_text(self, text: str, language: str, model: TTSModel) -> None:
        """
        Add text to the buffer
        
        Args:
            text: Text chunk to add
            language: Language code for the text
            model: TTS model configuration to use
        """
        with self._lock:
            current_time = time.time()
            
            # If buffer is empty, set initial timestamp
            if not self._buffer:
                self._buffer_timestamp = current_time
            
            # Add text to buffer
            self._buffer += text
            self._has_pending_text = True
            
            # Check if we should trigger TTS
            word_count = len(self._buffer.split())
            time_waited = current_time - self._buffer_timestamp if self._buffer_timestamp else 0
            
            logger.debug(f"Buffer state: {word_count} words, {time_waited:.1f}s waited, text: '{self._buffer[:50]}...'")
            
            should_trigger = (
                word_count >= self.min_words or 
                time_waited >= self.max_wait_seconds
            )
            
            if should_trigger and not self._processing:
                self._trigger_tts(language, model)
            elif not self._processing:
                # Start or restart timer
                self._start_timer(language, model)
    
    def finalize(self) -> None:
        """
        Signal that no more text will be added and complete processing
        """
        with self._lock:
            if self._buffer.strip():
                # Process any remaining text
                return  # Let the flush handle completion
            elif not self._processing:
                # No text to process and not currently processing
                self._has_pending_text = False
                if self.completion_callback:
                    self.completion_callback()
    
    def flush(self, language: str, model: TTSModel) -> None:
        """
        Force flush any remaining text in buffer
        
        Args:
            language: Language code for the text
            model: TTS model configuration to use
        """
        with self._lock:
            # Set the flag to indicate we're in flush/completion mode
            self._has_pending_text = True
            
            if self._buffer.strip() and not self._processing:
                self._trigger_tts(language, model)
            elif not self._buffer.strip() and not self._processing:
                # No text to process and not currently processing, mark as complete
                self._has_pending_text = False
                if self.completion_callback:
                    self.completion_callback()
    
    def _start_timer(self, language: str, model: TTSModel) -> None:
        """Start timer for max wait timeout"""
        if self._timer_thread and self._timer_thread.is_alive():
            return
        
        def timer_worker():
            time.sleep(self.max_wait_seconds)
            with self._lock:
                if self._buffer.strip() and not self._processing:
                    time_waited = time.time() - self._buffer_timestamp if self._buffer_timestamp else 0
                    if time_waited >= self.max_wait_seconds:
                        logger.debug(f"Timer triggered TTS after {time_waited:.1f}s")
                        self._trigger_tts(language, model)
        
        self._timer_thread = Thread(target=timer_worker, daemon=True)
        self._timer_thread.start()
    
    def _trigger_tts(self, language: str, model: TTSModel) -> None:
        """
        Trigger TTS generation for current buffer content
        
        Args:
            language: Language code for the text
            model: TTS model configuration to use
        """
        if not self._buffer.strip():
            return
        
        text_to_process = self._buffer.strip()
        self._buffer = ""
        self._buffer_timestamp = None
        self._processing = True
        
        logger.info(f"Triggering TTS for text: '{text_to_process[:100]}...' ({len(text_to_process.split())} words)")
        
        # Process TTS in background thread
        def tts_worker():
            try:
                audio_data = self._generate_speech(text_to_process, language, model)
                if audio_data and self.chunk_callback:
                    self.chunk_callback(text_to_process, audio_data)
            except Exception as e:
                logger.error(f"TTS generation failed: {str(e)}")
            finally:
                with self._lock:
                    self._processing = False
                    # Check if we're completely done (no buffer and no pending text)
                    if not self._buffer.strip() and self._has_pending_text:
                        # Buffer is empty and we had pending text, mark as complete
                        self._has_pending_text = False
                        if self.completion_callback:
                            self.completion_callback()
        
        thread = Thread(target=tts_worker, daemon=True)
        thread.start()
    
    def _generate_speech(self, text: str, language: str, model: TTSModel) -> Optional[bytes]:
        """
        Generate speech using Azure TTS API
        
        Args:
            text: Text to convert to speech
            language: Language code
            model: TTS model configuration
            
        Returns:
            Audio data as bytes, or None if failed
        """
        try:
            # Create SSML
            ssml = self._create_ssml(text, language, model)
            
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
                logger.error(f"TTS API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            return None
    
    def _create_ssml(self, text: str, language: str, model: TTSModel) -> str:
        """
        Create SSML for the text
        
        Args:
            text: Text to convert
            language: Language code
            model: TTS model configuration
            
        Returns:
            SSML string
        """
        # Clean text for SSML
        cleaned_text = self._clean_text_for_ssml(text)
        
        # Build SSML
        ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{language}">
    <voice name="{model.name}">'''
        
        # Add pitch if specified
        if model.pitch:
            ssml += f'<prosody pitch="{model.pitch}">'
        
        ssml += cleaned_text
        
        if model.pitch:
            ssml += '</prosody>'
        
        ssml += '''
    </voice>
</speak>'''
        
        return ssml
    
    def _clean_text_for_ssml(self, text: str) -> str:
        """
        Clean text for SSML by escaping special characters
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text safe for SSML
        """
        # Escape XML special characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')
        
        # Remove or replace problematic characters
        text = text.replace('\n', ' ')
        text = text.replace('\r', ' ')
        text = text.replace('\t', ' ')
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text

class TTSStreamer:
    """
    Main TTS streaming coordinator
    Manages multiple language buffers and coordinates TTS generation
    """
    
    def __init__(self, org_config: OrgConfigData, chunk_callback: Optional[Callable[[str, str, bytes], None]] = None,
                 completion_callback: Optional[Callable[[], None]] = None):
        """
        Initialize TTS streamer with organization configuration
        
        Args:
            org_config: Organization configuration containing TTS settings
            chunk_callback: Optional callback for audio chunks (text, language, audio_data)
            completion_callback: Optional callback when all TTS processing is complete
        """
        self.org_config = org_config
        self.chunk_callback = chunk_callback
        self.completion_callback = completion_callback
        
        # Validate TTS config
        if not org_config.tts or not org_config.tts.azure:
            raise ValueError("Azure TTS configuration not found in organization config")
        
        self.azure_config = org_config.tts.azure
        self.subscription_key = self.azure_config.subscriptionKey
        
        # Create buffers for each language/model
        self.buffers: Dict[str, TTSBuffer] = {}
        
        # Track active processing
        self._active_buffers = set()
        self._completion_lock = Lock()
        
        logger.info(f"Initialized TTS streamer with {len(self.azure_config.models)} TTS models")
    
    def get_model_for_language(self, language: str) -> Optional[TTSModel]:
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
        return {
            "language": language,
            "name": "es-ES-XimenaMultilingualNeura",  # Fallback to first model
            "pitch": None,
            "phonemeUrl": None
        }
    
    def add_text_chunk(self, text: str, language: str) -> None:
        """
        Add a text chunk for TTS processing
        
        Args:
            text: Text chunk to process
            language: Language code for the text
        """
        # Get model for language
        model = self.get_model_for_language(language)
        logger.info(f"Adding text chunk for language '{language}': '{text[:50]}...'")
        if not model:
            logger.warning(f"Skipping TTS for unsupported language: {language}")
            return
        
        # Get or create buffer for this language
        buffer_key = f"{language}_{model.name}"
        if buffer_key not in self.buffers:
            def audio_callback(processed_text: str, audio_data: bytes):
                if self.chunk_callback:
                    self.chunk_callback(processed_text, language, audio_data)
            
            def buffer_completion_callback():
                """Called when a buffer completes processing"""
                with self._completion_lock:
                    self._active_buffers.discard(buffer_key)
                    if not self._active_buffers and self.completion_callback:
                        logger.info("All TTS buffers completed")
                        self.completion_callback()
            
            self.buffers[buffer_key] = TTSBuffer(
                subscription_key=self.subscription_key,
                region="southeastasia",  # As specified in the request
                chunk_callback=audio_callback,
                completion_callback=buffer_completion_callback
            )
        
        # Track this buffer as active
        with self._completion_lock:
            self._active_buffers.add(buffer_key)
        
        # Add text to buffer
        self.buffers[buffer_key].add_text(text, language, model)
    
    def flush_all(self) -> None:
        """Flush all buffers to generate remaining TTS"""
        for language_model, buffer in self.buffers.items():
            language = language_model.split('_')[0]
            model = self.get_model_for_language(language)
            if model:
                # Track this buffer as active when flushing
                with self._completion_lock:
                    self._active_buffers.add(language_model)
                buffer.flush(language, model)
        
        # If no buffers were active, signal completion immediately
        with self._completion_lock:
            if not self._active_buffers and self.completion_callback:
                logger.info("No active TTS buffers, marking as complete")
                self.completion_callback()
    
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

# Example usage and testing
if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(level=logging.INFO)
    
    # Test with sample org config (would normally come from org_config.py)
    from src.org_config import load_org_config
    
    try:
        # Load a sample config
        config = load_org_config("your-config-id-here")
        if config:
            def audio_ready(text: str, language: str, audio_data: bytes):
                print(f"Audio ready for text: '{text[:50]}...' (language: {language}, size: {len(audio_data)} bytes)")
            
            streamer = TTSStreamer(config, chunk_callback=audio_ready)
            
            # Test adding chunks
            streamer.add_text_chunk("Hello", "en-US")
            streamer.add_text_chunk(" world", "en-US")
            streamer.add_text_chunk(" this is", "en-US")
            streamer.add_text_chunk(" a test", "en-US")
            
            # Wait for processing
            time.sleep(3)
            
            # Flush remaining
            streamer.flush_all()
            
            # Wait for final processing
            time.sleep(2)
        else:
            print("Could not load org config")
            
    except Exception as e:
        print(f"Test failed: {e}")