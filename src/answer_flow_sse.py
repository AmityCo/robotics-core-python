"""
Server-Sent Events flow for the complete answer pipeline.
Handles validation with Gemini, KM search, and answer generation with OpenAI GPT.
"""

import json
import logging
from datetime import datetime
from typing import Generator, Dict, Any, List
import requests
import re

from src.app_config import config
from src.km_search import KMBatchSearchRequest, batch_search_km
from src.validator import GeminiValidationRequest, validate_with_gemini
from src.generator import OpenAIGenerationRequest, generate_answer_with_openai, stream_answer_with_openai
from src.org_config import load_org_config

# Configure logger
logger = logging.getLogger(__name__)


def get_validation_prompts_from_org_config(org_config, language: str):
    """
    Get validation prompts from organization configuration
    Tries to load from URLs first, falls back to configured prompts
    """
    # Get localization config for the specified language
    localization = None
    for loc in org_config.localization:
        if loc.language == language:
            localization = loc
            break
    
    if not localization:
        # Fallback to default primary language
        for loc in org_config.localization:
            if loc.language == org_config.defaultPrimaryLanguage:
                localization = loc
                break
    
    if not localization:
        raise ValueError(f"No localization found for language {language} or default language {org_config.defaultPrimaryLanguage}")
    
    validation_system_prompt = None
    validation_user_prompt = None
    
    # Try to load system prompt from URL
    if localization.validatorSystemPromptTemplateUrl:
        try:
            response = requests.get(localization.validatorSystemPromptTemplateUrl, timeout=config.REQUEST_TIMEOUT)
            if response.status_code == 200:
                validation_system_prompt = response.text.strip()
                logger.info("Loaded validation system prompt from localization template URL")
            else:
                logger.warning(f"Failed to load validation system prompt from localization template: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to load validation system prompt template: {e}")
    
    # Try to load user prompt from URL
    if localization.validatorTranscriptPromptTemplateUrl:
        try:
            response = requests.get(localization.validatorTranscriptPromptTemplateUrl, timeout=config.REQUEST_TIMEOUT)
            if response.status_code == 200:
                validation_user_prompt = response.text.strip()
                logger.info("Loaded validation user prompt from localization template URL")
            else:
                logger.warning(f"Failed to load validation user prompt from localization template: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to load validation user prompt template: {e}")
    
    # Fallback to Gemini config URLs if localization URLs didn't work
    if not validation_system_prompt and org_config.gemini.validatorSystemPromptTemplateUrl:
        try:
            response = requests.get(org_config.gemini.validatorSystemPromptTemplateUrl, timeout=config.REQUEST_TIMEOUT)
            if response.status_code == 200:
                validation_system_prompt = response.text.strip()
                logger.info("Loaded validation system prompt from Gemini template URL")
            else:
                logger.warning(f"Failed to load validation system prompt from Gemini template: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to load validation system prompt from Gemini template: {e}")
    
    if not validation_user_prompt and org_config.gemini.validatorTranscriptPromptTemplateUrl:
        try:
            response = requests.get(org_config.gemini.validatorTranscriptPromptTemplateUrl, timeout=config.REQUEST_TIMEOUT)
            if response.status_code == 200:
                validation_user_prompt = response.text.strip()
                logger.info("Loaded validation user prompt from Gemini template URL")
            else:
                logger.warning(f"Failed to load validation user prompt from Gemini template: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to load validation user prompt from Gemini template: {e}")
    
    if not validation_system_prompt or not validation_user_prompt:
        raise ValueError("Could not load validation prompts from organization configuration URLs")
    
    return validation_system_prompt, validation_user_prompt


