#!/usr/bin/env python3
"""
Test the completion registry system in SSEHandler
"""
import time
import threading
from sse_handler import SSEHandler

def test_completion_registry():
    """Test that SSEHandler properly waits for all components to complete"""
    print("Testing SSEHandler completion registry...")
    
    # Create handler
    handler = SSEHandler()
    
    # Register components
    handler.register_component('text_generation')
    handler.register_component('tts_processing')
    
    # Verify handler is not complete initially
    assert not handler.is_complete.is_set(), "Handler should not be complete initially"
    
    # Mark one component complete
    handler.mark_component_complete('text_generation')
    time.sleep(0.1)  # Give a moment for processing
    
    assert not handler.is_complete.is_set(), "Handler should not be complete with only one component done"
    
    # Mark second component complete
    handler.mark_component_complete('tts_processing')
    time.sleep(0.1)  # Give a moment for processing
    
    assert handler.is_complete.is_set(), "Handler should be complete after all components are done"
    
    print("✓ Completion registry test passed")

def test_concurrent_completion():
    """Test completion from multiple threads"""
    print("Testing concurrent completion...")
    
    handler = SSEHandler()
    handler.register_component('component1')
    handler.register_component('component2')
    handler.register_component('component3')
    
    # Function to complete a component after a delay
    def complete_after_delay(component_name, delay):
        time.sleep(delay)
        handler.mark_component_complete(component_name)
    
    # Start threads to complete components
    thread1 = threading.Thread(target=complete_after_delay, args=('component1', 0.1))
    thread2 = threading.Thread(target=complete_after_delay, args=('component2', 0.2))
    thread3 = threading.Thread(target=complete_after_delay, args=('component3', 0.3))
    
    thread1.start()
    thread2.start()
    thread3.start()
    
    # Wait for all threads
    thread1.join()
    thread2.join()
    thread3.join()
    
    # Should be complete now
    assert handler.is_complete.is_set(), "Handler should be complete after all components from threads"
    
    print("✓ Concurrent completion test passed")

def test_message_yielding():
    """Test that messages are yielded until completion"""
    print("Testing message yielding with completion registry...")
    
    handler = SSEHandler()
    handler.register_component('test_component')
    
    # Send some messages
    handler.send('status', message='Starting test')
    handler.send('data', data={'key': 'value'})
    
    # Start yielding messages in a separate thread
    messages = []
    def collect_messages():
        for message in handler.yield_messages():
            messages.append(message)
    
    yield_thread = threading.Thread(target=collect_messages)
    yield_thread.start()
    
    # Give some time for initial messages
    time.sleep(0.1)
    
    # Send more messages
    handler.send('progress', data={'percent': 50})
    time.sleep(0.1)
    
    # Complete the component
    handler.mark_component_complete('test_component')
    
    # Wait for yielding to complete
    yield_thread.join(timeout=2.0)
    
    print(f"Collected {len(messages)} messages")
    
    # Should have at least the messages we sent plus completion
    assert len(messages) >= 4, f"Expected at least 4 messages, got {len(messages)}"
    
    # Last message should be completion
    import json
    last_message_data = json.loads(messages[-1].replace('data: ', '').strip())
    assert last_message_data['type'] == 'complete', "Last message should be completion"
    
    print("✓ Message yielding test passed")

if __name__ == "__main__":
    test_completion_registry()
    test_concurrent_completion()
    test_message_yielding()
    print("\n✅ All tests passed!")
