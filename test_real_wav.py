#!/usr/bin/env python3
"""
Test script to verify audio trimming with a real WAV file
"""
import wave
import numpy as np
import time
from src.audio_helper import AudioProcessor

def load_wav_file(file_path):
    """
    Load a WAV file and return PCM data and audio info
    """
    try:
        with wave.open(file_path, 'rb') as wav_file:
            # Get audio parameters
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            
            # Read audio data
            audio_data = wav_file.readframes(frames)
            
            print(f"WAV File Info:")
            print(f"  Duration: {frames / sample_rate:.3f} seconds")
            print(f"  Sample Rate: {sample_rate} Hz")
            print(f"  Channels: {channels}")
            print(f"  Sample Width: {sample_width} bytes")
            print(f"  Total Frames: {frames}")
            print(f"  File Size: {len(audio_data)} bytes")
            
            return audio_data, sample_rate, channels, sample_width
            
    except Exception as e:
        print(f"Error loading WAV file: {e}")
        return None, None, None, None

def analyze_audio_data(audio_data, sample_rate, sample_width):
    """
    Analyze the audio data to show silence regions
    """
    if sample_width == 2:  # 16-bit
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
    elif sample_width == 1:  # 8-bit
        audio_array = np.frombuffer(audio_data, dtype=np.uint8).astype(np.int16) - 128
    else:
        print(f"Unsupported sample width: {sample_width}")
        return None
    
    # Normalize to [-1, 1]
    if len(audio_array.shape) > 1 or audio_array.dtype != np.int16:
        print("Converting audio format...")
        audio_array = audio_array.astype(np.float32) / 32768.0
        audio_array = (audio_array * 32767).astype(np.int16)
    
    # Convert to mono if stereo
    if len(audio_data) // sample_width // len(audio_array) == 2:
        print("Converting stereo to mono...")
        audio_array = audio_array.reshape(-1, 2).mean(axis=1).astype(np.int16)
    
    # Calculate energy in chunks to find silence regions
    chunk_size = sample_rate // 10  # 100ms chunks
    chunks = len(audio_array) // chunk_size
    
    print(f"\nAudio Analysis (100ms chunks):")
    silence_threshold = np.max(np.abs(audio_array)) * 0.01  # 1% of max
    
    silent_regions = []
    for i in range(chunks):
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size, len(audio_array))
        chunk = audio_array[start_idx:end_idx]
        
        max_amplitude = np.max(np.abs(chunk))
        is_silent = max_amplitude < silence_threshold
        
        time_start = start_idx / sample_rate
        time_end = end_idx / sample_rate
        
        status = "SILENT" if is_silent else "AUDIO"
        print(f"  {time_start:6.3f}s - {time_end:6.3f}s: {status} (max: {max_amplitude:5d})")
        
        if is_silent:
            silent_regions.append((time_start, time_end))
    
    return audio_array, silent_regions

