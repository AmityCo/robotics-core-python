#!/usr/bin/env python3
"""
Test script for chat history functionality in the /answer-sse API
"""

import requests
import json
import base64
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
API_BASE_URL = "http://localhost:8000"
ANSWER_SSE_ENDPOINT = f"{API_BASE_URL}/api/v1/answer-sse"
ORG_ID = "spw-internal-3"

def create_dummy_audio() -> str:
    """Create a dummy base64 audio string for testing"""
    # Create a simple dummy audio data (just some random bytes)
    dummy_audio = b'\x00' * 1024  # 1KB of zero bytes as dummy audio
    return base64.b64encode(dummy_audio).decode('utf-8')

def test_chat_history_api():
    """Test the chat history functionality"""
    
    # Test data
    transcript = "Hello, can you help me?"
    language = "en"
    base64_audio = create_dummy_audio()
    
    # Chat history to test
    chat_history = [
        {"role": "user", "content": "Hi, I'm having trouble with my account"},
        {"role": "assistant", "content": "I'd be happy to help you with your account. What specific issue are you experiencing?"},
        {"role": "user", "content": "I can't log in to my account"}
    ]
    
    # Test payload with chat history
    payload_with_history = {
        "transcript": transcript,
        "language": language,
        "base64_audio": base64_audio,
        "org_id": ORG_ID,
        "chat_history": chat_history
    }
    
    # Test payload without chat history (backward compatibility)
    payload_without_history = {
        "transcript": transcript,
        "language": language,
        "base64_audio": base64_audio,
        "org_id": ORG_ID
    }
    
    logger.info("Testing API with chat history...")
    test_request(payload_with_history, "with chat history")
    
    logger.info("\nTesting API without chat history (backward compatibility)...")
    test_request(payload_without_history, "without chat history")

def test_request(payload: Dict[str, Any], test_name: str):
    """Send a test request and analyze the response"""
    try:
        logger.info(f"Sending request {test_name}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")
        
        # Send request (we'll just test the request structure, not the full SSE stream)
        response = requests.post(
            ANSWER_SSE_ENDPOINT,
            json=payload,
            timeout=5,
            stream=True
        )
        
        if response.status_code == 200:
            logger.info(f"✅ Request {test_name} succeeded (status: {response.status_code})")
        else:
            logger.error(f"❌ Request {test_name} failed (status: {response.status_code})")
            logger.error(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        logger.info(f"⚠️  Request {test_name} timed out (expected for this test)")
    except requests.exceptions.ConnectionError:
        logger.warning(f"⚠️  Connection error for {test_name} - server may not be running")
    except Exception as e:
        logger.error(f"❌ Unexpected error for {test_name}: {e}")

def test_validation_only():
    """Test just the validation logic by importing the modules directly"""
    try:
        from src.validator import GeminiValidationRequest, ChatMessage
        from src.generator import OpenAIGenerationRequest
        
        # Test ChatMessage model
        chat_msg = ChatMessage(role="user", content="Test message")
        logger.info(f"✅ ChatMessage model works: {chat_msg}")
        
        # Test chat history in validation request
        chat_history = [
            ChatMessage(role="user", content="Previous question"),
            ChatMessage(role="assistant", content="Previous answer")
        ]
        
        validation_request = GeminiValidationRequest(
            transcript="Test transcript",
            language="en",
            base64_audio="dummy_audio",
            validation_system_prompt="Test system prompt",
            validation_user_prompt="Test user prompt",
            model="gemini-2.5-flash",
            generation_config={},
            gemini_api_key="dummy_key",
            chat_history=chat_history
        )
        logger.info(f"✅ GeminiValidationRequest with chat history works")
        
        # Test chat history in generation request
        generation_request = OpenAIGenerationRequest(
            org_config_id="test_id",
            question="Test question",
            chat_history=chat_history
        )
        logger.info(f"✅ OpenAIGenerationRequest with chat history works")
        
        logger.info("✅ All model validations passed!")
        
    except Exception as e:
        logger.error(f"❌ Model validation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logger.info("Starting chat history functionality tests")
    
    # Test model validation first
    logger.info("="*50)
    logger.info("Testing model validation...")
    test_validation_only()
    
    # Test API endpoints (requires server to be running)
    logger.info("="*50)
    logger.info("Testing API endpoints...")
    test_chat_history_api()
    
    logger.info("="*50)
    logger.info("Test completed!")