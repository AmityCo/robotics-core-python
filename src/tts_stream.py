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

logger = logging.getLogger(__name__)

@dataclass
class TtsPhoneme:
    """Represents a phoneme mapping for TTS"""
    name: str
    phoneme: Optional[str] = None
    sub: Optional[str] = None

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
        self.localized_phonemes: Dict[str, List[TtsPhoneme]] = {}
        self.global_phonemes: List[TtsPhoneme] = []
        self.phonemes_loaded = False
        
    async def load_phonemes(self) -> None:
        """Load phoneme data from configured URLs"""
        if self.phonemes_loaded:
            return
            
        try:
            # Load global phonemes if available
            if hasattr(self.azure_config, 'phonemeUrl') and self.azure_config.phonemeUrl:
                self.global_phonemes = await self._load_phoneme_data(self.azure_config.phonemeUrl)
                logger.info(f"Loaded {len(self.global_phonemes)} global phonemes")
            
            # Load localized phonemes for each model
            for model in self.azure_config.models:
                if hasattr(model, 'phonemeUrl') and model.phonemeUrl:
                    lang_phonemes = await self._load_phoneme_data(model.phonemeUrl)
                    if lang_phonemes:
                        self.localized_phonemes[model.language.lower()] = lang_phonemes
                        logger.info(f"Loaded {len(lang_phonemes)} phonemes for {model.language}")
            
            self.phonemes_loaded = True
            
        except Exception as e:
            logger.error(f"Failed to load phonemes: {str(e)}")
    
    async def _load_phoneme_data(self, url: str) -> List[TtsPhoneme]:
        """Load phoneme data from a URL using cached requests"""
        try:
            logger.info(f"Loading phoneme data from: {url}")
            
            # Use cached requests handler for better performance and caching
            response = await cached_get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                phonemes = []
                for item in data:
                    if isinstance(item, dict) and 'name' in item:
                        phoneme = TtsPhoneme(
                            name=item['name'],
                            phoneme=item.get('phoneme'),
                            sub=item.get('sub')
                        )
                        # Only add if it has either phoneme or sub
                        if phoneme.phoneme or phoneme.sub:
                            phonemes.append(phoneme)
                
                logger.info(f"Successfully loaded {len(phonemes)} phonemes from {url}")
                return phonemes
            else:
                logger.error(f"Failed to load phonemes from {url}: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error loading phonemes from {url}: {str(e)}")
        
        return []
    
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
        language_lower = language.lower()
        
        # Get phonemes for this language
        localized = self.localized_phonemes.get(language_lower, [])
        global_phonemes = self.global_phonemes
        
        # Get all available names
        all_names = []
        for phoneme in localized:
            if phoneme.name:
                all_names.append(phoneme.name)
        for phoneme in global_phonemes:
            if phoneme.name:
                all_names.append(phoneme.name)
        
        if not all_names:
            return text
        
        # Remove duplicates and sort by length (longest first)
        unique_names = list(set(all_names))
        sorted_names = sorted(unique_names, key=len, reverse=True)
        
        current_text = text
        
        for name_key in sorted_names:
            # Find phoneme item (prioritize localized)
            phoneme_item = None
            for phoneme in localized:
                if phoneme.name == name_key:
                    phoneme_item = phoneme
                    break
            
            if not phoneme_item:
                for phoneme in global_phonemes:
                    if phoneme.name == name_key:
                        phoneme_item = phoneme
                        break
            
            if not phoneme_item or (not phoneme_item.sub and not phoneme_item.phoneme):
                continue
            
            # Create replacement tag
            if phoneme_item.sub:
                replacement_tag = f'<sub alias="{phoneme_item.sub}">{name_key}</sub>'
            else:
                replacement_tag = f'<phoneme alphabet="ipa" ph="{phoneme_item.phoneme}">{name_key}</phoneme>'
            
            # Create regex pattern to avoid double-replacement
            escaped_name = re.escape(name_key)
            pattern = rf'(<(?:phoneme|sub)\b[^>]*>.*?</(?:phoneme|sub)>)|(\b{escaped_name}\b)'
            
            def replace_func(match):
                if match.group(1):  # Already tagged
                    return match.group(0)
                elif match.group(2):  # Untagged word
                    return replacement_tag
                else:
                    return match.group(0)
            
            current_text = re.sub(pattern, replace_func, current_text, flags=re.IGNORECASE | re.DOTALL)
        
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
            phoneme_text = self.transform_with_phonemes(transformed_text, model.language)
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
        
        return ssml

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
        # if thai language, name should be "th-TH-Neural2"
        if language.startswith('th-'):
            return type('TTSModel', (), {
                'language': language,
                'name': "th-TH-Neural2",  # Fallback to a common Thai model
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
    
    def _create_ssml(self, text: str) -> str:
        """
        Create SSML for the text (legacy method, kept for backward compatibility)
        
        Args:
            text: Text to convert
            
        Returns:
            SSML string
        """
        # Use the new formatter for backward compatibility
        return self.ssml_formatter.create_ssml(text, self.model, self.chunk_order)
    
    
    def get_available_voices(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of available voices from Azure TTS API via TTSHandler
        
        Returns:
            List of voice information or None if failed
        """
        return self.tts_handler.get_available_voices()