def test_real_wav_file():
    """Test the AudioProcessor with a real WAV file"""
    file_path = "/Users/touchaponk/Downloads/048e0fef40c8c6d5.wav"
    
    print("=== Testing Real WAV File Trimming ===")
    print(f"File: {file_path}")
    
    # Load the WAV file
    wav_data, sample_rate, channels, sample_width = load_wav_file(file_path)
    if wav_data is None:
        return
    
    # Analyze the original audio
    print(f"\n=== Original Audio Analysis ===")
    audio_array, silent_regions = analyze_audio_data(wav_data, sample_rate, sample_width)
    
    if len(silent_regions) > 0:
        print(f"\nDetected {len(silent_regions)} silent regions:")
        for i, (start, end) in enumerate(silent_regions):
            duration = end - start
            print(f"  Silent region {i+1}: {start:.3f}s - {end:.3f}s (duration: {duration:.3f}s)")
    
    # Convert to PCM format expected by AudioProcessor (16-bit mono)
    if sample_width != 2:
        print("Converting to 16-bit...")
        if sample_width == 1:
            audio_16bit = ((np.frombuffer(wav_data, dtype=np.uint8).astype(np.float32) - 128) / 128 * 32767).astype(np.int16)
        else:
            print(f"Unsupported bit depth: {sample_width * 8}")
            return
    else:
        audio_16bit = np.frombuffer(wav_data, dtype=np.int16)
    
    # Convert stereo to mono if needed
    if channels == 2:
        print("Converting stereo to mono...")
        audio_16bit = audio_16bit.reshape(-1, 2).mean(axis=1).astype(np.int16)
    
    # Convert to bytes for AudioProcessor
    pcm_data = audio_16bit.tobytes()
    
    print(f"\nPCM Data for processing: {len(pcm_data)} bytes")
    
    # Test different threshold levels
    thresholds = [0.001, 0.01, 0.05]  # 0.1%, 1%, 5%
    
    print(f"\n=== Performance Benchmarking ===")
    print(f"Running each test multiple times for accurate timing...")
    
    performance_results = []
    
    for threshold in thresholds:
        print(f"\n=== Testing with threshold {threshold*100:.1f}% ===")
        
        # Create audio processor with current threshold
        processor = AudioProcessor(silence_threshold=threshold, enable_trimming=True)
        
        # Run multiple iterations for more accurate timing
        num_iterations = 5
        trimming_times = []
        conversion_times = []
        
        print(f"  Running {num_iterations} iterations for accurate timing...")
        
        for i in range(num_iterations):
            # Measure trimming performance
            start_time = time.perf_counter()
            trimmed_data = processor.trim_silence(pcm_data)
            end_time = time.perf_counter()
            raw_time = end_time - start_time
            trimming_times.append(raw_time * 1000)  # Convert seconds to milliseconds
            
            # Debug output for first iteration
            if i == 0:
                print(f"    Debug: Raw trimming time = {raw_time:.6f} seconds = {raw_time * 1000:.3f} ms")
            
            # Measure WAV conversion performance
            start_time = time.perf_counter()
            wav_output = processor.convert_pcm_to_wav(trimmed_data, sample_rate=sample_rate)
            end_time = time.perf_counter()
            raw_conversion_time = end_time - start_time
            conversion_times.append(raw_conversion_time * 1000)  # Convert seconds to milliseconds
            
            # Debug output for first iteration
            if i == 0:
                print(f"    Debug: Raw conversion time = {raw_conversion_time:.6f} seconds = {raw_conversion_time * 1000:.3f} ms")
        
        # Calculate average times
        avg_trimming_time = sum(trimming_times) / len(trimming_times)
        avg_conversion_time = sum(conversion_times) / len(conversion_times)
        min_trimming_time = min(trimming_times)
        max_trimming_time = max(trimming_times)
        
        # Calculate results
        original_samples = len(pcm_data) // 2  # 16-bit = 2 bytes per sample
        trimmed_samples = len(trimmed_data) // 2
        
        original_duration = original_samples / sample_rate
        trimmed_duration = trimmed_samples / sample_rate
        trimmed_amount = original_duration - trimmed_duration
        
        print(f"  Original: {original_duration:.3f}s ({len(pcm_data)} bytes)")
        print(f"  Trimmed:  {trimmed_duration:.3f}s ({len(trimmed_data)} bytes)")
        print(f"  Removed:  {trimmed_amount:.3f}s ({trimmed_amount/original_duration*100:.1f}%)")
        print(f"  ⏱️  Trimming took: {avg_trimming_time:.2f}ms (avg), {min_trimming_time:.2f}-{max_trimming_time:.2f}ms (range)")
        
        # Calculate processing speed ratio
        speed_ratio = original_duration * 1000 / avg_trimming_time
        print(f"  🚀 Processing speed: {speed_ratio:.1f}x realtime")
        
        print(f"  ⏱️  WAV conversion took: {avg_conversion_time:.2f}ms (avg)")
        
        total_processing_time = avg_trimming_time + avg_conversion_time
        total_speed_ratio = original_duration * 1000 / total_processing_time
        print(f"  🚀 Total processing speed: {total_speed_ratio:.1f}x realtime")
        
        # Store results for summary
        performance_results.append({
            'threshold': threshold,
            'trimming_time': avg_trimming_time,
            'conversion_time': avg_conversion_time,
            'total_time': total_processing_time,
            'speed_ratio': total_speed_ratio,
            'audio_reduction': trimmed_amount/original_duration*100
        })
        output_filename = f"/tmp/trimmed_threshold_{threshold*100:.1f}percent.wav"
        
        try:
            with open(output_filename, 'wb') as f:
                f.write(wav_output)
            print(f"  Saved trimmed audio to: {output_filename}")
        except Exception as e:
            print(f"  Error saving file: {e}")
    
    # Performance Summary
    print(f"\n=== Performance Summary ===")
    print(f"Audio file: 2.688s, 86KB")
    print(f"{'Threshold':<12} {'Trim Time':<12} {'Convert Time':<14} {'Total Time':<12} {'Speed':<8} {'Reduction'}")
    print(f"{'='*12} {'='*12} {'='*14} {'='*12} {'='*8} {'='*9}")
    
    for result in performance_results:
        print(f"{result['threshold']*100:>10.1f}% "
              f"{result['trimming_time']:>10.2f}ms "
              f"{result['conversion_time']:>12.2f}ms "
              f"{result['total_time']:>10.2f}ms "
              f"{result['speed_ratio']:>6.1f}x "
              f"{result['audio_reduction']:>7.1f}%")
    
    # Find best performing threshold
    best_result = min(performance_results, key=lambda x: x['total_time'])
    print(f"\n🏆 Fastest processing: {best_result['threshold']*100:.1f}% threshold")
    print(f"   Total time: {best_result['total_time']:.2f}ms ({best_result['speed_ratio']:.1f}x realtime)")
    
    # Find most effective trimming
    best_trim = max(performance_results, key=lambda x: x['audio_reduction'])
    print(f"🎯 Most effective trimming: {best_trim['threshold']*100:.1f}% threshold")
    print(f"   Audio reduction: {best_trim['audio_reduction']:.1f}%")
    
    print("\n=== Real WAV File Test Completed ===")

if __name__ == "__main__":
    test_real_wav_file()
