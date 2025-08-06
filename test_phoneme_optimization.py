#!/usr/bin/env python3
"""
Test script to verify the phoneme transformation optimization
"""
import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.tts_stream import SSMLFormatter, TtsPhoneme

class MockAzureConfig:
    """Mock Azure config for testing"""
    def __init__(self):
        self.phonemeUrl = None
        self.lexiconURL = None
        self.models = []

def test_phoneme_transformation_performance():
    """Test the performance of phoneme transformation"""
    
    # Create mock config
    azure_config = MockAzureConfig()
    formatter = SSMLFormatter(azure_config)
    
    # Create some test phonemes (simulating 360 items as mentioned)
    test_phonemes = []
    for i in range(360):
        phoneme = TtsPhoneme(
            name=f"TestWord{i}",
            phoneme=f"test{i}",
            sub=None if i % 2 == 0 else f"replacement{i}"
        )
        test_phonemes.append(phoneme)
    
    # Set up phonemes
    formatter.global_phonemes = test_phonemes
    formatter.localized_phonemes = {"en-us": test_phonemes[:50]}  # Some localized
    formatter.phonemes_loaded = True
    
    # Pre-compile patterns (this is the optimization)
    formatter._precompile_phoneme_patterns()
    
    # Test text with some matches
    test_text = "This is a test with TestWord1 and TestWord50 and TestWord100 in it. " * 10
    
    print(f"Testing with {len(test_phonemes)} phonemes")
    print(f"Test text length: {len(test_text)} characters")
    
    # Time the transformation
    start_time = time.time()
    result = formatter.transform_with_phonemes(test_text, "en-US")
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"Transformation took: {duration:.4f} seconds")
    print(f"Result length: {len(result)} characters")
    
    # Check that some transformations were applied
    if "<sub alias=" in result or "<phoneme alphabet=" in result:
        print("✓ Phoneme transformations were applied successfully")
    else:
        print("✗ No phoneme transformations were found in result")
    
    # Performance target: should be much faster than 0.7 seconds
    if duration < 0.1:  # Target under 100ms
        print(f"✓ Performance is excellent: {duration:.4f}s (target: <0.1s)")
    elif duration < 0.3:
        print(f"✓ Performance is good: {duration:.4f}s (much better than 0.7s)")
    else:
        print(f"⚠ Performance needs improvement: {duration:.4f}s")
    
    return duration

if __name__ == "__main__":
    test_phoneme_transformation_performance()
