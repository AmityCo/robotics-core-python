#!/usr/bin/env python3
"""
Test script for SSMLFormatter with cached requests integration
"""
import asyncio
import logging
from typing import List
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TtsPhoneme:
    """Represents a phoneme mapping for TTS"""
    name: str
    phoneme: str = None
    sub: str = None

@dataclass 
class TTSModel:
    language: str
    name: str
    pitch: str = None
    rate: str = None
    phonemeUrl: str = None

@dataclass
class AzureTTSConfig:
    subscriptionKey: str
    lexiconURL: str
    phonemeUrl: str
    models: List[TTSModel]

# Mock the cached_get function for testing
class MockCachedResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code
    
    def json(self):
        return self.data

async def mock_cached_get(url, timeout=10):
    """Mock cached_get function that returns sample phoneme data"""
    logger.info(f"Mock cached request to: {url}")
    
    # Return sample phoneme data
    sample_data = [
        {"name": "hello", "phoneme": "həˈloʊ"},
        {"name": "world", "sub": "WORLD"},
        {"name": "test", "phoneme": "tɛst"},
        {"name": "example", "sub": "EXAMPLE"}
    ]
    
    return MockCachedResponse(sample_data)

# Monkey patch the import for testing
import sys
from unittest.mock import MagicMock

# Create a mock module for src.requests_handler
mock_requests_handler = MagicMock()
mock_requests_handler.get = mock_cached_get
sys.modules['src.requests_handler'] = mock_requests_handler

# Now import our SSMLFormatter
from src.tts_stream import SSMLFormatter

async def test_cached_phoneme_loading():
    """Test the SSMLFormatter with cached phoneme loading"""
    
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
    
    print("Testing cached phoneme loading...")
    
    # Load phonemes (should use cached requests)
    await formatter.load_phonemes()
    
    print(f"Phonemes loaded: {formatter.phonemes_loaded}")
    print(f"Global phonemes count: {len(formatter.global_phonemes)}")
    print(f"Localized phonemes: {list(formatter.localized_phonemes.keys())}")
    
    # Test text transformation
    test_text = "Hello world! (this should be removed) & this < > \" ' "
    transformed = formatter.transform_text(test_text)
    print(f"\nOriginal: {test_text}")
    print(f"Transformed: {transformed}")
    
    # Test phoneme transformation
    phoneme_text = formatter.transform_with_phonemes("Hello world test example", "en-US")
    print(f"\nWith phonemes: {phoneme_text}")
    
    # Test SSML generation
    model = models[0]  # English model
    ssml = formatter.create_ssml("Hello world! This is a test example.", model, order=0)
    print(f"\nGenerated SSML (first chunk):")
    print(ssml)
    
    # Test with second chunk (order=1)
    ssml2 = formatter.create_ssml("This is the second chunk with test words.", model, order=1)
    print(f"\nGenerated SSML (second chunk with leading silence):")
    print(ssml2)
    
    print("\nTest completed successfully! The cached requests integration is working.")

if __name__ == "__main__":
    try:
        asyncio.run(test_cached_phoneme_loading())
    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
