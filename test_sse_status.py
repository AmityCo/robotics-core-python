#!/usr/bin/env python3
"""
Focused test to validate the SSE status field enhancement
"""
import sys
import os
import json
import threading
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.sse_handler import SSEHandler
from src.models import SSEStatus


def test_sse_status_field():
    """Test that SSE messages now include the status field"""
    print("Testing SSE status field enhancement...")
    
    # Create SSE handler
    handler = SSEHandler()
    
    # Test different status types
    test_cases = [
        ('status', 'Starting answer pipeline', SSEStatus.STARTING),
        ('status', 'Starting validation with Gemini', SSEStatus.VALIDATING),
        ('status', 'Starting knowledge management search', SSEStatus.SEARCHING_KM),
        ('status', 'Starting answer generation with OpenAI', SSEStatus.GENERATING_ANSWER),
        ('complete', 'Answer pipeline completed successfully', SSEStatus.COMPLETE),
        ('error', 'Test error message', SSEStatus.ERROR),
    ]
    
    # Send test messages
    for msg_type, message, status in test_cases:
        if msg_type == 'error':
            handler.send_error(message)
        else:
            handler.send(msg_type, message=message, status=status)
    
    # Collect and verify messages
    messages = []
    while not handler.queue.empty():
        message = handler.queue.get_nowait()
        messages.append(message)
    
    print(f"Generated {len(messages)} SSE messages")
    
    # Verify each message has the expected format
    for i, (expected_type, expected_message, expected_status) in enumerate(test_cases):
        if i >= len(messages):
            print(f"ERROR: Missing message {i+1}")
            return False
            
        message = messages[i]
        
        # Parse SSE message
        if not message.startswith('data: '):
            print(f"ERROR: Message {i+1} doesn't start with 'data: '")
            return False
            
        data_json = message[6:].strip().split('\n')[0]  # Remove 'data: ' and trailing newlines
        
        try:
            parsed = json.loads(data_json)
        except json.JSONDecodeError as e:
            print(f"ERROR: Message {i+1} is not valid JSON: {e}")
            return False
        
        # Verify required fields exist
        required_fields = ['type', 'timestamp', 'message', 'status']
        for field in required_fields:
            if field not in parsed:
                print(f"ERROR: Message {i+1} missing required field '{field}'")
                return False
        
        # Verify field values
        if parsed['type'] != expected_type:
            print(f"ERROR: Message {i+1} type mismatch. Expected: {expected_type}, Got: {parsed['type']}")
            return False
            
        if parsed['message'] != expected_message:
            print(f"ERROR: Message {i+1} message mismatch. Expected: {expected_message}, Got: {parsed['message']}")
            return False
            
        if parsed['status'] != expected_status.value:
            print(f"ERROR: Message {i+1} status mismatch. Expected: {expected_status.value}, Got: {parsed['status']}")
            return False
        
        print(f"✓ Message {i+1}: type={parsed['type']}, status={parsed['status']}, message='{parsed['message']}'")
    
    return True


def test_backward_compatibility():
    """Test that old messages without status still work"""
    print("\nTesting backward compatibility...")
    
    handler = SSEHandler()
    
    # Send message without status (old way)
    handler.send('status', message='Test message without status')
    
    # Get message
    message = handler.queue.get_nowait()
    
    # Parse it
    data_json = message[6:].strip().split('\n')[0]
    parsed = json.loads(data_json)
    
    # Should have type, timestamp, message but not status
    expected_fields = ['type', 'timestamp', 'message']
    for field in expected_fields:
        if field not in parsed:
            print(f"ERROR: Missing required field '{field}'")
            return False
    
    if 'status' in parsed:
        print(f"ERROR: Found unexpected 'status' field when none was provided")
        return False
    
    print("✓ Backward compatibility maintained - messages without status work correctly")
    return True


def test_enum_values():
    """Test that all enum values are valid"""
    print("\nTesting SSE status enum values...")
    
    expected_values = {
        'STARTING': 'starting',
        'VALIDATING': 'validating', 
        'SEARCHING_KM': 'searching_km',
        'GENERATING_ANSWER': 'generating_answer',
        'COMPLETE': 'complete',
        'ERROR': 'error'
    }
    
    for name, expected_value in expected_values.items():
        status = getattr(SSEStatus, name)
        if status.value != expected_value:
            print(f"ERROR: SSEStatus.{name} has value '{status.value}', expected '{expected_value}'")
            return False
        print(f"✓ SSEStatus.{name} = '{status.value}'")
    
    return True


def main():
    """Run all tests"""
    print("SSE Status Field Enhancement Tests")
    print("=" * 50)
    
    all_passed = True
    
    # Test 1: Status field functionality
    if not test_sse_status_field():
        all_passed = False
        print("❌ Status field test FAILED")
    else:
        print("✅ Status field test PASSED")
    
    # Test 2: Backward compatibility
    if not test_backward_compatibility():
        all_passed = False
        print("❌ Backward compatibility test FAILED")
    else:
        print("✅ Backward compatibility test PASSED")
    
    # Test 3: Enum values
    if not test_enum_values():
        all_passed = False
        print("❌ Enum values test FAILED")
    else:
        print("✅ Enum values test PASSED")
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("💥 SOME TESTS FAILED!")
        return 1


if __name__ == '__main__':
    sys.exit(main())