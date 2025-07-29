#!/usr/bin/env python3
"""
Simple test to verify SSE setup and functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app
import uvicorn
import threading
import time
import requests
import json

def start_server():
    """Start the FastAPI server in a separate thread"""
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")

def test_sse_endpoint():
    """Test the SSE endpoint with a simple request"""
    # Wait a bit for server to start
    time.sleep(2)
    
    try:
        # Test data
        payload = {
            "transcript": "Hello, this is a test",
            "language": "en",
            "base64_audio": "",  # Empty for testing
            "org_id": "spw-internal-3"
        }
        
        print("Testing SSE endpoint...")
        response = requests.post(
            "http://127.0.0.1:8001/api/v1/answer-sse",
            json=payload,
            stream=True
        )
        
        print(f"Response status: {response.status_code}")
        print("SSE Events:")
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                        print(f"  {data.get('type', 'unknown')}: {data.get('message', data)}")
                        if data.get('type') == 'complete':
                            break
                    except json.JSONDecodeError:
                        print(f"  Raw: {line_str}")
                        
    except Exception as e:
        print(f"Error testing SSE endpoint: {e}")

if __name__ == "__main__":
    print("Starting SSE test...")
    
    # Start server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Test the endpoint
    test_sse_endpoint()
    
    print("SSE test completed")
