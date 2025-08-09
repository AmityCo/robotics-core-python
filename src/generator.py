"""
OpenAI Generation Module
Handles all OpenAI GPT API generation operations
"""

from datetime import datetime
import json
import logging
import asyncio
import requests
from typing import Dict, Any, List, Optional, Generator
from pydantic import BaseModel
from src.app_config import config
from src.org_config import load_org_config, OrgConfigData
from src.km_search import KMSearchResponse
from src.requests_handler import get, get_sync
from src.models import ChatMessage
from src.groq_handler import GroqHandler, is_groq_model

logger = logging.getLogger(__name__)

def _load_org_config_sync(org_id: str, config_id: str):
    """Synchronous wrapper for async load_org_config function"""
    return asyncio.run(load_org_config(org_id, config_id))

class OpenAIGenerationRequest(BaseModel):
    org_id: str  # Organization ID (partition key)
    config_id: str  # Configuration ID within the organization
    question: str
    language: Optional[str] = None  # Language code (e.g., 'en-US', 'th-TH') - if not provided, uses default
    chat_history: List[ChatMessage] = []  # Previous conversation history
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

def stream_answer_with_openai(
    request: OpenAIGenerationRequest, 
    km_result: KMSearchResponse
) -> Generator[str, None, None]:
    """
    Stream answer generation using OpenAI GPT with KM search results and validation data.
    Yields chunks of text as they are generated.
    """
    logger.info(f"Starting streaming OpenAI generation for org: {request.org_id}, config: {request.config_id}")
    
    # Load organization configuration
    org_config = _load_org_config_sync(request.org_id, request.config_id)
    if not org_config:
        raise ValueError(f"Organization configuration not found for orgId: {request.org_id}, configId: {request.config_id}")
    
    # Delegate to the function that accepts org_config
    yield from stream_answer_with_openai_with_config(request, km_result, org_config)


