#!/usr/bin/env python3
"""
Compare regular API vs SSE API performance and experience
"""

import requests
import json
import time
from datetime import datetime

# Test payload
payload = {
    "transcript": "How do I reset my password?",
    "language": "en", 
    "base64_audio": "",  # Empty for demo
    "org_id": "spw-internal-3"
}

def test_regular_api():
    print("🔄 Testing Regular API...")
    start_time = time.time()
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/answer",
            json=payload,
            timeout=30
        )
        
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Regular API completed in {end_time - start_time:.2f} seconds")
            print(f"   Answer: {result.get('answer', '')[:100]}...")
            return True
        else:
            print(f"❌ Regular API failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Regular API error: {e}")
        return False

def test_sse_api():
    print("📡 Testing SSE API...")
    start_time = time.time()
    events_received = []
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/answer-sse",
            json=payload,
            stream=True,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ SSE API failed: HTTP {response.status_code}")
            return False
        
        final_answer = ""
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        event_type = data.get('type')
                        timestamp = data.get('timestamp')
                        
                        events_received.append({
                            'type': event_type,
                            'timestamp': timestamp,
                            'time_since_start': time.time() - start_time
                        })
                        
                        if event_type == 'answer_result':
                            answer_data = data.get('data', {})
                            final_answer = answer_data.get('answer', '')
                        
                        elif event_type == 'complete':
                            break
                            
                        elif event_type == 'error':
                            print(f"❌ SSE API error: {data.get('message')}")
                            return False
                            
                    except json.JSONDecodeError:
                        continue
        
        end_time = time.time()
        
        print(f"✅ SSE API completed in {end_time - start_time:.2f} seconds")
        print(f"   Events received: {len(events_received)}")
        print(f"   Answer: {final_answer[:100]}...")
        
        print("   📊 Event timeline:")
        for event in events_received:
            print(f"     {event['time_since_start']:6.2f}s - {event['type']}")
        
        return True
        
    except Exception as e:
        print(f"❌ SSE API error: {e}")
        return False

def main():
    print("=== API Comparison Demo ===")
    print(f"Test payload: {payload['transcript']}")
    print()
    
    # Test both APIs
    regular_success = test_regular_api()
    print()
    sse_success = test_sse_api()
    
    print()
    print("=== Summary ===")
    if regular_success and sse_success:
        print("✅ Both APIs working correctly")
        print("🎯 Key differences:")
        print("   • Regular API: Single response after completion")
        print("   • SSE API: Real-time progress updates throughout pipeline")
        print("   • SSE API: Better user experience for long-running requests")
        print("   • SSE API: Detailed timing information for debugging")
    elif not regular_success and not sse_success:
        print("❌ Both APIs failed - check if server is running")
    elif regular_success:
        print("⚠️  Regular API works, SSE API failed")
    else:
        print("⚠️  SSE API works, Regular API failed")

if __name__ == "__main__":
    main()
