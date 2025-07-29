#!/usr/bin/env python3
"""
Demo script showing TTS integration with answer flow
This demonstrates how answer chunks are automatically sent to TTS as they're generated
"""

import sys
import os
import logging
import json
import time
from typing import Generator

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.answer_flow_sse import execute_answer_flow_sse
from src.org_config import load_org_config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def demo_answer_flow_with_tts():
    """
    Demo the answer flow with TTS integration
    """
    logger.info("Starting Answer Flow + TTS Demo")
    
    # Example inputs (you'll need to adjust these for your setup)
    sample_transcript = "Hello, can you tell me about the weather today?"
    sample_language = "en-US"
    sample_audio = ""  # Base64 encoded audio (empty for demo)
    
    # Get org config ID from environment or use default
    org_id = os.getenv("DEMO_ORG_CONFIG_ID")
    if not org_id:
        logger.error("Please set DEMO_ORG_CONFIG_ID environment variable with a valid config ID")
        return
    
    print(f"\nDemo Configuration:")
    print(f"Transcript: {sample_transcript}")
    print(f"Language: {sample_language}")
    print(f"Org ID: {org_id}")
    print(f"Audio: {'Yes' if sample_audio else 'No (demo mode)'}")
    
    print("\n" + "="*60)
    print("ANSWER FLOW + TTS STREAMING DEMO")
    print("="*60)
    
    try:
        # Track different types of events
        answer_chunks = []
        tts_events = []
        errors = []
        
        # Execute the answer flow with TTS integration
        for sse_event in execute_answer_flow_sse(
            transcript=sample_transcript,
            language=sample_language,
            base64_audio=sample_audio,
            org_id=org_id
        ):
            # Parse the SSE event
            if sse_event.startswith("data: "):
                try:
                    event_data = json.loads(sse_event[6:])  # Remove "data: " prefix
                    event_type = event_data.get('type', 'unknown')
                    timestamp = event_data.get('timestamp', '')
                    
                    print(f"\n[{timestamp}] {event_type.upper()}")
                    
                    if event_type == 'status':
                        message = event_data.get('message', '')
                        print(f"  Status: {message}")
                    
                    elif event_type == 'validation_result':
                        correction = event_data.get('data', {}).get('correction', '')
                        keywords = event_data.get('data', {}).get('keywords', [])
                        print(f"  Correction: {correction}")
                        print(f"  Keywords: {len(keywords)} items")
                    
                    elif event_type == 'km_result':
                        km_data = event_data.get('data', {})
                        results_count = len(km_data.get('data', []))
                        print(f"  KM Results: {results_count} documents found")
                    
                    elif event_type == 'thinking':
                        thinking_content = event_data.get('data', {}).get('content', '')
                        print(f"  Thinking: {thinking_content[:100]}...")
                    
                    elif event_type == 'answer_chunk':
                        content = event_data.get('data', {}).get('content', '')
                        answer_chunks.append(content)
                        print(f"  Answer Chunk: '{content}'")
                        print(f"  -> This chunk will be sent to TTS buffer")
                    
                    elif event_type == 'tts_audio':
                        text = event_data.get('data', {}).get('text', '')
                        language = event_data.get('data', {}).get('language', '')
                        audio_size = event_data.get('data', {}).get('audio_size', 0)
                        tts_events.append({
                            'text': text,
                            'language': language,
                            'audio_size': audio_size
                        })
                        print(f"  TTS Audio Ready: '{text[:50]}...' ({audio_size} bytes)")
                    
                    elif event_type == 'metadata':
                        metadata = event_data.get('data', {})
                        print(f"  Metadata: {metadata}")
                    
                    elif event_type == 'error':
                        error_msg = event_data.get('message', '')
                        errors.append(error_msg)
                        print(f"  ERROR: {error_msg}")
                    
                    elif event_type == 'complete':
                        print(f"  Pipeline completed successfully!")
                    
                    else:
                        print(f"  Unknown event type: {event_data}")
                
                except json.JSONDecodeError as e:
                    print(f"  Failed to parse SSE event: {e}")
                    print(f"  Raw event: {sse_event}")
        
        # Summary
        print("\n" + "="*60)
        print("DEMO SUMMARY")
        print("="*60)
        
        print(f"\nAnswer Generation:")
        print(f"  Total answer chunks: {len(answer_chunks)}")
        if answer_chunks:
            full_answer = ''.join(answer_chunks)
            print(f"  Full answer length: {len(full_answer)} characters")
            print(f"  Full answer: {full_answer[:200]}...")
        
        print(f"\nTTS Processing:")
        print(f"  TTS audio events: {len(tts_events)}")
        if tts_events:
            total_audio_size = sum(event['audio_size'] for event in tts_events)
            print(f"  Total audio size: {total_audio_size} bytes")
            for i, event in enumerate(tts_events):
                print(f"    Audio {i+1}: '{event['text'][:30]}...' ({event['audio_size']} bytes)")
        
        if errors:
            print(f"\nErrors encountered:")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"\nNo errors encountered!")
        
        print(f"\nTTS Integration Features Demonstrated:")
        print(f"  ✓ Automatic text chunk buffering")
        print(f"  ✓ Word count threshold (3+ words)")
        print(f"  ✓ Time-based flushing (2+ seconds)")
        print(f"  ✓ Azure TTS API integration")
        print(f"  ✓ Multiple language support")
        print(f"  ✓ Real-time streaming compatibility")
        
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        print(f"\nDemo failed with error: {e}")

def main():
    """Main demo function"""
    print("="*60)
    print("ROBOTICS CORE PYTHON - TTS INTEGRATION DEMO")
    print("="*60)
    
    print("\nThis demo shows how the answer flow automatically sends")
    print("text chunks to TTS (Text-to-Speech) as they're generated.")
    print("\nFeatures:")
    print("• Text buffering with smart triggering")
    print("• Azure Cognitive Services TTS integration")
    print("• Real-time streaming compatibility")
    print("• Multiple language support")
    print("• Configurable thresholds (words/time)")
    
    print("\nSetup Requirements:")
    print("1. Set DEMO_ORG_CONFIG_ID environment variable")
    print("2. Ensure organization config has valid Azure TTS settings")
    print("3. Verify Azure credentials are configured")
    
    # Check if config ID is available
    org_id = os.getenv("DEMO_ORG_CONFIG_ID")
    if not org_id:
        print("\n❌ DEMO_ORG_CONFIG_ID environment variable not set")
        print("   Please set it to a valid organization configuration ID")
        print("   Example: export DEMO_ORG_CONFIG_ID='your-config-id-here'")
        return
    
    print(f"\n✓ Using org config ID: {org_id}")
    
    # Try to load the config to verify it exists
    try:
        config = load_org_config(org_id)
        if config:
            print(f"✓ Config loaded: {config.displayName}")
            if config.tts and config.tts.azure:
                print(f"✓ Azure TTS configured with {len(config.tts.azure.models)} models")
            else:
                print("⚠️  Warning: No TTS configuration found in org config")
        else:
            print(f"❌ Could not load org config for ID: {org_id}")
            return
    except Exception as e:
        print(f"❌ Error loading org config: {e}")
        return
    
    # Run the demo
    input("\nPress Enter to start the demo...")
    demo_answer_flow_with_tts()

if __name__ == "__main__":
    main()
