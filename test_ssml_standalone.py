#!/usr/bin/env python3
"""
Simple test script for SSMLFormatter functionality (standalone)
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TtsPhoneme:
    """Represents a phoneme mapping for TTS"""
    name: str
    phoneme: Optional[str] = None
    sub: Optional[str] = None

@dataclass 
class TTSModel:
    language: str
    name: str
    pitch: Optional[str] = None
    rate: Optional[str] = None
    phonemeUrl: Optional[str] = None

@dataclass
class AzureTTSConfig:
    subscriptionKey: str
    lexiconURL: str
    phonemeUrl: str
    models: List[TTSModel]

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
        self.localized_phonemes = {}
        self.global_phonemes = []
        self.phonemes_loaded = False
        
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
        
        # Replace illegal characters
        transformed = (transformed
                      .replace("&", " And ")
                      .replace("<", "")
                      .replace(">", "")
                      .replace('"', "")
                      .replace("'", ""))
        
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
        leading = "0ms" if order < 1 else "100ms"
        
        # Get model properties with defaults
        model_name = getattr(model, 'name', 'en-US-AriaNeural')
        pitch = getattr(model, 'pitch', 'medium')
        rate = getattr(model, 'rate', '1')
        
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

async def test_ssml_formatter():
    """Test the SSMLFormatter functionality"""
    
    # Create a mock Azure TTS config
    models = [
        TTSModel(
            language="en-US",
            name="en-US-AriaNeural",
            pitch="medium",
            rate="1.0",
            phonemeUrl="https://example.com/phonemes/en-us.json"
        ),
        TTSModel(
            language="th-TH", 
            name="th-TH-PremwadeeNeural",
            pitch="medium",
            rate="1.0",
            phonemeUrl="https://example.com/phonemes/th-th.json"
        )
    ]
    
    azure_config = AzureTTSConfig(
        subscriptionKey="test-key",
        lexiconURL="https://example.com/lexicons/",
        phonemeUrl="https://example.com/phonemes/global.json",
        models=models
    )
    
    # Create formatter
    formatter = SSMLFormatter(azure_config, remove_bracketed_words=True)
    
    # Test text transformation
    test_text = "Hello world! (this should be removed) & this < > \" ' "
    transformed = formatter.transform_text(test_text)
    print(f"Original: {test_text}")
    print(f"Transformed: {transformed}")
    print()
    
    # Test phoneme transformation (without actual loading)
    # Simulate some phonemes
    formatter.localized_phonemes["en-us"] = [
        TtsPhoneme(name="hello", phoneme="həˈloʊ"),
        TtsPhoneme(name="world", sub="WORLD")
    ]
    formatter.phonemes_loaded = True
    
    phoneme_text = formatter.transform_with_phonemes("Hello world test", "en-US")
    print(f"With phonemes: {phoneme_text}")
    print()
    
    # Test SSML generation
    model = models[0]  # English model
    ssml = formatter.create_ssml("Hello world! This is a test.", model, order=0)
    print("Generated SSML (first chunk):")
    print(ssml)
    print()
    
    # Test with second chunk (order=1)
    ssml2 = formatter.create_ssml("This is the second chunk.", model, order=1)
    print("Generated SSML (second chunk with leading silence):")
    print(ssml2)
    print()
    
    # Test with bracketed text
    ssml3 = formatter.create_ssml("This text (should be removed) will be clean.", model, order=2)
    print("Generated SSML with bracketed text removed:")
    print(ssml3)

if __name__ == "__main__":
    asyncio.run(test_ssml_formatter())
