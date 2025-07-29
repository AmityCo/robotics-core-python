#!/usr/bin/env python3
"""
Test the complete SSE flow with TTS integration
"""
import time
import threading
import json
from unittest.mock import Mock, patch
from sse_handler import SSEHandler

def test_sse_flow_with_tts():
    """Test complete SSE flow simulation"""
    print("Testing complete SSE flow with TTS simulation...")
    
    handler = SSEHandler()
    handler.register_component('text_generation')
    handler.register_component('tts_processing')
    
    # Collect all messages
    messages = []
    completed = threading.Event()
    
    def message_collector():
        for message in handler.yield_messages():
            messages.append(message)
            # Parse message to check for completion
            try:
                data = json.loads(message.replace('data: ', '').strip())
                if data.get('type') == 'complete':
                    completed.set()
            except:
                pass
    
    # Start message collection
    collector_thread = threading.Thread(target=message_collector)
    collector_thread.start()
    
    # Simulate the pipeline
    def simulate_pipeline():
        # Send initial status
        handler.send('status', message='Starting pipeline')
        time.sleep(0.1)
        
        # Send validation result
        handler.send('validation_result', data={'correction': 'test correction'})
        time.sleep(0.1)
        
        # Send KM search result
        handler.send('km_result', data={'results': []})
        time.sleep(0.1)
        
        # Simulate streaming text generation
        text_chunks = ["Hello ", "world ", "this ", "is ", "a ", "test."]
        for chunk in text_chunks:
            handler.send('answer_chunk', data={'content': chunk})
            time.sleep(0.05)
        
        # Mark text generation complete
        handler.mark_component_complete('text_generation')
        time.sleep(0.1)
        
        # Simulate TTS completion after a delay
        def complete_tts():
            time.sleep(0.2)
            handler.send('tts_audio', data={'text': 'Hello world', 'audio_size': 1024})
            handler.mark_component_complete('tts_processing')
        
        tts_thread = threading.Thread(target=complete_tts)
        tts_thread.start()
        tts_thread.join()
    
    # Run pipeline simulation
    pipeline_thread = threading.Thread(target=simulate_pipeline)
    pipeline_thread.start()
    
    # Wait for completion or timeout
    completed.wait(timeout=5.0)
    
    # Wait for threads to finish
    pipeline_thread.join()
    collector_thread.join(timeout=1.0)
    
    print(f"Collected {len(messages)} messages")
    
    # Verify we got messages
    assert len(messages) > 0, "Should have collected messages"
    
    # Verify completion message exists
    completion_found = False
    for message in messages:
        try:
            data = json.loads(message.replace('data: ', '').strip())
            if data.get('type') == 'complete':
                completion_found = True
                break
        except:
            continue
    
    assert completion_found, "Should have found completion message"
    
    print("✓ Complete SSE flow test passed")

def test_error_handling():
    """Test that errors properly mark components as complete"""
    print("Testing error handling...")
    
    handler = SSEHandler()
    handler.register_component('text_generation')
    handler.register_component('tts_processing')
    
    # Send error and mark components complete
    handler.send_error("Test error")
    handler.mark_component_complete('text_generation')
    handler.mark_component_complete('tts_processing')
    
    # Should be complete after error + component completion
    time.sleep(0.1)
    assert handler.is_complete.is_set(), "Handler should be complete after error and component completion"
    
    print("✓ Error handling test passed")

if __name__ == "__main__":
    test_sse_flow_with_tts()
    test_error_handling()
    print("\n✅ All SSE flow tests passed!")
