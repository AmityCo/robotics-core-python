"""
Text-to-Speech Streaming Module
Simplified version that buffers text in chunks and sends them for speech generation when ready.
Integrates with Azure Cognitive Services TTS API.
"""
import logging
import requests
import time
import re
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass

from src.org_config import OrgConfigData, TTSModel
from src.requests_handler import get as cached_get
from src.tts_handler import TTSHandler
from src.phoneme_manager import PhonemeManager

logger = logging.getLogger(__name__)

class SSMLFormatter:
    """
    Handles SSML formatting for Azure TTS with phoneme processing and advanced features
    """
    
    def __init__(self, azure_config, remove_bracketed_words: bool = False):
        """
        Initialize SSML formatter
        
        Args:
            azure_config: Azure TTS configuration
            remove_bracketed_words: Whether to remove text in brackets
        """
        self.azure_config = azure_config
        self.remove_bracketed_words = remove_bracketed_words
        self.phonemes_loaded = False
        # Cache for pre-compiled patterns per language - now managed by PhonemeManager
        self._phoneme_patterns_cache: Dict[str, List[tuple]] = {}
        
    async def load_phonemes(self) -> None:
        """Load phoneme data from configured URLs using PhonemeManager"""
        if self.phonemes_loaded:
            return
            
        try:
            # Get phoneme patterns cache from PhonemeManager
            self._phoneme_patterns_cache = await PhonemeManager.get_phoneme_patterns_cache(self.azure_config)
            self.phonemes_loaded = True
            logger.info(f"Loaded phoneme patterns for {len(self._phoneme_patterns_cache)} languages")
            
        except Exception as e:
            logger.error(f"Failed to load phonemes: {str(e)}")
    
    def _precompile_phoneme_patterns(self) -> None:
        """Pre-compile regex patterns for all languages to improve performance"""
        # This method is now deprecated since PhonemeManager handles pattern compilation
        # Keeping for backward compatibility but it's a no-op
        pass
    
    def _compile_patterns_for_language(self, language: str) -> List[tuple]:
        """Compile regex patterns for a specific language"""
        # This method is now deprecated since PhonemeManager handles pattern compilation
        # Keeping for backward compatibility but delegating to cached patterns
        return self._phoneme_patterns_cache.get(language, self._phoneme_patterns_cache.get('default', []))
    
    def transform_text(self, text: str) -> str:
        """
        Transform text by removing brackets and replacing illegal characters
        
        Args:
            text: Input text to transform
            
        Returns:
            Transformed text
        """
        transformed = text
        
        # Remove bracketed words if configured
        if self.remove_bracketed_words:
            transformed = re.sub(r'\(.*?\)', '', transformed)
        
        return transformed
    
    def transform_with_phonemes(self, text: str, language: str) -> str:
        """
        Transform text by applying phoneme substitutions
        
        Args:
            text: Text to transform
            language: Language code
            
        Returns:
            Text with phoneme tags applied
        """
        # Early return for empty text
        if not text or not text.strip():
            return text
        
        language_lower = language.lower()
        
        # Use pre-compiled patterns if available
        patterns_and_replacements = self._phoneme_patterns_cache.get(
            language_lower, 
            self._phoneme_patterns_cache.get('default', [])
        )
        
        if not patterns_and_replacements:
            return text
        
        current_text = text
        
        # Apply all transformations using pre-compiled patterns
        for pattern, replacement_tag, name_key in patterns_and_replacements:
            # Quick check if the name exists in the text before expensive regex
            if name_key.lower() not in current_text.lower():
                continue
                
            def replace_func(match):
                if match.group(1):  # Already tagged
                    return match.group(0)
                elif match.group(2):  # Untagged word
                    return replacement_tag
                else:
                    return match.group(0)
            
            current_text = pattern.sub(replace_func, current_text)
        
        return current_text
    
    def to_bcp47_normalized(self, language: str) -> str:
        """Convert language code to BCP47 normalized format"""
        # Simple conversion - you might want to expand this based on your needs
        parts = language.split('-')
        if len(parts) >= 2:
            return f"{parts[0].lower()}-{parts[1].upper()}"
        return language
    
    def create_ssml(self, text: str, model: TTSModel, order: int = 0) -> str:
        """
        Create advanced SSML with all features from Kotlin implementation
        
        Args:
            text: Text to convert
            model: TTS model configuration
            order: Order number for silence timing
            
        Returns:
            Complete SSML string
        """
        # Transform text
        transformed_text = self.transform_text(text)
        
        # Apply phoneme transformations
        if self.phonemes_loaded:
            start_time = time.time()
            phoneme_text = self.transform_with_phonemes(transformed_text, model.language)
            logger.info(f"Phoneme transformation took {time.time() - start_time:.2f} seconds")
        else:
            phoneme_text = transformed_text
        
        # Normalize language code
        format_language = self.to_bcp47_normalized(model.language)
        
        # Create timestamp for lexicon caching
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Determine leading silence
        leading = "0ms"
        
        # Get model properties with defaults
        model_name = getattr(model, 'name', 'en-US-AriaNeural')
        if not hasattr(model, 'pitch'):
            pitch = 'medium'
        else:
            pitch = getattr(model, 'pitch')
        # if pitch is none, default to 'medium'
        if pitch is None:
            pitch = 'medium'
        # Get rate, default to '1.0' if not set
        # check if model has rate attribute
        if not hasattr(model, 'rate'):
            rate = '1.0'
        else:
            rate = getattr(model, 'rate')
        if rate is None:
            rate = '1.0'
        
        # Create lexicon tag if available and phonemes weren't applied
        lexicon_tag = ""
        if (hasattr(self.azure_config, 'lexiconURL') and 
            self.azure_config.lexiconURL and 
            self.azure_config.lexiconURL not in ["null", ""] and
            transformed_text == phoneme_text):  # Only use lexicon if no phonemes were applied
            
            lexicon_url = f"{self.azure_config.lexiconURL}{format_language}.xml?timestamp={timestamp}"
            lexicon_tag = f'<lexicon uri="{lexicon_url}"/>'
        
        # Build complete SSML
        ssml = f'''<speak version="1.0" xml:lang="{format_language}" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts">
    <voice xml:lang="{format_language}" xml:gender="Female" name="{model_name}">
        {lexicon_tag}
        <mstts:silence type="Sentenceboundary" value="0ms"/>
        <mstts:silence type="Leading-exact" value="{leading}"/>
        <mstts:silence type="Tailing-exact" value="0ms"/>
        <prosody pitch="{pitch}" rate="{rate}">
            <lang xml:lang="{format_language}">
                {phoneme_text}
            </lang>
        </prosody>
    </voice>
</speak>'''
        
        return ssml, phoneme_text

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
    
    def has_minimum_words(self, min_words: int = 4) -> bool:
        """Check if chunk has minimum word count"""
        return self.word_count >= min_words
    
    def is_empty(self) -> bool:
        """Check if chunk is empty"""
        return not self.text.strip()

