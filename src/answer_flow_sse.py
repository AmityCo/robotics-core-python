"""
Server-Sent Events flow for the complete answer pipeline.
Handles validation with Gemini, KM search, and answer generation with OpenAI GPT.
"""
import json
import logging
import threading
import base64
import re
import asyncio
import os
import random
from typing import Generator, Dict, List, Optional
from requests import RequestException

from src.sse_handler import SSEHandler
from src.app_config import config
from src.requests_handler import get as cached_get
from src.km_search import KMBatchSearchRequest, batch_search_km
from src.validator import GeminiValidationRequest, validate_with_gemini
from src.generator import OpenAIGenerationRequest, stream_answer_with_openai_with_config
from src.org_config import load_org_config
from src.tts_stream import TTSStreamer
from src.models import ChatMessage, SSEStatus
from src.km_data_formatter import extract_relevant_km_data
from src.audio_helper import AudioProcessor

# Configure logger
logger = logging.getLogger(__name__)


def get_random_processing_message(org_config, language: str) -> str:
    """
    Get a random processing message for the specified language from org config.
    
    Args:
        org_config: The organization configuration
        language: Language code (e.g., 'en-US', 'th-TH')
        
    Returns:
        Random processing transcript text for the language
    """
    try:
        # First try to get from avatar.processing in resources
        if (hasattr(org_config, 'resources') and 
            org_config.resources and 
            hasattr(org_config.resources, 'avatar') and 
            org_config.resources.avatar):
            
            avatar_dict = org_config.resources.avatar
            if isinstance(avatar_dict, dict) and 'processing' in avatar_dict:
                processing_items = avatar_dict['processing']
                
                # Filter items for the specified language
                language_items = [item for item in processing_items 
                                if isinstance(item, dict) and 
                                item.get('language') == language and 
                                'transcript' in item]
                
                if language_items:
                    # Pick a random item and return its transcript
                    random_item = random.choice(language_items)
                    return random_item['transcript']
        
        # Fallback: try to get from state.processing.message
        if (hasattr(org_config, 'state') and 
            org_config.state and 
            hasattr(org_config.state, 'processing') and 
            org_config.state.processing):
            
            processing_dict = org_config.state.processing
            if isinstance(processing_dict, dict) and 'message' in processing_dict:
                messages = processing_dict['message']
                if isinstance(messages, dict) and language in messages:
                    return messages[language]
        
        # Final fallback: return a default message based on language
        default_messages = {
            'en-US': 'Please wait a moment',
            'th-TH': 'กรุณารอสักครู่ค่ะ',
            'zh-CN': '请稍等片刻',
            'ja-JP': '少しお待ちください',
            'ko-KR': '잠시만 기다려 주세요',
            'ar-AE': 'من فضلك، انتظر لحظة',
            'ru-RU': 'Пожалуйста, подождите минуту'
        }
        
        return default_messages.get(language, 'Please wait a moment')
        
    except Exception as e:
        logger.warning(f"Failed to get processing message for language {language}: {str(e)}")
        return 'Please wait a moment'


