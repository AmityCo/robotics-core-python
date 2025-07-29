"""
OpenAI Generation Module
Handles all OpenAI GPT API generation operations
"""

from datetime import datetime
import json
import logging
import requests
from typing import Dict, Any, List, Optional, Generator
from pydantic import BaseModel
from src.app_config import config
from src.org_config import load_org_config, OrgConfigData
from src.km_search import KMSearchResponse

logger = logging.getLogger(__name__)

class OpenAIGenerationRequest(BaseModel):
    org_config_id: str
    question: str
    language: Optional[str] = None  # Language code (e.g., 'en-US', 'th-TH') - if not provided, uses default
    # Optional prompts - if not provided, will try to load from org config URLs
    generation_system_prompt: Optional[str] = None
    generation_user_prompt: Optional[str] = None
    # Optional overrides - if not provided, will use org config
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    openai_api_key: Optional[str] = None

class OpenAIGenerationResult(BaseModel):
    answer: str
    model_used: str
    raw_response: str

def generate_answer_with_openai(
    request: OpenAIGenerationRequest, 
    km_result: KMSearchResponse,
    validation_result: Dict[str, Any]
) -> OpenAIGenerationResult:
    """
    Generate an answer using OpenAI GPT with KM search results and validation data
    Uses organization configuration from DynamoDB
    """
    logger.info(f"Starting OpenAI generation for org config: {request.org_config_id}")
    
    # Load organization configuration
    org_config = load_org_config(request.org_config_id)
    if not org_config:
        raise ValueError(f"Organization configuration not found for ID: {request.org_config_id}")
    
    # Get OpenAI and Generator configurations
    openai_config = org_config.openai
    
    # Determine which language localization to use
    language = request.language or org_config.defaultPrimaryLanguage
    localization_config = None
    for loc in org_config.localization:
        if loc.language == language:
            localization_config = loc
            break
    
    if not localization_config:
        logger.warning(f"No localization found for language {language}, using default")
        localization_config = org_config.localization[0] if org_config.localization else None
    
    if not localization_config:
        raise ValueError(f"No localization configuration available")
    
    logger.info(f"Using localization for language: {localization_config.language}")
    
    # Use config values with optional overrides from request
    model = "gpt-4.1-mini" if not request.model else request.model
    api_key = request.openai_api_key or openai_config.apiKey
    temperature = request.temperature if request.temperature is not None else 0.7
    max_tokens = request.max_tokens or 2048
    
    logger.info(f"Using OpenAI model: {model}")
    
    # Load prompt templates from localization config, otherwise use request prompts
    system_prompt = request.generation_system_prompt or ""
    user_prompt = request.generation_user_prompt or ""
    
    # Load system prompt from localization config if URL is provided
    if localization_config.systemPrompt:
        try:
            response = requests.get(localization_config.systemPrompt, timeout=config.REQUEST_TIMEOUT)
            if response.ok:
                response.encoding = 'utf-8'  # Ensure UTF-8 decoding for Thai/Chinese characters
                system_prompt = response.text
                logger.info("Loaded system prompt from localization config")
            else:
                logger.warning(f"Failed to load system prompt from localization: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to load system prompt from localization: {e}")
    
    # Load affirmation prompt from localization config if URL is provided
    if localization_config.affirmationPrompt:
        try:
            response = requests.get(localization_config.affirmationPrompt, timeout=config.REQUEST_TIMEOUT)
            if response.ok:
                response.encoding = 'utf-8'  # Ensure UTF-8 decoding for Thai/Chinese characters
                user_prompt = response.text
                logger.info("Loaded affirmation prompt from localization config")
            else:
                logger.warning(f"Failed to load affirmation prompt from localization: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to load affirmation prompt from localization: {e}")
    
    # Validate that we have prompts (either from request or loaded from config)
    if not system_prompt:
        raise ValueError("No system prompt provided in request and no systemPrompt URL in localization config")
    if not user_prompt:
        raise ValueError("No user prompt provided in request and no affirmationPrompt URL in localization config")
    
    # Prepare context from KM results
    km_context = ""
    if km_result.data:
        km_context = "\n\n=== Knowledge Base Results ===\n"
        for i, item in enumerate(km_result.data[:5], 1):  # Limit to top 5 results
            km_context += f"\n{i}. **Score: {item.rerankerScore:.3f}**\n"
            km_context += f"Content: {item.document.content}\n"
            if item.document.title:
                km_context += f"Title: {item.document.title}\n"
            if item.document.sampleQuestions:
                km_context += f"Sample Questions: {item.document.sampleQuestions}\n"
    else:
        km_context = "\n\n=== Knowledge Base Results ===\nNo relevant results found in the knowledge base.\n"

    # Replace {context} and {current_time} placeholders in system prompt
    current_time = datetime.now().isoformat()
    system_prompt = system_prompt.format(context=km_context, current_time=current_time)
    
    # Replace {question} placeholder in user prompt
    user_prompt = user_prompt.format(question=request.question)
    
    openai_request_data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": user_prompt
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    logger.info(f"Calling OpenAI API with model: {model}")
    
    openai_response: requests.Response = requests.post(
        f"{config.OPENAI_API_BASE_URL}/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        json=openai_request_data,
        timeout=config.REQUEST_TIMEOUT
    )

    if not openai_response.ok:
        logger.error(f"OpenAI API error: {openai_response.status_code} - {openai_response.text}")
        raise requests.HTTPError(f"OpenAI API returned {openai_response.status_code}: {openai_response.text}")

    openai_data = openai_response.json()
    logger.info(f"OpenAI generation response received")

    if not openai_data.get("choices", [{}])[0].get("message", {}).get("content"):
        raise ValueError("No response from OpenAI API")

    answer = openai_data["choices"][0]["message"]["content"]
    
    return OpenAIGenerationResult(
        answer=answer,
        model_used=model,
        raw_response=json.dumps(openai_data)
    )


