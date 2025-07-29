#!/usr/bin/env python3
"""
Test script for the new SSEHandler implementation.
This script tests the SSE handler functionality without requiring external APIs.
"""

import threading
import time
import json
from sse_handler import SSEHandler


def simulate_background_work(sse_handler: SSEHandler):
    """Simulate background work that sends SSE messages."""
    try:
        # Simulate initial status
        sse_handler.send('status', message='Starting simulation')
        time.sleep(0.5)
        
        # Simulate validation
        sse_handler.send('status', message='Starting validation')
        time.sleep(1.0)
        
        validation_data = {
            'correction': 'This is a test correction',
            'keywords': ['test', 'correction']
        }
        sse_handler.send('validation_result', data=validation_data)
        time.sleep(0.5)
        
        # Simulate KM search
        sse_handler.send('status', message='Starting KM search')
        time.sleep(1.0)
        
        km_data = {'data': [{'title': 'Test Document', 'content': 'Test content'}]}
        sse_handler.send('km_result', data=km_data)
        time.sleep(0.5)
        
        # Simulate answer generation
        sse_handler.send('status', message='Starting answer generation')
        time.sleep(0.5)
        
        # Simulate streaming answer chunks
        answer_chunks = [
            "This is the first part of the answer. ",
            "Here's some more content. ",
            "And this is the final part of the response."
        ]
        
        for chunk in answer_chunks:
            sse_handler.send('answer_chunk', data={'content': chunk})
            time.sleep(0.3)
        
        # Simulate TTS audio
        tts_data = {
            'text': 'Sample TTS text',
            'language': 'en',
            'audio_size': 1024,
            'audio_data': 'base64encodedaudiodata',
            'audio_format': 'wav'
        }
        sse_handler.send('tts_audio', data=tts_data)
        time.sleep(0.5)
        
        # Simulate metadata
        metadata = {'docs_used': 3, 'confidence': 0.95}
        sse_handler.send('metadata', data=metadata)
        time.sleep(0.5)
        
        # Complete the process
        sse_handler.mark_complete()
        
    except Exception as e:
        sse_handler.send_error(f"Simulation failed: {str(e)}")


def test_sse_handler():
    """Test the SSEHandler with simulated background work."""
    print("Testing SSEHandler...")
    
    # Create SSE handler
    sse_handler = SSEHandler()
    
    # Start background thread
    background_thread = threading.Thread(
        target=simulate_background_work,
        args=(sse_handler,),
        daemon=True
    )
    background_thread.start()
    
    # Collect messages from the handler
    messages = []
    print("\nSSE Messages:")
    print("-" * 50)
    
    for message in sse_handler.yield_messages():
        print(message.strip())
        messages.append(message)
        
        # Parse and display the JSON content for better readability
        try:
            if message.startswith("data: "):
                json_str = message[6:].strip()  # Remove "data: " prefix
                data = json.loads(json_str)
                print(f"  → Type: {data['type']}")
                if 'message' in data:
                    print(f"  → Message: {data['message']}")
                if 'data' in data:
                    print(f"  → Data: {data['data']}")
                print()
        except json.JSONDecodeError:
            pass
    
    # Wait for background thread to complete
    background_thread.join(timeout=10)
    
    print(f"\nTest completed! Received {len(messages)} SSE messages.")
    return len(messages) > 0


def test_error_handling():
    """Test SSEHandler error handling."""
    print("\nTesting error handling...")
    
    sse_handler = SSEHandler()
    
    def error_simulation(handler):
        handler.send('status', message='Starting error test')
        time.sleep(0.5)
        handler.send_error('This is a test error')
    
    error_thread = threading.Thread(target=error_simulation, args=(sse_handler,))
    error_thread.start()
    
    messages = []
    for message in sse_handler.yield_messages():
        print(message.strip())
        messages.append(message)
    
    error_thread.join()
    print(f"Error test completed! Received {len(messages)} messages.")
    return len(messages) == 2  # Should have status and error messages


if __name__ == "__main__":
    print("SSEHandler Test Suite")
    print("=" * 50)
    
    # Test normal operation
    success1 = test_sse_handler()
    
    # Test error handling
    success2 = test_error_handling()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
        print(f"Normal operation test: {'✅' if success1 else '❌'}")
        print(f"Error handling test: {'✅' if success2 else '❌'}")
