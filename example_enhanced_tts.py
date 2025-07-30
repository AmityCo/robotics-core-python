#!/usr/bin/env python3
"""
Example usage of the enhanced TTS handler with caching
"""
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.tts_handler import TTSHandler

def main():
    """Example usage of TTS handler with caching"""
    
    # Initialize TTS handler (you'll need to set AZURE_TTS_SUBSCRIPTION_KEY)
    subscription_key = os.getenv("AZURE_TTS_SUBSCRIPTION_KEY")
    if not subscription_key:
        print("Please set AZURE_TTS_SUBSCRIPTION_KEY environment variable")
        return
    
    tts_handler = TTSHandler(subscription_key=subscription_key)
    
    # Example 1: Basic usage (language and model auto-detected from SSML)
    ssml_content = '''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
        <voice name="en-US-AriaNeural">
            <prosody rate="medium" pitch="medium">
                Welcome to the enhanced TTS system with intelligent caching!
            </prosody>
        </voice>
    </speak>'''
    
    print("Generating speech (auto-detect language/model)...")
    audio_data = tts_handler.generate_speech(ssml_content)
    
    if audio_data:
        print(f"✓ Generated audio: {len(audio_data)} bytes")
        
        # Save to file for testing
        with open("example_output.mp3", "wb") as f:
            f.write(audio_data)
        print("Audio saved as example_output.mp3")
    else:
        print("✗ Failed to generate audio")
        return
    
    # Example 2: Explicit language and model specification
    print("\nGenerating speech with explicit parameters...")
    audio_data2 = tts_handler.generate_speech(
        ssml_content, 
        language="en-US", 
        model="neural2"
    )
    
    if audio_data2:
        print(f"✓ Generated audio: {len(audio_data2)} bytes")
        # This should be the same as the first call due to caching
        if audio_data == audio_data2:
            print("✓ Cache working - same audio data returned")
        else:
            print("⚠ Different audio data - cache may not be working")
    
    # Example 3: Check cache info
    print("\nChecking cache information...")
    cache_info = tts_handler.get_cache_info(
        "Welcome to the enhanced TTS system with intelligent caching!",
        "en-US",
        "neural2"
    )
    print(f"Cache info: {cache_info}")
    
    # Example 4: Thai language example
    thai_ssml = '''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="th-TH">
        <voice name="th-TH-PremwadeeNeural">
            <prosody rate="medium" pitch="medium">
                สวัสดีครับ นี่คือระบบ TTS ที่มีการแคชข้อมูลอัจฉริยะ
            </prosody>
        </voice>
    </speak>'''
    
    print("\nGenerating Thai speech...")
    thai_audio = tts_handler.generate_speech(thai_ssml)
    
    if thai_audio:
        print(f"✓ Generated Thai audio: {len(thai_audio)} bytes")
        with open("example_thai.mp3", "wb") as f:
            f.write(thai_audio)
        print("Thai audio saved as example_thai.mp3")
    
    print("\nExample complete!")

if __name__ == "__main__":
    main()
