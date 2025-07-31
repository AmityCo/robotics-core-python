#!/usr/bin/env python3
"""
Demo script to show the new SSE status field functionality
"""
import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.sse_handler import SSEHandler
from src.models import SSEStatus


def demo_status_field_enhancement():
    """Demonstrate the new status field in SSE messages"""
    print("🚀 SSE Status Field Enhancement Demo")
    print("=" * 60)
    
    print("\n📋 Available Status Values:")
    for status in SSEStatus:
        print(f"  • {status.name}: '{status.value}'")
    
    print("\n🔄 Simulating Answer Pipeline with Status Fields:")
    print("-" * 60)
    
    handler = SSEHandler()
    
    # Demo the enhanced messages
    pipeline_steps = [
        (SSEStatus.STARTING, 'Starting answer pipeline'),
        (SSEStatus.VALIDATING, 'Starting validation with Gemini'),
        (SSEStatus.SEARCHING_KM, 'Starting knowledge management search'),
        (SSEStatus.GENERATING_ANSWER, 'Starting answer generation with OpenAI'),
        (SSEStatus.COMPLETE, 'Answer pipeline completed successfully'),
    ]
    
    print("\n📤 Sending Enhanced SSE Messages:")
    for i, (status, message) in enumerate(pipeline_steps, 1):
        if status == SSEStatus.COMPLETE:
            handler.send('complete', message=message, status=status)
        else:
            handler.send('status', message=message, status=status)
        
        print(f"  {i}. {status.name} → '{message}'")
    
    print("\n📥 Received SSE Messages:")
    print("-" * 60)
    
    message_count = 0
    while not handler.queue.empty():
        message_count += 1
        sse_message = handler.queue.get_nowait()
        
        # Parse the SSE message
        data_line = sse_message.strip().split('\n')[0]
        data_json = data_line[6:]  # Remove 'data: ' prefix
        parsed = json.loads(data_json)
        
        # Display the message in a nice format
        print(f"\n📨 Message {message_count}:")
        print(f"   Type: {parsed['type']}")
        print(f"   Status: {parsed['status']} ⭐")  # New field!
        print(f"   Message: {parsed['message']}")
        print(f"   Timestamp: {parsed['timestamp']}")
        
        # Show the raw SSE format
        print(f"   Raw SSE: {repr(sse_message.strip())}")
    
    print("\n✨ Key Benefits:")
    print("  • Clients can now programmatically understand pipeline stages")
    print("  • Status field provides structured data alongside human-readable messages")
    print("  • Backward compatibility maintained for existing clients")
    print("  • Enum ensures consistent status values across the application")
    
    print("\n🔧 Usage for Clients:")
    print("  JavaScript: event.data.status === 'validating'")
    print("  Python: parsed_data['status'] == SSEStatus.VALIDATING.value")
    print("  Any Language: check if status === 'generating_answer'")
    
    print("\n✅ Enhancement Complete!")


def demo_backward_compatibility():
    """Show that backward compatibility is maintained"""
    print("\n🔄 Backward Compatibility Demo:")
    print("-" * 60)
    
    handler = SSEHandler()
    
    # Send old-style message (without status)
    handler.send('status', message='Old style message without status')
    
    # Send new-style message (with status)
    handler.send('status', message='New style message with status', status=SSEStatus.VALIDATING)
    
    print("\n📥 Both Message Styles Work:")
    
    for i in range(2):
        sse_message = handler.queue.get_nowait()
        data_line = sse_message.strip().split('\n')[0]
        data_json = data_line[6:]
        parsed = json.loads(data_json)
        
        print(f"\n📨 Message {i+1}:")
        print(f"   Type: {parsed['type']}")
        if 'status' in parsed:
            print(f"   Status: {parsed['status']} ⭐ (New!)")
        else:
            print(f"   Status: (not present) ✓ (Legacy)")
        print(f"   Message: {parsed['message']}")
    
    print("\n✅ Backward compatibility confirmed!")


if __name__ == '__main__':
    demo_status_field_enhancement()
    demo_backward_compatibility()