async def get_validation_prompts_from_org_config(org_config, language: str):
    """
    Get validation prompts and model from organization configuration
    Tries to load from URLs first, falls back to configured prompts
    Returns: (validation_system_prompt, validation_user_prompt, validator_model)
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
    
    # Get validator model from localization config, fallback to default
    validator_model = localization.validatorModel if localization.validatorModel else "gemini-2.5-flash"
    
    # Try to load system prompt from URL
    if localization.validatorSystemPromptTemplateUrl:
        try:
            response = await cached_get(localization.validatorSystemPromptTemplateUrl, timeout=config.REQUEST_TIMEOUT)
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
            response = await cached_get(localization.validatorTranscriptPromptTemplateUrl, timeout=config.REQUEST_TIMEOUT)
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
            response = await cached_get(org_config.gemini.validatorSystemPromptTemplateUrl, timeout=config.REQUEST_TIMEOUT)
            if response.status_code == 200:
                validation_system_prompt = response.text.strip()
                logger.info("Loaded validation system prompt from Gemini template URL")
            else:
                logger.warning(f"Failed to load validation system prompt from Gemini template: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to load validation system prompt from Gemini template: {e}")
    
    if not validation_user_prompt and org_config.gemini.validatorTranscriptPromptTemplateUrl:
        try:
            response = await cached_get(org_config.gemini.validatorTranscriptPromptTemplateUrl, timeout=config.REQUEST_TIMEOUT)
            if response.status_code == 200:
                validation_user_prompt = response.text.strip()
                logger.info("Loaded validation user prompt from Gemini template URL")
            else:
                logger.warning(f"Failed to load validation user prompt from Gemini template: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to load validation user prompt from Gemini template: {e}")
    
    if not validation_system_prompt or not validation_user_prompt:
        raise ValueError("Could not load validation prompts from organization configuration URLs")
    
    return validation_system_prompt, validation_user_prompt, validator_model

def trim_audio_if_enabled(org_config, base64_audio: Optional[str]) -> Optional[str]:
    """
    Trim audio silence if auto_trim_silent flag is enabled in organization config.
    
    Args:
        org_config: Organization configuration containing audio settings
        base64_audio: Base64 encoded audio data (optional)
        
    Returns:
        Trimmed base64 audio data if trimming is enabled, otherwise original audio
    """
    if not base64_audio:
        return base64_audio
    
    try:
        # Check if auto trimming is enabled in config
        auto_trim_enabled = getattr(org_config.audio, 'auto_trim_silent', False)
        
        if not auto_trim_enabled:
            logger.debug("Audio auto trimming is disabled in organization config")
            return base64_audio
        
        logger.info("Auto trim silent audio is enabled - processing audio")
        
        # Decode base64 audio data
        audio_data = base64.b64decode(base64_audio)
        
        # Create audio processor and trim silence
        audio_processor = AudioProcessor(silence_threshold=0.05, enable_trimming=True)
        trimmed_audio_data = audio_processor.trim_silence(audio_data)
        
        # Re-encode to base64
        trimmed_base64_audio = base64.b64encode(trimmed_audio_data).decode('utf-8')
        
        # Log trimming results
        original_size = len(audio_data)
        trimmed_size = len(trimmed_audio_data)
        size_reduction = original_size - trimmed_size
        size_reduction_percent = (size_reduction / original_size) * 100 if original_size > 0 else 0
        
        logger.info(f"Audio trimming completed: {original_size} bytes -> {trimmed_size} bytes "
                   f"(reduced by {size_reduction} bytes, {size_reduction_percent:.1f}%)")
        
        return trimmed_base64_audio
        
    except Exception as e:
        logger.error(f"Error trimming audio: {str(e)}")
        logger.info("Returning original audio data due to trimming error")
        return base64_audio



async def _execute_answer_pipeline_background(sse_handler: SSEHandler, transcript: str, language: str, base64_audio: Optional[str], org_id: str, config_id: str, chat_history: List[ChatMessage], keywords: Optional[List[str]] = None, transcript_confidence: Optional[float] = None, generate_answer: bool = True):
    """
    Background worker function that executes the answer pipeline.
    Uses SSEHandler to send messages back to the main thread.
    Supports both audio-based and text-only validation.
    If keywords are provided, validation step is skipped.
    If generate_answer is False, the pipeline ends after KM search results are returned.
    """
    try:
        # Send initial status
        sse_handler.send('status', message=SSEStatus.STARTING)
        logger.info("Starting answer pipeline in background thread")
        
        # Load organization configuration
        org_config = await load_org_config(org_id, config_id)
        if not org_config:
            sse_handler.send('status', message=SSEStatus.ERROR)
            sse_handler.send_error(f"Organization configuration not found for orgId: {org_id}, configId: {config_id}")
            return
        
        logger.info(f"Loaded org config for: {org_config.displayName} (kmId: {org_config.kmId})")
        
        # Trim audio silence if enabled in organization config
        base64_audio = trim_audio_if_enabled(org_config, base64_audio)
        
        # Initialize TTS streamer if TTS config is available
        tts_streamer = None
        
        # Register components that need to complete
        sse_handler.register_component('text_generation')
        
        try:
            def tts_audio_callback(text: str, audio_data: bytes):
                """Callback for when TTS audio is ready"""
                tts_audio_data = {
                    'text': text,
                    'language': language,
                    'audio_size': len(audio_data),
                    'audio_data': base64.b64encode(audio_data).decode('utf-8'),
                    'audio_format': 'raw-16khz-16bit-mono-pcm'
                }
                sse_handler.send('tts_audio', data=tts_audio_data)
                logger.info(f"TTS audio sent for text: '{text[:50]}...' (language: {language}, size: {len(audio_data)} bytes)")
            
            tts_streamer = TTSStreamer(org_config, language, audio_callback=tts_audio_callback)
            await tts_streamer.initialize()
            sse_handler.register_component('tts_processing')
            logger.info("TTS streamer initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize TTS streamer: {str(e)}")
            tts_streamer = None
        
        # Check if keywords are provided directly (skip validation)
        if keywords is not None:
            # Skip validation - use provided keywords and transcript directly
            logger.info(f"Skipping validation - using provided keywords: {keywords}")
            # sse_handler.send('status', message=SSEStatus.VALIDATING)
            
            # Create a mock validation result using the transcript and provided keywords
            validation_data = {
                'correction': transcript,  # Use transcript as-is for correction
                'keywords': keywords or []  # Use provided keywords (even if empty)
            }
            
            # Set up variables for KM search
            correction = transcript
            validation_keywords = keywords or []
            
        else:
            # Perform normal validation process
            # Get validation prompts from org config
            validation_system_prompt, validation_user_prompt, validator_model = await get_validation_prompts_from_org_config(org_config, language)
            
            # Send validation start status
            validation_type = "text-based" if base64_audio is None else "audio-based"
            sse_handler.send('status', message=SSEStatus.VALIDATING)
            logger.info(f"Starting {validation_type} validation with Gemini using model: {validator_model}")
            
            # Generate and play processing TTS message at the start of validation
            try:
                processing_message = get_random_processing_message(org_config, language)
                if processing_message and tts_streamer:
                    logger.info(f"Generating TTS for processing message: '{processing_message}' (language: {language})")
                    # Generate TTS for the processing message immediately
                    tts_streamer.append_text(processing_message)
                    tts_streamer.flush()  # Ensure it gets processed immediately
            except Exception as e:
                logger.warning(f"Failed to generate processing TTS: {str(e)}")
            
            # Check transcript confidence threshold
            validation_transcript = transcript
            if transcript_confidence is not None:
                # Get confidence threshold from localization config (higher priority) or gemini config
                confidence_threshold = None
                
                # First try to get from localization config for the current language
                for localization in org_config.localization:
                    if localization.language == language and localization.validatorTranscriptConfidenceThreshold is not None:
                        confidence_threshold = localization.validatorTranscriptConfidenceThreshold
                        break
                
                # Fallback to gemini config if not found in localization
                if confidence_threshold is None and org_config.gemini.validatorTranscriptConfidenceThreshold is not None:
                    confidence_threshold = org_config.gemini.validatorTranscriptConfidenceThreshold
                
                # Apply threshold check if configured
                if confidence_threshold is not None and transcript_confidence < confidence_threshold:
                    validation_transcript = "<transcript not available>"
                    logger.info(f"Transcript confidence {transcript_confidence} below threshold {confidence_threshold}, using placeholder")
                else:
                    logger.info(f"Transcript confidence {transcript_confidence} meets threshold {confidence_threshold}, using original transcript")
            
            # Step 1: Perform Gemini validation using the refactored validator
            validator_request = GeminiValidationRequest(
                transcript=validation_transcript,
                language=language,
                base64_audio=base64_audio,  # This can now be None for text-only validation
                validation_system_prompt=validation_system_prompt,
                validation_user_prompt=validation_user_prompt,
                model=validator_model,
                generation_config={
                    "temperature": 0.01,
                    "topP": 0.95,
                    "topK": 64,
                    "maxOutputTokens": 8192,
                    "responseMimeType": "application/json"
                },
                gemini_api_key=org_config.gemini.key,
                chat_history=chat_history
            )
            
            validation_result = validate_with_gemini(validator_request)
            logger.info(f"Validation completed: {validation_result.correction}")

            # Send validation result
            validation_data = {
                'correction': validation_result.correction,
                'keywords': validation_result.keywords
            }
            sse_handler.send('validation_result', data=validation_data)
            
            # Set up variables for KM search
            correction = validation_result.correction
            validation_keywords = validation_result.keywords

        # Send KM search start status
        sse_handler.send('status', message=SSEStatus.SEARCHING_KM)

        # Step 2: Perform KM batch search using the validation/provided data
        search_queries: List[str] = []
        
        # Add correction (main query)
        if correction:
            search_queries.append(correction)
        
        # add keywords to search queries
        if validation_keywords:
            for keyword in validation_keywords:
                if keyword.strip():
                    search_queries.append(keyword.strip())
        
        # Remove duplicates and empty strings
        unique_queries = list(set([q for q in search_queries if q and q.strip()]))
        
        logger.info(f"Performing KM batch search with queries: {unique_queries}")

        # convert unique_queries into 1 string separated by space
        query_string = ' '.join(unique_queries)
        # Get the assistantKey for the current language from org config
        assistant_key = None
        for localization in org_config.localization:
            if localization.language == language:
                assistant_key = localization.assistantKey
                break
        
        if not assistant_key:
            # Fallback to default primary language if current language not found
            for localization in org_config.localization:
                if localization.language == org_config.defaultPrimaryLanguage:
                    assistant_key = localization.assistantKey
                    break
        
        if not assistant_key:
            raise ValueError(f"No assistantKey found for language {language} or default language {org_config.defaultPrimaryLanguage}")
        
        # Perform KM batch search using org config
        km_request = KMBatchSearchRequest(
            queries=[query_string],
            language=language,
            km_id=org_config.kmId,
            km_token=assistant_key,
            max_results=10
        )
        
        km_result = batch_search_km(km_request)
        logger.info(f"KM search completed: found {len(km_result.data)} results")

        # Send KM search result
        sse_handler.send('km_result', data=km_result.dict())

        # Check if we should skip answer generation
        if not generate_answer:
            logger.info("Skipping answer generation as generate_answer is False")
            sse_handler.send('status', message=SSEStatus.COMPLETE)
            # Mark components as complete to properly end the flow
            if 'text_generation' in sse_handler._completion_registry:
                sse_handler.mark_component_complete('text_generation')
            if 'tts_processing' in sse_handler._completion_registry:
                sse_handler.mark_component_complete('tts_processing')
            return

        # Send answer generation start status
        sse_handler.send('status', message=SSEStatus.GENERATING_ANSWER)


        # Play wait audio after validation completion
        sse_handler.playAudio('wait2.mp3')
        
        # Step 3: Generate answer using OpenAI GPT with streaming
        generation_request = OpenAIGenerationRequest(
            org_id=org_id,
            config_id=config_id,
            question=correction,  # Use the correction from validation or transcript
            chat_history=chat_history,
            language=language
        )
        
        # Helper function to send answer chunk and to TTS
        def send_answer_chunk(content: str):
            """Helper to send answer chunk and send to TTS streamer if available"""
            if content.strip():
                sse_handler.send('answer_chunk', data={'content': content})
                
                # Send to TTS streamer if available
                if tts_streamer:
                    try:
                        tts_streamer.append_text(content)
                    except Exception as e:
                        logger.warning(f"Failed to add text to TTS streamer: {str(e)}")
        
        # Track the full response for parsing
        full_response = ""
        current_section = "unknown"
        thinking_processed = False
        thinking_content = ""
        answer_content = ""
        metadata_content = ""
        
        # Buffer for handling potential metadata markers that span multiple chunks
        pending_bracket_buffer = ""
        
        try:
            # Stream the response from OpenAI - pass org_config to avoid reloading
            for chunk in stream_answer_with_openai_with_config(
                generation_request, 
                km_result,
                org_config
            ):
                full_response += chunk
                
                # First, determine the section type if we haven't yet
                if current_section == "unknown":
                    if "<thinking>" in full_response:
                        current_section = "thinking"
                        continue
                    elif len(full_response) >= 10:
                        current_section = "answer"
                        if "[meta:docs]" in full_response:
                            parts = full_response.split("[meta:docs]", 1)
                            if parts[0].strip():
                                send_answer_chunk(parts[0].strip())
                            
                            metadata_content = "[meta:docs]" + parts[1]
                            current_section = "metadata"
                        else:
                            if full_response.strip():
                                send_answer_chunk(full_response.strip())
                    else:
                        continue
                
                # Handle thinking section
                elif current_section == "thinking" and not thinking_processed:
                    if "</thinking>" in full_response:
                        thinking_start = full_response.find("<thinking>") + len("<thinking>")
                        thinking_end = full_response.find("</thinking>")
                        thinking_content = full_response[thinking_start:thinking_end]
                        
                        # Send thinking section once
                        sse_handler.send('thinking', data={'content': thinking_content})
                        
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
                                    send_answer_chunk(answer_part.strip())
                                
                                current_section = "metadata"
                            else:
                                if remaining_content.strip():
                                    send_answer_chunk(remaining_content.strip())
                    else:
                        continue
                
                # Handle answer section
                elif current_section == "answer":
                    # Check for {#NXENDX#} marker first
                    if "{#NXENDX#}" in chunk:
                        # Process content before the marker
                        nxend_index = chunk.find("{#NXENDX#}")
                        content_before_nxend = pending_bracket_buffer + chunk[:nxend_index]
                        
                        if content_before_nxend.strip():
                            send_answer_chunk(content_before_nxend.strip())
                        
                        # Send SESSION_END status
                        sse_handler.send('status', message=SSEStatus.SESSION_ENDED)
                        logger.info("SESSION_ENDED status sent due to {#NXENDX#} marker found in answer section")
                        current_section = "session_end"
                        pending_bracket_buffer = ""
                        continue
                    
                    # Handle any pending bracket buffer first
                    content_to_process = pending_bracket_buffer + chunk
                    pending_bracket_buffer = ""
                    
                    # Check if this chunk contains a bracket that might be metadata
                    bracket_start = content_to_process.find('[')
                    
                    if bracket_start != -1:
                        # Send any content before the bracket as answer
                        if bracket_start > 0:
                            send_answer_chunk(content_to_process[:bracket_start])
                        
                        # Buffer content from the bracket onwards
                        bracket_content = content_to_process[bracket_start:]
                        
                        # Check if we have a complete bracketed expression
                        bracket_end = bracket_content.find(']')
                        
                        if bracket_end != -1:
                            # We have a complete bracketed expression
                            complete_bracket = bracket_content[:bracket_end + 1]
                            remaining_content = bracket_content[bracket_end + 1:]
                            
                            if complete_bracket.startswith('[meta:docs]'):
                                # This is metadata, switch to metadata section
                                metadata_content = complete_bracket + remaining_content
                                current_section = "metadata"
                            else:
                                # This is not metadata, send as answer content
                                send_answer_chunk(complete_bracket)
                                # Process any remaining content
                                if remaining_content:
                                    send_answer_chunk(remaining_content)
                        else:
                            # Incomplete bracket expression, buffer it
                            pending_bracket_buffer = bracket_content
                    else:
                        # No brackets in this chunk, send as answer
                        send_answer_chunk(content_to_process)
                
                # Handle metadata section
                elif current_section == "metadata":
                    metadata_content += chunk
                
                # Handle session end section - skip all remaining content
                elif current_section == "session_end":
                    continue
            
            # Handle any remaining pending bracket buffer
            if pending_bracket_buffer.strip():
                # Check for {#NXENDX#} in pending content
                if "{#NXENDX#}" in pending_bracket_buffer:
                    # Send content before the marker
                    nxend_index = pending_bracket_buffer.find("{#NXENDX#}")
                    content_before_nxend = pending_bracket_buffer[:nxend_index]
                    
                    if content_before_nxend.strip():
                        send_answer_chunk(content_before_nxend.strip())
                    
                    # Send SESSION_END status
                    sse_handler.send('status', message=SSEStatus.SESSION_ENDED)
                    logger.info("SESSION_ENDED status sent due to {#NXENDX#} marker found in pending buffer")
                else:
                    # If we have pending bracket content, treat it as answer content
                    send_answer_chunk(pending_bracket_buffer.strip())
            
            # Send metadata if we collected any
            if metadata_content.strip():
                try:
                    json_match = re.search(r'\{[^}]+\}', metadata_content)
                    if json_match:
                        metadata_json = json.loads(json_match.group())
                        
                        # Check if metadata has the expected doc-ids key
                        if 'doc-ids' in metadata_json:
                            # Extract relevant data from KM results based on metadata doc-ids
                            relevant_data = extract_relevant_km_data(metadata_json, km_result)
                            
                            # Send the simplified relevant data object directly
                            sse_handler.send('metadata', data=relevant_data)
                            logger.info(f"Sent simplified metadata with {len(relevant_data.get('items', []))} relevant data items")
                        else:
                            # Try to extract doc IDs from any string values in the JSON
                            doc_ids = []
                            for key, value in metadata_json.items():
                                if isinstance(value, str):
                                    # Look for doc-like patterns in the string
                                    doc_matches = re.findall(r'doc[-_]?\w+', value)
                                    doc_ids.extend(doc_matches)
                            
                            if doc_ids:
                                # Create a normalized metadata format
                                normalized_metadata = {'doc-ids': ','.join(doc_ids)}
                                relevant_data = extract_relevant_km_data(normalized_metadata, km_result)
                                sse_handler.send('metadata', data=relevant_data)
                                logger.info(f"Sent metadata with extracted doc-ids from malformed JSON: {doc_ids}")
                            else:
                                # No doc IDs found, send raw metadata
                                sse_handler.send('metadata', data={'raw': metadata_content.strip()})
                                logger.info("No doc-ids found in metadata JSON, sent raw content")
                    else:
                        # No JSON found, try to extract doc IDs from raw text
                        doc_matches = re.findall(r'doc[-_]?\w+', metadata_content)
                        if doc_matches:
                            # Create metadata format from extracted doc IDs
                            normalized_metadata = {'doc-ids': ','.join(doc_matches)}
                            relevant_data = extract_relevant_km_data(normalized_metadata, km_result)
                            sse_handler.send('metadata', data=relevant_data)
                            logger.info(f"Sent metadata with doc-ids extracted from raw text: {doc_matches}")
                        else:
                            # Send raw metadata content as fallback
                            sse_handler.send('metadata', data={'raw': metadata_content.strip()})
                            logger.info("No doc-ids found in raw metadata, sent raw content")
                except json.JSONDecodeError as e:
                    # Try to extract doc IDs from the raw content even if JSON parsing failed
                    doc_matches = re.findall(r'doc[-_]?\w+', metadata_content)
                    if doc_matches:
                        # Create metadata format from extracted doc IDs
                        normalized_metadata = {'doc-ids': ','.join(doc_matches)}
                        relevant_data = extract_relevant_km_data(normalized_metadata, km_result)
                        sse_handler.send('metadata', data=relevant_data)
                        logger.info(f"Sent metadata with doc-ids extracted from malformed JSON: {doc_matches}")
                    else:
                        # Send raw metadata content as final fallback
                        sse_handler.send('metadata', data={'raw': metadata_content.strip()})
                        logger.info("Failed to parse JSON and extract doc-ids, sent raw content")
            
            # Check for {#NXENDX#} after metadata and send SESSION_ENDED
            if metadata_content and "{#NXENDX#}" in metadata_content:
                sse_handler.send('status', message=SSEStatus.SESSION_ENDED)
                logger.info("SESSION_ENDED status sent due to {#NXENDX#} marker found after metadata")
            
            logger.info("Streaming answer generation completed")
            
            # First, flush any remaining TTS content before marking text generation as complete
            if tts_streamer:
                try:
                    logger.info("Flushing remaining TTS content...")
                    tts_streamer.flush()
                    logger.info("Successfully flushed remaining TTS content")
                    # Mark TTS as complete since the new API doesn't have completion callbacks
                    sse_handler.mark_component_complete('tts_processing')
                except Exception as e:
                    logger.error(f"Failed to flush TTS content: {str(e)}")
                    # If TTS fails, still mark it as complete to avoid hanging
                    sse_handler.mark_component_complete('tts_processing')
            else:
                # No TTS streamer available, mark TTS as complete if it was registered
                if 'tts_processing' in sse_handler._completion_registry:
                    sse_handler.mark_component_complete('tts_processing')
            
            # Mark text generation as complete after TTS flush
            sse_handler.mark_component_complete('text_generation')
            
            # Send completion status
            sse_handler.send('status', message=SSEStatus.COMPLETE)
            
        except Exception as e:
            logger.error(f"Error during streaming generation: {str(e)}")
            # print stack trace for debugging
            import traceback
            logger.error(traceback.format_exc())
            sse_handler.send('status', message=SSEStatus.ERROR)
            sse_handler.send_error(f"Streaming generation failed: {str(e)}")
            raise e

        # Don't call mark_complete() here anymore - let the component system handle it

    except RequestException as e:
        logger.error(f"Request error: {str(e)}")
        sse_handler.send('status', message=SSEStatus.ERROR)
        sse_handler.send_error(f"Request failed: {str(e)}")
        # Mark components as complete to avoid hanging
        if 'text_generation' in sse_handler._completion_registry:
            sse_handler.mark_component_complete('text_generation')
        if 'tts_processing' in sse_handler._completion_registry:
            sse_handler.mark_component_complete('tts_processing')
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        # print traceback for debugging
        import traceback
        logger.error(traceback.format_exc())
        # Send error status and message
        sse_handler.send('status', message=SSEStatus.ERROR)
        sse_handler.send_error(f"Answer generation failed: {str(e)}")
        # Mark components as complete to avoid hanging
        if 'text_generation' in sse_handler._completion_registry:
            sse_handler.mark_component_complete('text_generation')
        if 'tts_processing' in sse_handler._completion_registry:
            sse_handler.mark_component_complete('tts_processing')


def _execute_answer_pipeline_sync_wrapper(sse_handler: SSEHandler, transcript: str, language: str, base64_audio: Optional[str], org_id: str, config_id: str, chat_history: List[ChatMessage], keywords: Optional[List[str]] = None, transcript_confidence: Optional[float] = None, generate_answer: bool = True):
    """
    Synchronous wrapper for the async background function
    """
    asyncio.run(_execute_answer_pipeline_background(sse_handler, transcript, language, base64_audio, org_id, config_id, chat_history, keywords, transcript_confidence, generate_answer))


def execute_answer_flow_sse(transcript: str, language: str, base64_audio: Optional[str], org_id: str, config_id: str, chat_history: List[ChatMessage] = None, keywords: Optional[List[str]] = None, transcript_confidence: Optional[float] = None, generate_answer: bool = True) -> Generator[str, None, None]:
    """
    Execute the complete answer pipeline with Server-Sent Events.
    Validates with Gemini, searches KM, then generates answer with OpenAI GPT.
    Sends data stage by stage via SSE for real-time progress updates.
    
    This function creates an SSEHandler and runs the actual pipeline in a background thread,
    while the main thread yields SSE messages from the handler's queue.
    
    Args:
        transcript: The user's transcript
        language: The language of the transcript
        base64_audio: Base64 encoded audio data (optional, for text-only requests can be None)
        org_id: Organization ID (partition key)
        config_id: Configuration ID within the organization
        chat_history: Previous conversation history (optional)
        keywords: If provided, skip validation and use these keywords directly (optional)
        transcript_confidence: Confidence score of the transcript (optional)
        generate_answer: If False, end flow after KM search results are returned (optional, default True)
        
    Yields:
        SSE formatted strings containing progress updates and results
    """
    if chat_history is None:
        chat_history = []
    
    # Create SSE handler
    sse_handler = SSEHandler()
    
    # Start the background thread to execute the pipeline
    pipeline_thread = threading.Thread(
        target=_execute_answer_pipeline_sync_wrapper,
        args=(sse_handler, transcript, language, base64_audio, org_id, config_id, chat_history, keywords, transcript_confidence, generate_answer),
        daemon=True
    )
    pipeline_thread.start()
    
    # Yield messages from the SSE handler queue
    yield from sse_handler.yield_messages()
    # Wait for the background thread to complete
    pipeline_thread.join(timeout=300)  # 5 minute timeout
    if pipeline_thread.is_alive():
        logger.warning("Pipeline thread did not complete within timeout")
