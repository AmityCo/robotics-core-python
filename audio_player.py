#!/usr/bin/env python3
"""
Simple script to play the trimmed audio files for comparison
"""
import os
import subprocess

def play_audio_comparison():
    """Play original and trimmed audio files for comparison"""
    
    original_file = "/Users/touchaponk/Downloads/048e0fef40c8c6d5.wav"
    trimmed_files = [
        "/tmp/trimmed_threshold_0.1percent.wav",
        "/tmp/trimmed_threshold_1.0percent.wav", 
        "/tmp/trimmed_threshold_5.0percent.wav"
    ]
    
    print("Audio Comparison Player")
    print("======================")
    
    while True:
        print(f"\nOptions:")
        print(f"1. Play original (2.688s)")
        print(f"2. Play 0.1% threshold (2.684s)")
        print(f"3. Play 1.0% threshold (2.212s) - RECOMMENDED")
        print(f"4. Play 5.0% threshold (2.164s)")
        print(f"5. Quit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == "1":
            print("Playing original...")
            play_file(original_file)
        elif choice == "2":
            print("Playing 0.1% threshold trimmed...")
            play_file(trimmed_files[0])
        elif choice == "3":
            print("Playing 1.0% threshold trimmed (recommended)...")
            play_file(trimmed_files[1])
        elif choice == "4":
            print("Playing 5.0% threshold trimmed...")
            play_file(trimmed_files[2])
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid choice!")

def play_file(file_path):
    """Play an audio file using system default player"""
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
        
    try:
        # Try to use afplay on macOS
        subprocess.run(["afplay", file_path], check=True)
    except subprocess.CalledProcessError:
        print(f"Error playing {file_path}")
    except FileNotFoundError:
        print("afplay not found. Opening with default application...")
        try:
            subprocess.run(["open", file_path], check=True)
        except:
            print(f"Could not play {file_path}")

if __name__ == "__main__":
    play_audio_comparison()