def stream_answer_with_openai(
    request: OpenAIGenerationRequest, 
    km_result: KMSearchResponse
) -> Generator[str, None, None]:
    """
    Stream answer generation using OpenAI GPT with KM search results and validation data.
    Yields chunks of text as they are generated.
    """
    logger.info(f"Starting streaming OpenAI generation for org config: {request.org_config_id}")
    
    # Load organization configuration
    org_config = load_org_config(request.org_config_id)
    if not org_config:
        raise ValueError(f"Organization configuration not found for ID: {request.org_config_id}")
    
    # Get OpenAI and Generator configurations
    openai_config = org_config.openai
    
    # Determine which language localization to use
    language = request.language or org_config.defaultPrimaryLanguage
    localization_config = None
    for loc in org_config.localization:
        if loc.language == language:
            localization_config = loc
            break
    
    if not localization_config:
        logger.warning(f"No localization found for language {language}, using default")
        localization_config = org_config.localization[0] if org_config.localization else None
    
    if not localization_config:
        raise ValueError(f"No localization configuration available")
    
    logger.info(f"Using localization for language: {localization_config.language}")
    
    # Use config values with optional overrides from request
    model = "gpt-4.1-mini" if not request.model else request.model
    api_key = request.openai_api_key or openai_config.apiKey
    temperature = request.temperature if request.temperature is not None else 0.7
    max_tokens = request.max_tokens or 2048
    
    logger.info(f"Using OpenAI model: {model}")
    
    # Load prompt templates from localization config, otherwise use request prompts
    system_prompt = request.generation_system_prompt or ""
    user_prompt = request.generation_user_prompt or ""
    
    # Load system prompt from localization config if URL is provided
    if localization_config.systemPrompt:
        try:
            response = requests.get(localization_config.systemPrompt, timeout=config.REQUEST_TIMEOUT)
            if response.ok:
                response.encoding = 'utf-8'  # Ensure UTF-8 decoding for Thai/Chinese characters
                system_prompt = response.text
                logger.info("Loaded system prompt from localization config")
            else:
                logger.warning(f"Failed to load system prompt from localization: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to load system prompt from localization: {e}")
    
    # Load affirmation prompt from localization config if URL is provided
    if localization_config.affirmationPrompt:
        try:
            response = requests.get(localization_config.affirmationPrompt, timeout=config.REQUEST_TIMEOUT)
            if response.ok:
                response.encoding = 'utf-8'  # Ensure UTF-8 decoding for Thai/Chinese characters
                user_prompt = response.text
                logger.info("Loaded affirmation prompt from localization config")
            else:
                logger.warning(f"Failed to load affirmation prompt from localization: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to load affirmation prompt from localization: {e}")
    
    # Validate that we have prompts
    if not system_prompt:
        raise ValueError("No system prompt provided in request and no systemPrompt URL in localization config")
    if not user_prompt:
        raise ValueError("No user prompt provided in request and no affirmationPrompt URL in localization config")
    
    # Prepare context from KM results
    km_context = ""
    if km_result.data:
        km_context = "\n\n=== Knowledge Base Results ===\n"
        for i, item in enumerate(km_result.data[:5], 1):  # Limit to top 5 results
            km_context += f"\n{i}. **Score: {item.rerankerScore:.3f}**\n"
            km_context += f"Content: {item.document.content}\n"
            if item.document.title:
                km_context += f"Title: {item.document.title}\n"
            if item.document.sampleQuestions:
                km_context += f"Sample Questions: {item.document.sampleQuestions}\n"
    else:
        km_context = "\n\n=== Knowledge Base Results ===\nNo relevant results found in the knowledge base.\n"
    
    # Replace {context} and {current_time} placeholders in system prompt
    current_time = datetime.now().isoformat()
    system_prompt = system_prompt.replace("{context}", km_context).replace("{current_time}", current_time)

    # Replace {question} placeholder in user prompt
    user_prompt = user_prompt.replace("{question}", request.question)

    openai_request_data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": user_prompt
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True  # Enable streaming
    }

    logger.info(f"Calling OpenAI API with streaming for model: {model}")
    
    # Make streaming request to OpenAI
    response = requests.post(
        f"{config.OPENAI_API_BASE_URL}/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        json=openai_request_data,
        timeout=config.REQUEST_TIMEOUT,
        stream=True
    )

    if not response.ok:
        logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
        raise requests.HTTPError(f"OpenAI API returned {response.status_code}: {response.text}")

    # Process streaming response
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data_str = line[6:]  # Remove 'data: ' prefix
                if data_str.strip() == '[DONE]':
                    break
                
                try:
                    data = json.loads(data_str)
                    if 'choices' in data and len(data['choices']) > 0:
                        delta = data['choices'][0].get('delta', {})
                        if 'content' in delta:
                            content = delta['content']
                            if content:
                                yield content
                except json.JSONDecodeError:
                    continue
