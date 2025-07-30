#!/usr/bin/env python3
"""
Test script for SSMLFormatter functionality
"""
import asyncio
import logging
from src.tts_stream import SSMLFormatter, TtsPhoneme
from src.org_config import TTSModel, AzureTTSConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    print("Generated SSML:")
    print(ssml)
    print()
    
    # Test with second chunk (order=1)
    ssml2 = formatter.create_ssml("This is the second chunk.", model, order=1)
    print("Generated SSML (second chunk):")
    print(ssml2)

if __name__ == "__main__":
    asyncio.run(test_ssml_formatter())
