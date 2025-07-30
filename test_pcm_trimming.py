#!/usr/bin/env python3
"""
Test ultra-fast PCM-based audio trimming
"""
import os
import sys
import time
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pcm_trimming():
    """Test the ultra-fast PCM-based audio trimming"""
    try:
        from src.tts_handler import TTSHandler, AUDIO_PROCESSING_AVAILABLE
        import numpy as np
        
        if not AUDIO_PROCESSING_AVAILABLE:
            logger.error("Audio processing libraries not available")
            return False
        
        logger.info("Testing ultra-fast PCM-based audio trimming...")
        
        # Create test data: 16-bit PCM at 16kHz with silence padding
        sr = 16000
        duration = 2.0  # 2 seconds of actual audio
        silence_duration = 0.2  # 200ms silence at each end
        
        # Generate test tone
        t = np.linspace(0, duration, int(sr * duration), False)
        tone = np.sin(440 * 2.0 * np.pi * t) * 0.3  # A4 note at 30% volume
        
        # Add silence
        silence_samples = int(silence_duration * sr)
        silence = np.zeros(silence_samples)
        
        full_signal = np.concatenate([silence, tone, silence])
        
        # Convert to 16-bit PCM bytes (simulating Azure TTS output)
        pcm_data = (full_signal * 32767).astype(np.int16).tobytes()
        
        logger.info(f"Created test PCM data: {len(pcm_data)} bytes ({len(full_signal)/sr:.3f}s)")
        
        # Test with trimming enabled
        logger.info("\n=== Testing with trimming ENABLED ===")
        tts_handler = TTSHandler("dummy_key", "southeastasia", enable_trimming=True)
        
        start_time = time.time()
        trimmed_data = tts_handler._trim_silence(pcm_data)
        duration_with_trimming = time.time() - start_time
        
        logger.info(f"✅ Trimming took: {duration_with_trimming:.6f}s")
        logger.info(f"Original size: {len(pcm_data)} bytes -> Trimmed size: {len(trimmed_data)} bytes")
        
        # Test with trimming disabled
        logger.info("\n=== Testing with trimming DISABLED ===")
        tts_handler_no_trim = TTSHandler("dummy_key", "southeastasia", enable_trimming=False)
        
        start_time = time.time()
        no_trim_data = tts_handler_no_trim._trim_silence(pcm_data)
        duration_no_trimming = time.time() - start_time
        
        logger.info(f"✅ No trimming took: {duration_no_trimming:.6f}s")
        logger.info(f"Size unchanged: {len(no_trim_data)} bytes")
        
        # Test with actual MP3 file if available
        test_audio_path = "speech.mp3"
        if os.path.exists(test_audio_path):
            logger.info("\n=== Comparing with MP3 file processing ===")
            
            # Simulate converting MP3 to PCM first (this would be done by Azure TTS now)
            import librosa
            with open(test_audio_path, 'rb') as f:
                mp3_data = f.read()
            
            # Load and convert to PCM format
            start_conversion = time.time()
            y, sr_orig = librosa.load(test_audio_path, sr=16000, mono=True)
            pcm_from_mp3 = (y * 32767).astype(np.int16).tobytes()
            conversion_time = time.time() - start_conversion
            
            logger.info(f"MP3 to PCM conversion took: {conversion_time:.3f}s")
            
            # Now test trimming the PCM data
            start_time = time.time()
            trimmed_mp3_data = tts_handler._trim_silence(pcm_from_mp3)
            pcm_trim_time = time.time() - start_time
            
            logger.info(f"PCM trimming took: {pcm_trim_time:.6f}s")
            logger.info(f"Total would be: {conversion_time + pcm_trim_time:.3f}s (but Azure TTS gives us PCM directly!)")
        
        # Performance summary
        logger.info(f"\n=== Performance Summary ===")
        logger.info(f"PCM trimming (enabled): {duration_with_trimming:.6f}s")
        logger.info(f"PCM trimming (disabled): {duration_no_trimming:.6f}s")
        
        if duration_with_trimming < 0.01:  # Less than 10ms
            logger.info("🚀 SUCCESS: Trimming is now ultra-fast (<10ms)!")
            return True
        else:
            logger.warning(f"Trimming still takes {duration_with_trimming:.3f}s")
            return False
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_pcm_trimming()
    
    if success:
        logger.info("\n✅ Ultra-fast PCM trimming test completed successfully!")
        logger.info("🎯 Key improvements:")
        logger.info("   - Azure TTS now returns raw PCM (no MP3 decoding needed)")
        logger.info("   - Direct numpy array processing (no librosa.load)")
        logger.info("   - Trimming should now be <10ms")
        logger.info("   - Optional trimming can be disabled entirely for maximum speed")
    else:
        logger.error("❌ Ultra-fast PCM trimming test failed")
        sys.exit(1)
