#!/usr/bin/env python3
"""
Demo script to show SSE functionality in action
"""

import requests
import json
import time
from datetime import datetime

# Test payload
payload = {
    "transcript": "What is the weather like today?",
    "language": "en", 
    "base64_audio": "",  # Empty for demo
    "org_id": "spw-internal-3"
}

print("=== SSE Answer API Demo ===")
print(f"Sending request at: {datetime.now().isoformat()}")
print(f"Transcript: {payload['transcript']}")
print(f"Language: {payload['language']}")
print()

try:
    # Send SSE request
    response = requests.post(
        "http://localhost:8000/api/v1/answer-sse",
        json=payload,
        stream=True,
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        print(f"Response: {response.text}")
        exit(1)
    
    print("📡 Receiving SSE events:")
    print("-" * 50)
    
    stage_times = {}
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                    event_type = data.get('type', 'unknown')
                    timestamp = data.get('timestamp', '')
                    
                    # Track timing
                    stage_times[event_type] = timestamp
                    
                    # Pretty print based on event type
                    if event_type == 'status':
                        print(f"⏳ Status: {data.get('message')}")
                    
                    elif event_type == 'validation_result':
                        validation_data = data.get('data', {})
                        correction = validation_data.get('correction', '')
                        print(f"✅ Validation Complete: {correction[:100]}...")
                        
                    elif event_type == 'km_result':
                        km_data = data.get('data', {})
                        results_count = len(km_data.get('data', []))
                        print(f"🔍 KM Search Complete: Found {results_count} results")
                        
                    elif event_type == 'answer_result':
                        answer_data = data.get('data', {})
                        answer = answer_data.get('answer', '')
                        model = answer_data.get('model_used', '')
                        print(f"🤖 Answer Generated ({model}): {answer[:100]}...")
                        
                    elif event_type == 'complete':
                        print(f"🎉 Pipeline Complete!")
                        break
                        
                    elif event_type == 'error':
                        print(f"❌ Error: {data.get('message')}")
                        break
                        
                    else:
                        print(f"📨 {event_type}: {data}")
                        
                except json.JSONDecodeError:
                    print(f"Raw line: {line_str}")
    
    print("-" * 50)
    print("📊 Timing Summary:")
    for event, timestamp in stage_times.items():
        if timestamp:
            print(f"  {event}: {timestamp}")
            
except requests.exceptions.ConnectionError:
    print("❌ Connection Error: Make sure the server is running on localhost:8000")
    print("   Start server with: python src/main.py")
    
except requests.exceptions.Timeout:
    print("⏰ Request timed out")
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")

print()
print("Demo completed!")
