#!/usr/bin/env python3
"""
Test script for PhonemeManager functionality
"""

import asyncio
import logging
from src.phoneme_manager import PhonemeManager

# Set up logging
logging.basicConfig(level=logging.INFO)

class MockModel:
    def __init__(self, language, phoneme_url=None):
        self.language = language
        self.phonemeUrl = phoneme_url

class MockAzureConfig:
    def __init__(self, phoneme_url=None, lexicon_url=None, models=None):
        self.phonemeUrl = phoneme_url
        self.lexiconURL = lexicon_url
        self.models = models or []

async def test_phoneme_manager():
    """Test PhonemeManager basic functionality"""
    
    print("Testing PhonemeManager...")
    
    # Create mock Azure config
    models = [
        MockModel("en-US", "https://example.com/en-phonemes.json"),
        MockModel("th-TH", "https://example.com/th-phonemes.json"),
    ]
    
    azure_config = MockAzureConfig(
        phoneme_url="https://example.com/global-phonemes.json",
        lexicon_url="https://example.com/lexicons/",
        models=models
    )
    
    # Test phoneme cache ID generation
    phoneme_cache_id = PhonemeManager._generate_phoneme_cache_id(azure_config)
    print(f"Generated phoneme cache ID: {phoneme_cache_id}")
    
    # Test cache stats
    stats = PhonemeManager.get_cache_stats()
    print(f"Initial cache stats: {stats}")
    
    # Test that the phoneme cache ID is consistent
    phoneme_cache_id2 = PhonemeManager._generate_phoneme_cache_id(azure_config)
    assert phoneme_cache_id == phoneme_cache_id2, "Phoneme cache IDs should be consistent"
    print("✓ Phoneme cache ID generation is consistent")
    
    # Test with different config
    azure_config2 = MockAzureConfig(
        phoneme_url="https://example.com/different-global-phonemes.json",
        models=models
    )
    
    phoneme_cache_id3 = PhonemeManager._generate_phoneme_cache_id(azure_config2)
    assert phoneme_cache_id != phoneme_cache_id3, "Different configs should have different phoneme cache IDs"
    print("✓ Different configs generate different phoneme cache IDs")
    
    # Test cache clearing
    PhonemeManager.clear_cache()
    stats = PhonemeManager.get_cache_stats()
    print(f"Cache stats after clear: {stats}")
    
    print("All tests passed! ✓")

if __name__ == "__main__":
    asyncio.run(test_phoneme_manager())
