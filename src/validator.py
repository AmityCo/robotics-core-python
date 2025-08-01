"""
Gemini Validation Module
Handles all Gemini API validation operations
"""

import json
import logging
import requests
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from src.app_config import config
from src.models import ChatMessage

logger = logging.getLogger(__name__)


class GeminiValidationRequest(BaseModel):
    transcript: str
    language: str
    base64_audio: Optional[str] = None  # Made optional to support text-only validation
    validation_system_prompt: str
    validation_user_prompt: str
    model: str
    generation_config: Dict[str, Any]
    gemini_api_key: str
    chat_history: List[ChatMessage] = []


class GeminiValidationResult(BaseModel):
    correction: str
    keywords: list[str]
    raw_response: str


def validate_with_gemini(request: GeminiValidationRequest) -> GeminiValidationResult:
    """
    Validate transcript and audio with Gemini API
    """
    logger.info(f"Starting Gemini validation with model: {request.model}")

    # Build contents array starting with chat history
    contents = []
    
    # Add chat history as previous conversation context
    if request.chat_history:
        for message in request.chat_history:
            # Convert our ChatMessage format to Gemini format
            gemini_role = "user" if message.role == "user" else "model"
            contents.append({
                "role": gemini_role,
                "parts": [{"text": message.content}]
            })
    
    # Add current user message with validation prompt and optional audio
    user_parts = []
    
    # Add audio if provided
    if request.base64_audio:
        user_parts.append({
            "inlineData": {
                "mimeType": "audio/wav",
                "data": request.base64_audio,
            }
        })
    
    # Add the validation prompt with transcript included
    user_parts.append({"text": request.validation_user_prompt
                       .replace("{transcript}", request.transcript)
                      .replace("{language}", request.language)})
    
    contents.append({
        "role": "user",
        "parts": user_parts
    })
    gemini_request_data = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": request.validation_system_prompt}]},
        "generationConfig": {
            **request.generation_config,
            "responseMimeType": "application/json",
            "temperature": 0.0,
            "topP": 0.95,
            # thinking budget is 0 for gemini-2.5-flash and 128 for gemini-2.5-pro
            "thinkingConfig": {"thinkingBudget": 128 if request.model == "gemini-2.5-pro" else 0},
            "responseSchema": {
                "type": "object",
                "properties": {
                    "correction": {"type": "string"},
                    "chat_history": {"type": "array", "items": {"type": "string"}},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["correction", "chat_history", "keywords"],
                "propertyOrdering": ["correction", "chat_history", "keywords"],
            }
        },
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE",
            },
        ],
    }

    logger.info(f"Calling Gemini API with model: {request.model} and {len(request.chat_history)} chat history messages")

    gemini_response: requests.Response = requests.post(
        f"{config.GEMINI_API_BASE_URL}/models/{request.model}:generateContent",
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": request.gemini_api_key,
        },
        json=gemini_request_data,
        timeout=config.REQUEST_TIMEOUT,
    )

    if not gemini_response.ok:
        logger.error(
            f"Gemini API error: {gemini_response.status_code} - {gemini_response.text}"
        )
        raise requests.HTTPError(
            f"Gemini API returned {gemini_response.status_code}: {gemini_response.text}"
        )

    gemini_data = gemini_response.json()
    logger.info(f"Gemini validator response: {gemini_data}")

    if (
        not gemini_data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text")
    ):
        raise ValueError("No response from Gemini validator")

    response_text = gemini_data["candidates"][0]["content"]["parts"][0]["text"]

    # Clean the response text by removing markdown code block formatting
    cleaned_response = response_text.strip()
    
    # Remove opening markdown tags
    if cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response[7:]  # Remove ```json
    elif cleaned_response.startswith("```"):
        cleaned_response = cleaned_response[3:]   # Remove ``` (in case it's just ```)
    
    # Remove closing markdown tags
    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response[:-3]  # Remove closing ```
    
    cleaned_response = cleaned_response.strip()

    try:
        validation_result = json.loads(cleaned_response)
        if "correction" not in validation_result:
            raise ValueError("Invalid response format: missing correction field")

        return GeminiValidationResult(
            correction=validation_result["correction"],
            keywords=validation_result.get("keywords", []),
            raw_response=response_text,
        )
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}, raw_response: {response_text}")
        raise ValueError(f"Failed to parse Gemini response as JSON: {str(e)}")