class TTSStreamer:
    """
    Main TTS streaming class that manages text chunks and triggers TTS generation.
    Processes text when <break/> keyword is detected for immediate speech generation.
    """
    
    def __init__(self, org_config: OrgConfigData, language: str, 
                 audio_callback: Optional[Callable[[str, bytes], None]] = None,
                 min_words: int = 4, remove_bracketed_words: bool = False):
        """
        Initialize TTS streamer with organization configuration for a specific language
        
        Args:
            org_config: Organization configuration containing TTS settings
            language: Language code for all text chunks
            audio_callback: Callback for when audio chunks are ready (text, audio_data)
            min_words: Minimum words before triggering TTS (kept for backward compatibility)
            remove_bracketed_words: Whether to remove text in brackets
            
        Note:
            Text processing is now triggered by <break/> keyword rather than word count.
            The min_words parameter is kept for backward compatibility but not actively used.
        """
        self.language = language
        self.audio_callback = audio_callback
        self.min_words = min_words
        
        # Validate TTS config
        if not org_config.tts or not org_config.tts.azure:
            raise ValueError("Azure TTS configuration not found in organization config")
        
        self.azure_config = org_config.tts.azure
        region = "southeastasia"
        
        # Initialize TTS handler
        self.tts_handler = TTSHandler(self.azure_config.subscriptionKey, region)
        
        # Get model for the specified language
        self.model = self._get_model_for_language(language)
        if not self.model:
            raise ValueError(f"No TTS model found for language: {language}")
        
        # Initialize SSML formatter
        self.ssml_formatter = SSMLFormatter(self.azure_config, remove_bracketed_words)
        
        # Current chunk being built
        self.current_chunk = TTSChunk("")
        self.chunk_order = 0  # Track order for SSML generation
        
        logger.info(f"Initialized TTS streamer for language: {language}, model: {self.model.name}, break-triggered processing enabled")
    
    async def initialize(self) -> None:
        """Initialize the TTS streamer by loading phonemes"""
        await self.ssml_formatter.load_phonemes()
        logger.info("TTS streamer initialization complete")
    
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
        # if thai language, name should be "th-TH-PremwadeeNeural
        if language.startswith('th-'):
            return type('TTSModel', (), {
                'language': language,
                'name': "th-TH-PremwadeeNeural",  # Fallback to a common Thai model
                'pitch': None,
                'phonemeUrl': None
            })()
        return type('TTSModel', (), {
            'language': language,
            'name': "es-ES-XimenaMultilingualNeural",  # Fallback to a common model
            'pitch': None,
            'phonemeUrl': None
        })()
    
    def append_text(self, text: str) -> None:
        """
        Append text to current chunk. If chunk contains <break/> keyword,
        process it and start a new chunk.
        
        Args:
            text: Text to append
        """
        logger.debug(f"Appending text: '{text}'")
        
        # Append text to current chunk
        self.current_chunk.append_text(text)
        
        # Check if we should process the current chunk by looking for <break/> keyword
        if "<break/>" in self.current_chunk.text:
            self._process_current_chunk_with_break()
    
    def flush(self) -> None:
        """
        Process any remaining text in the current chunk
        """
        if not self.current_chunk.is_empty():
            # First check if there are any <break/> markers to process
            if "<break/>" in self.current_chunk.text:
                self._process_current_chunk_with_break()
            
            # Process any remaining text after break processing
            if not self.current_chunk.is_empty():
                logger.info(f"Flushing remaining text: '{self.current_chunk.text}'")
                # During flush, we want to process ALL text, removing any <break/> markers
                text_to_process = self.current_chunk.text.replace("<break/>", "").strip()
                
                if text_to_process:  # Only process if there's actual content
                    # Generate speech for remaining text
                    audio_data = self._generate_speech(text_to_process)
                    
                    # Trigger callback if audio was generated successfully
                    if audio_data and self.audio_callback:
                        self.audio_callback(text_to_process, audio_data)
                
                # Clear the chunk
                self.current_chunk = TTSChunk("")
    
    def _process_current_chunk_with_break(self) -> None:
        """
        Process the current chunk when <break/> keyword is detected.
        Ships off the whole buffer up to and including the <break/> marker.
        """
        if self.current_chunk.is_empty():
            return
        
        text_to_process = self.current_chunk.text.strip()
        
        # Find the position of <break/> and split the text
        break_index = text_to_process.find("<break/>")
        if break_index != -1:
            # Include everything up to and including <break/>
            text_with_break = text_to_process[:break_index + len("<break/>")]
            remaining_text = text_to_process[break_index + len("<break/>"):]
            
            # Remove the <break/> tag from the text to be processed (it's just a marker)
            text_for_speech = text_with_break.replace("<break/>", "").strip()
            
            if text_for_speech:  # Only process if there's actual content
                logger.info(f"Processing chunk with break: '{text_for_speech[:100]}...'")
                
                # Generate speech for this chunk
                audio_data = self._generate_speech(text_for_speech)
                
                # Trigger callback if audio was generated successfully
                if audio_data and self.audio_callback:
                    self.audio_callback(text_for_speech, audio_data)
            
            # Create new chunk with any remaining text after <break/>
            self.current_chunk = TTSChunk(remaining_text.strip())
            self.chunk_order += 1
            
            # Check if the remaining text also contains <break/> and process recursively
            if "<break/>" in remaining_text:
                self._process_current_chunk_with_break()
        else:
            # This shouldn't happen since we checked for <break/> before calling this method
            logger.warning("_process_current_chunk_with_break called but no <break/> found")
    
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
        self.chunk_order += 1

    def _generate_speech(self, text: str) -> Optional[bytes]:
        """
        Generate speech using Azure TTS API via TTSHandler
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Audio data as bytes, or None if failed
        """
        try:
            # Use TTS handler with SSMLFormatter directly
            return self.tts_handler.generate_speech(text, self.ssml_formatter, self.model, self.chunk_order)
                
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            return None 
    
    def get_available_voices(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of available voices from Azure TTS API via TTSHandler
        
        Returns:
            List of voice information or None if failed
        """
        return self.tts_handler.get_available_voices()