def stream_answer_with_openai_with_config(
    request: OpenAIGenerationRequest, 
    km_result: KMSearchResponse,
    org_config: OrgConfigData
) -> Generator[str, None, None]:
    """
    Stream answer generation using OpenAI GPT with KM search results and pre-loaded org config.
    Yields chunks of text as they are generated.
    """
    logger.info(f"Starting streaming OpenAI generation for org: {request.org_id}, config: {request.config_id}")
    
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
    # Priority: request.model > localization_config.generatorModel > default "gpt-4.1-mini"
    model = request.model or localization_config.generatorModel or "gpt-4.1-mini"
    api_key = request.openai_api_key or openai_config.apiKey
    temperature = request.temperature if request.temperature is not None else 0.01
    max_tokens = request.max_tokens or 2048
    
    # Log all parameters being used for debugging and transparency
    logger.info(f"OpenAI Generation Parameters:")
    logger.info(f"  Language: {language}")
    logger.info(f"  Localization: {localization_config.language}")
    
    # Log model source for debugging
    if request.model:
        logger.info(f"  Model: {model} (from request override)")
    elif localization_config.generatorModel:
        logger.info(f"  Model: {model} (from localization config)")
    else:
        logger.info(f"  Model: {model} (default)")
    
    logger.info(f"  Temperature: {temperature}")
    logger.info(f"  Max Tokens: {max_tokens}")
    logger.info(f"  API Key: {'***' + api_key[-4:] if api_key and len(api_key) > 4 else 'Not set'}")
    
     
    # Load prompt templates from localization config, otherwise use request prompts
    system_prompt = request.generation_system_prompt or ""
    user_prompt = request.generation_user_prompt or ""
    
    # Load system prompt from localization config if URL is provided
    if localization_config.systemPrompt:
        try:
            response = get_sync(localization_config.systemPrompt, timeout=config.REQUEST_TIMEOUT)
            if response.ok:
                system_prompt = response.text
                logger.info("Loaded system prompt from localization config")
            else:
                logger.warning(f"Failed to load system prompt from localization: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to load system prompt from localization: {e}")
    
    # Load affirmation prompt from localization config if URL is provided
    if localization_config.affirmationPrompt:
        try:
            response = get_sync(localization_config.affirmationPrompt, timeout=config.REQUEST_TIMEOUT)
            if response.ok:
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
    context = "Context: " + km_context + " \nCurrent Time: " + current_time
    
    # Replace {question} placeholder in user prompt
    user_prompt = user_prompt.replace("{question}", request.question)
    
    # Apply formatting template if generatorFormatTextPromptUrl is configured
    format_text_prompt = ""
    if localization_config.generatorFormatTextPromptUrl:
        try:
            response = get_sync(localization_config.generatorFormatTextPromptUrl, timeout=config.REQUEST_TIMEOUT)
            if response.ok:
                format_text_prompt = response.text
                logger.info("Loaded generator format text prompt from URL")
            else:
                logger.warning(f"Failed to load generator format text prompt from URL: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to load generator format text prompt from URL: {e}")
    
    if format_text_prompt:
        logger.info("Applying generator format text prompt template")
        formatted_system_prompt = f"""You're a professional response generator that needs to provide response in 2 consecutive section as followed:

** Section A:
Provide your response according to the following brief:
{system_prompt}
====== END OF SECTION A======
Section B:
Format your response you've just provided in Section A with the following guidelines:
{format_text_prompt}
====== END OF SECTION B======

{context}

[IMPORTANT] You MUST output for format in 2 distinguish sections strictly with the following formatting:
<sectionA>
<Response to section A, ending with [meta:docs]<json> if there are any documents to reference>
</sectionA>
<sectionB>
<Response to section B>
</sectionB>
"""
        system_prompt = formatted_system_prompt
        logger.info("System prompt has been formatted with generatorFormatTextPromptUrl")
        
        # Build messages array with only the formatted system message
        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]
    else:
        logger.info("No generatorFormatTextPromptUrl configured, using original system prompt")
        # Original behavior: separate system and context messages
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "system",
                "content": context
            }
        ]
    
    # Add chat history to messages 
    # if request.chat_history:
    #     for message in request.chat_history:
    #         messages.append({
    #             "role": message.role,
    #             "content": message.content
    #         })
    
    # try adding to user prompt
    if request.chat_history:
        for message in request.chat_history:
            if message.role == "user":
                user_prompt = f"User: {message.content}\n" + user_prompt
            elif message.role == "assistant":
                user_prompt = f"Assistant: {message.content}\n" + user_prompt

    # Add current user question
    messages.append({
        "role": "user", 
        "content": user_prompt
    })

    openai_request_data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,  # Enable streaming
        "stream_options": {"include_usage": True}
    }

    logger.info(f"Final API Request:")
    logger.info(f"  Model: {model}")
    logger.info(f"  Messages count: {len(messages)}")
    logger.info(f"  Temperature: {temperature}")
    logger.info(f"  Max tokens: {max_tokens}")
    logger.info(f"  Chat history length: {len(request.chat_history)}")
    
    # Check if this is a Groq model and prepare request accordingly
    if is_groq_model(model):
        logger.info(f"Detected Groq model: {model}, routing to Groq API")
        
        # Extract the actual model name (remove groq/ prefix)
        actual_model_name = model[5:] if model.startswith("groq/") else model
        
        # Combine system prompts since Groq only supports one
        system_prompts = []
        other_messages = []
        
        for message in messages:
            if message.get("role") == "system":
                system_prompts.append(message.get("content", ""))
            else:
                other_messages.append(message)
        
        # Combine all system prompts into one
        final_messages = []
        if system_prompts:
            combined_system_content = "\n\n".join(filter(None, system_prompts))
            final_messages.append({"role": "system", "content": combined_system_content})
        final_messages.extend(other_messages)
        
        # Prepare Groq API request
        request_data = {
            "model": actual_model_name,
            "messages": final_messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
            "stream": True,
            "top_p": 1.0,
            "reasoning_effort": "medium",
            "stop": None
        }
        
        api_url = "https://api.groq.com/openai/v1/chat/completions"
        auth_header = f"Bearer {org_config.groq.apiKey}"
        
    else:
        logger.info(f"Using OpenAI API")
        
        # Prepare OpenAI API request
        request_data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,  # Enable streaming
            "stream_options": {"include_usage": True}
        }
        
        api_url = f"{config.OPENAI_API_BASE_URL}/chat/completions"
        auth_header = f"Bearer {api_key}"
    
    # Make streaming request (same for both APIs)
    response = requests.post(
        api_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": auth_header
        },
        json=request_data,
        timeout=config.REQUEST_TIMEOUT,
        stream=True
    )

    if not response.ok:
        api_name = "Groq" if is_groq_model(model) else "OpenAI"
        logger.error(f"{api_name} API error: {response.status_code} - {response.text}")
        raise requests.HTTPError(f"{api_name} API returned {response.status_code}: {response.text}")

    # Process streaming response (same for both APIs)
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            api_name = "Groq" if is_groq_model(model) else "OpenAI"
            logger.debug(f"{api_name} response line: {line}")
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
