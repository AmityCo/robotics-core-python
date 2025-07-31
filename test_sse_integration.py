#!/usr/bin/env python3
"""
Integration test to verify the SSE status field works in the full pipeline
This test doesn't run the actual pipeline but simulates the message flow
"""
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.sse_handler import SSEHandler
from src.models import SSEStatus


def simulate_answer_pipeline():
    """Simulate the full answer pipeline SSE flow"""
    print("Simulating answer pipeline SSE flow...")
    
    handler = SSEHandler()
    
    # Register components like the real pipeline does
    handler.register_component('text_generation')
    handler.register_component('tts_processing')
    
    # Simulate the sequence of status messages from the real pipeline
    handler.send('status', message='Starting answer pipeline', status=SSEStatus.STARTING)
    handler.send('status', message='Starting validation with Gemini', status=SSEStatus.VALIDATING)
    
    # Simulate validation result
    validation_data = {
        'correction': 'What is the weather today?',
        'keywords': ['weather', 'today']
    }
    handler.send('validation_result', data=validation_data)
    
    handler.send('status', message='Starting knowledge management search', status=SSEStatus.SEARCHING_KM)
    
    # Simulate KM result  
    km_data = {
        'data': [
            {'document': {'content': 'Weather information...', 'title': 'Weather FAQ'}, 'rerankerScore': 0.95}
        ]
    }
    handler.send('km_result', data=km_data)
    
    handler.send('status', message='Starting answer generation with OpenAI', status=SSEStatus.GENERATING_ANSWER)
    
    # Simulate answer chunks
    handler.send('answer_chunk', data={'content': 'Today the weather is'})
    handler.send('answer_chunk', data={'content': ' sunny with a temperature'})
    handler.send('answer_chunk', data={'content': ' of 25°C.'})
    
    # Simulate completion
    handler.mark_component_complete('text_generation')
    handler.mark_component_complete('tts_processing')
    
    # Collect all messages
    messages = []
    for message in handler.yield_messages():
        messages.append(message)
    
    return messages


def verify_pipeline_messages(messages):
    """Verify the messages have the expected format with status fields"""
    print(f"Verifying {len(messages)} messages...")
    
    status_messages = []
    other_messages = []
    
    for message in messages:
        if not message.startswith('data: '):
            continue
            
        data_json = message[6:].strip().split('\n')[0]
        try:
            parsed = json.loads(data_json)
            if parsed.get('type') in ['status', 'complete', 'error']:
                status_messages.append(parsed)
            else:
                other_messages.append(parsed)
        except json.JSONDecodeError:
            continue
    
    print(f"Found {len(status_messages)} status/complete/error messages")
    print(f"Found {len(other_messages)} other messages")
    
    # Verify all status-type messages have the status field
    expected_status_sequence = [
        ('status', SSEStatus.STARTING.value),
        ('status', SSEStatus.VALIDATING.value),
        ('status', SSEStatus.SEARCHING_KM.value),
        ('status', SSEStatus.GENERATING_ANSWER.value),
        ('complete', SSEStatus.COMPLETE.value),
    ]
    
    status_count = 0
    for parsed in status_messages:
        msg_type = parsed.get('type')
        status = parsed.get('status')
        message = parsed.get('message')
        
        if msg_type in ['status', 'complete', 'error']:
            if 'status' not in parsed:
                print(f"ERROR: {msg_type} message missing 'status' field: {parsed}")
                return False
            
            print(f"✓ {msg_type} message: status='{status}', message='{message}'")
            
            # Verify it matches expected sequence if it's a status/complete message
            if status_count < len(expected_status_sequence):
                expected_type, expected_status = expected_status_sequence[status_count]
                if msg_type == expected_type and status == expected_status:
                    status_count += 1
                elif msg_type == expected_type:
                    print(f"ERROR: Expected status '{expected_status}' but got '{status}'")
                    return False
    
    if status_count != len(expected_status_sequence):
        print(f"ERROR: Expected {len(expected_status_sequence)} status messages but processed {status_count}")
        return False
    
    # Verify other messages don't have status field
    for parsed in other_messages:
        if 'status' in parsed:
            print(f"ERROR: Non-status message has unexpected 'status' field: {parsed}")
            return False
    
    return True


def main():
    """Run the integration test"""
    print("SSE Status Field Integration Test")
    print("=" * 50)
    
    messages = simulate_answer_pipeline()
    
    if verify_pipeline_messages(messages):
        print("\n✅ Integration test PASSED!")
        print("Status field enhancement works correctly in simulated pipeline")
        return 0
    else:
        print("\n❌ Integration test FAILED!")
        return 1


if __name__ == '__main__':
    sys.exit(main())