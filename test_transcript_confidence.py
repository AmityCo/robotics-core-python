#!/usr/bin/env python3
"""
Test script to verify transcript confidence threshold functionality
"""

from src.org_config import GeminiConfig, LocalizationConfig

def test_gemini_config_with_confidence_threshold():
    """Test GeminiConfig with validatorTranscriptConfidenceThreshold"""
    config = GeminiConfig(
        key="test-key",
        validatorEnabled=True,
        validatorTranscriptConfidenceThreshold=0.8
    )
    
    assert config.key == "test-key"
    assert config.validatorEnabled == True
    assert config.validatorTranscriptConfidenceThreshold == 0.8
    print("✅ GeminiConfig with confidence threshold works correctly")

def test_localization_config_with_confidence_threshold():
    """Test LocalizationConfig with validatorTranscriptConfidenceThreshold"""
    config = LocalizationConfig(
        displayName="Test",
        icon="test-icon",
        language="en-US",
        assistantId="test-id",
        assistantKey="test-key",
        validatorTranscriptConfidenceThreshold=0.9
    )
    
    assert config.displayName == "Test"
    assert config.language == "en-US"
    assert config.validatorTranscriptConfidenceThreshold == 0.9
    print("✅ LocalizationConfig with confidence threshold works correctly")

def test_optional_confidence_threshold():
    """Test that confidence threshold is optional"""
    gemini_config = GeminiConfig(
        key="test-key",
        validatorEnabled=True
    )
    
    localization_config = LocalizationConfig(
        displayName="Test",
        icon="test-icon", 
        language="en-US",
        assistantId="test-id",
        assistantKey="test-key"
    )
    
    assert gemini_config.validatorTranscriptConfidenceThreshold is None
    assert localization_config.validatorTranscriptConfidenceThreshold is None
    print("✅ Optional confidence threshold works correctly")

if __name__ == "__main__":
    test_gemini_config_with_confidence_threshold()
    test_localization_config_with_confidence_threshold()
    test_optional_confidence_threshold()
    print("\n🎉 All tests passed!")
