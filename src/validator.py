"""
Gemini Validation Module
Handles all Gemini API validation operations
"""

import json
import logging
import requests
from typing import Dict, Any
from pydantic import BaseModel
from src.app_config import config

logger = logging.getLogger(__name__)

class GeminiValidationRequest(BaseModel):
    transcript: str
    language: str
    base64_audio: str
    validation_system_prompt: str
    validation_user_prompt: str
    model: str
    generation_config: Dict[str, Any]
    gemini_api_key: str

class GeminiValidationResult(BaseModel):
    correction: str
    search_terms: Dict[str, Any]
    raw_response: str

def validate_with_gemini(request: GeminiValidationRequest) -> GeminiValidationResult:
    """
    Validate transcript and audio with Gemini API
    """
    logger.info(f"Starting Gemini validation with model: {request.model}")
    
    gemini_request_data = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": "audio/wav",
                            "data": request.base64_audio
                        }
                    },
                    {
                        "text": request.validation_user_prompt
                    }
                ]
            }
        ],
        "systemInstruction": {
            "parts": [
                {
                    "text": request.validation_system_prompt
                }
            ]
        },
        "generationConfig": {
            **request.generation_config,
            "responseMimeType": "application/json"
        },
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]
    }

    logger.info(f"Calling Gemini API with model: {request.model}")
    
    gemini_response: requests.Response = requests.post(
        f"{config.GEMINI_API_BASE_URL}/models/{request.model}:generateContent",
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": request.gemini_api_key
        },
        json=gemini_request_data,
        timeout=config.REQUEST_TIMEOUT
    )

    if not gemini_response.ok:
        logger.error(f"Gemini API error: {gemini_response.status_code} - {gemini_response.text}")
        raise requests.HTTPError(f"Gemini API returned {gemini_response.status_code}: {gemini_response.text}")

    gemini_data = gemini_response.json()
    logger.info(f"Gemini validator response: {gemini_data}")

    if not gemini_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text"):
        raise ValueError("No response from Gemini validator")

    response_text = gemini_data["candidates"][0]["content"]["parts"][0]["text"]
    
    try:
        validation_result = json.loads(response_text)
        if "correction" not in validation_result:
            raise ValueError("Invalid response format: missing correction field")
        
        return GeminiValidationResult(
            correction=validation_result["correction"],
            search_terms=validation_result.get("searchTerms", {}),
            raw_response=response_text
        )
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}, raw_response: {response_text}")
        raise ValueError(f"Failed to parse Gemini response as JSON: {str(e)}")