def execute_answer_flow_sse(transcript: str, language: str, base64_audio: str, org_id: str) -> Generator[str, None, None]:
    """
    Execute the complete answer pipeline with Server-Sent Events.
    Validates with Gemini, searches KM, then generates answer with OpenAI GPT.
    Sends data stage by stage via SSE for real-time progress updates.
    
    Args:
        transcript: The user's transcript
        language: The language of the transcript
        base64_audio: Base64 encoded audio data
        org_id: Organization configuration ID
        
    Yields:
        SSE formatted strings containing progress updates and results
    """
    try:
        # Send initial status
        initial_data = json.dumps({
            'type': 'status', 
            'message': 'Starting answer pipeline', 
            'timestamp': datetime.now().isoformat()
        })
        logger.info("Sending initial SSE message")
        yield f"data: {initial_data}\n\n"
        
        # Load organization configuration
        org_config = load_org_config(org_id)
        if not org_config:
            error_data = {
                'type': 'error',
                'message': f"Organization configuration not found for ID: {org_id}",
                'timestamp': datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            return
        
        logger.info(f"Loaded org config for: {org_config.displayName} (kmId: {org_config.kmId})")
        
        # Get validation prompts from org config
        validation_system_prompt, validation_user_prompt = get_validation_prompts_from_org_config(org_config, language)
        
        # Send validation start status
        validation_start_data = json.dumps({
            'type': 'status', 
            'message': 'Starting validation with Gemini', 
            'timestamp': datetime.now().isoformat()
        })
        logger.info("Sending validation start SSE message")
        yield f"data: {validation_start_data}\n\n"
        
        # Step 1: Perform Gemini validation using the refactored validator
        validator_request = GeminiValidationRequest(
            transcript=transcript,
            language=language,
            base64_audio=base64_audio,
            validation_system_prompt=validation_system_prompt,
            validation_user_prompt=validation_user_prompt,
            model="gemini-2.5-flash",  # Use default model from Gemini config
            generation_config={
                "temperature": 0.1,
                "topP": 0.95,
                "topK": 64,
                "maxOutputTokens": 8192,
                "responseMimeType": "application/json"
            },
            gemini_api_key=org_config.gemini.key
        )
        
        validation_result = validate_with_gemini(validator_request)
        logger.info(f"Validation completed: {validation_result.correction}")

        # Send validation result
        validation_data = {
            'type': 'validation_result',
            'data': {
                'correction': validation_result.correction,
                'searchTerms': validation_result.search_terms
            },
            'timestamp': datetime.now().isoformat()
        }
        validation_json = json.dumps(validation_data)
        yield f"data: {validation_json}\n\n"

        # Send KM search start status
        km_start_data = json.dumps({
            'type': 'status', 
            'message': 'Starting knowledge management search', 
            'timestamp': datetime.now().isoformat()
        })
        yield f"data: {km_start_data}\n\n"

        # Step 2: Perform KM batch search using the validation result
        search_queries: List[str] = []
        
        # Add correction (main query)
        if validation_result.correction:
            search_queries.append(validation_result.correction)
        
        # Add translated question query combined with its keywords
        search_terms = validation_result.search_terms
        if search_terms.get("translatedQuestion", {}).get("query"):
            translated_query = search_terms["translatedQuestion"]["query"]
            translated_keywords = search_terms["translatedQuestion"].get("keywords", [])
            combined_translated_query = " ".join([translated_query] + translated_keywords)
            search_queries.append(combined_translated_query)
        
        # Add all search queries combined with their keywords
        if search_terms.get("searchQueries") and isinstance(search_terms["searchQueries"], list):
            for search_query in search_terms["searchQueries"]:
                if search_query.get("query"):
                    query = search_query["query"]
                    keywords = search_query.get("keywords", [])
                    combined_query = " ".join([query] + keywords)
                    search_queries.append(combined_query)

        # Remove duplicates and empty strings
        unique_queries = list(set([q for q in search_queries if q and q.strip()]))
        
        logger.info(f"Performing KM batch search with queries: {unique_queries}")

        # Perform KM batch search using org config
        km_request = KMBatchSearchRequest(
            queries=unique_queries,
            language=language,
            km_id=org_config.kmId,
            km_token=config.ASAP_KM_TOKEN,  # KM token from environment config
            max_results=10  # Default max results
        )
        
        km_result = batch_search_km(km_request)
        logger.info(f"KM search completed: found {len(km_result.data)} results")

        # Send KM search result
        km_data = {
            'type': 'km_result',
            'data': km_result.dict(),
            'timestamp': datetime.now().isoformat()
        }
        km_json = json.dumps(km_data)
        yield f"data: {km_json}\n\n"

        # Send answer generation start status
        answer_start_data = json.dumps({
            'type': 'status', 
            'message': 'Starting answer generation with OpenAI', 
            'timestamp': datetime.now().isoformat()
        })
        yield f"data: {answer_start_data}\n\n"

        # Step 3: Generate answer using OpenAI GPT with streaming
        generation_request = OpenAIGenerationRequest(
            org_config_id=org_id
        )
        
        # Track the full response for parsing
        full_response = ""
        current_section = "unknown"  # Start with unknown section
        thinking_processed = False  # Track if thinking section has been processed
        thinking_content = ""
        answer_content = ""
        metadata_content = ""
        
        try:
            # Stream the response from OpenAI
            for chunk in stream_answer_with_openai(
                generation_request, 
                km_result, 
                {
                    "correction": validation_result.correction,
                    "searchTerms": validation_result.search_terms
                }
            ):
                full_response += chunk
                
                # First, determine the section type if we haven't yet
                if current_section == "unknown":
                    if "<thinking>" in full_response:
                        current_section = "thinking"
                        continue  # Don't emit anything yet, wait for complete thinking section
                    elif len(full_response) >= 10:  # Wait a bit to see if <thinking> appears
                        # If we have enough content and no <thinking> tag, treat as answer
                        current_section = "answer"
                        # Process all accumulated content as answer
                        if "[meta:docs]" in full_response:
                            parts = full_response.split("[meta:docs]", 1)
                            if parts[0].strip():
                                answer_data = {
                                    'type': 'answer_chunk',
                                    'data': {'content': parts[0].strip()},
                                    'timestamp': datetime.now().isoformat()
                                }
                                yield f"data: {json.dumps(answer_data)}\n\n"
                            
                            metadata_content = "[meta:docs]" + parts[1]
                            current_section = "metadata"
                        else:
                            if full_response.strip():
                                answer_data = {
                                    'type': 'answer_chunk',
                                    'data': {'content': full_response.strip()},
                                    'timestamp': datetime.now().isoformat()
                                }
                                yield f"data: {json.dumps(answer_data)}\n\n"
                    else:
                        # Still waiting to determine section type
                        continue
                
                # Handle thinking section
                elif current_section == "thinking" and not thinking_processed:
                    if "</thinking>" in full_response:
                        # Thinking section is complete
                        thinking_start = full_response.find("<thinking>") + len("<thinking>")
                        thinking_end = full_response.find("</thinking>")
                        thinking_content = full_response[thinking_start:thinking_end]
                        
                        # Send thinking section once
                        thinking_data = {
                            'type': 'thinking',
                            'data': {'content': thinking_content},
                            'timestamp': datetime.now().isoformat()
                        }
                        yield f"data: {json.dumps(thinking_data)}\n\n"
                        
                        thinking_processed = True
                        current_section = "answer"
                        
                        # Process any remaining content after </thinking> as answer
                        remaining_content = full_response[thinking_end + len("</thinking>"):].strip()
                        if remaining_content:
                            if "[meta:docs]" in remaining_content:
                                meta_start = remaining_content.find("[meta:docs]")
                                answer_part = remaining_content[:meta_start]
                                metadata_content = remaining_content[meta_start:]
                                
                                if answer_part.strip():
                                    answer_data = {
                                        'type': 'answer_chunk',
                                        'data': {'content': answer_part.strip()},
                                        'timestamp': datetime.now().isoformat()
                                    }
                                    yield f"data: {json.dumps(answer_data)}\n\n"
                                
                                current_section = "metadata"
                            else:
                                if remaining_content.strip():
                                    answer_data = {
                                        'type': 'answer_chunk',
                                        'data': {'content': remaining_content.strip()},
                                        'timestamp': datetime.now().isoformat()
                                    }
                                    yield f"data: {json.dumps(answer_data)}\n\n"
                    else:
                        # Still collecting thinking content, don't emit anything yet
                        continue
                
                # Handle answer section
                elif current_section == "answer":
                    if "[meta:docs]" in chunk:
                        # Metadata started in this chunk
                        parts = chunk.split("[meta:docs]", 1)
                        if parts[0]:
                            answer_data = {
                                'type': 'answer_chunk',
                                'data': {'content': parts[0]},
                                'timestamp': datetime.now().isoformat()
                            }
                            yield f"data: {json.dumps(answer_data)}\n\n"
                        
                        # Start collecting metadata
                        metadata_content = "[meta:docs]" + parts[1]
                        current_section = "metadata"
                    else:
                        # Pure answer content - stream it immediately
                        answer_data = {
                            'type': 'answer_chunk',
                            'data': {'content': chunk},
                            'timestamp': datetime.now().isoformat()
                        }
                        logger.debug(f"Streaming answer chunk: {chunk[:50]}...")
                        yield f"data: {json.dumps(answer_data)}\n\n"
                
                # Handle metadata section
                elif current_section == "metadata":
                    # Just collect metadata, don't emit yet
                    metadata_content += chunk
            
            # Send metadata if we collected any
            if metadata_content.strip():
                # Parse metadata JSON if possible
                try:
                    # Extract JSON from metadata content
                    json_match = re.search(r'\{[^}]+\}', metadata_content)
                    if json_match:
                        metadata_json = json.loads(json_match.group())
                        metadata_data = {
                            'type': 'metadata',
                            'data': metadata_json,
                            'timestamp': datetime.now().isoformat()
                        }
                        yield f"data: {json.dumps(metadata_data)}\n\n"
                except json.JSONDecodeError:
                    # Send as raw metadata if JSON parsing fails
                    metadata_data = {
                        'type': 'metadata',
                        'data': {'raw': metadata_content.strip()},
                        'timestamp': datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(metadata_data)}\n\n"
            
            logger.info(f"Streaming answer generation completed")
            
        except Exception as e:
            logger.error(f"Error during streaming generation: {str(e)}")
            error_data = {
                'type': 'error',
                'message': f"Streaming generation failed: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            return

        # Send completion status
        completion_data = {
            'type': 'complete',
            'message': 'Answer pipeline completed successfully',
            'timestamp': datetime.now().isoformat()
        }
        yield f"data: {json.dumps(completion_data)}\n\n"

    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        error_data = {
            'type': 'error',
            'message': f"Request failed: {str(e)}",
            'timestamp': datetime.now().isoformat()
        }
        yield f"data: {json.dumps(error_data)}\n\n"
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        error_data = {
            'type': 'error',
            'message': f"Answer generation failed: {str(e)}",
            'timestamp': datetime.now().isoformat()
        }
        yield f"data: {json.dumps(error_data)}\n\n"
