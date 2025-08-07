"""
Generator Response Parser Module
Handles parsing of OpenAI GPT responses with support for different formats:
- XML sections (<sectionA>, <sectionB>) - tags are stripped from output
- Thinking sections (<thinking>)
- Metadata sections ([meta:docs])
- Session end markers ({#NXENDX#})
"""

import logging
import re
from typing import Dict, Any, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class ParseState(Enum):
    """Enumeration of parsing states"""
    UNKNOWN = "unknown"
    SECTION_A = "section_a"
    SECTION_B = "section_b"
    THINKING = "thinking"
    ANSWER = "answer"
    METADATA = "metadata"
    COMPLETED = "completed"
    SESSION_END = "session_end"


class GeneratorParser:
    """
    Parser for OpenAI generator responses with support for various formats
    """
    
    def __init__(self, 
                 thinking_callback: Callable[[str], None],
                 answer_chunk_callback: Callable[[str], None],
                 voice_answer_chunk_callback: Callable[[str], None],
                 metadata_callback: Callable[[str], None],
                 session_end_callback: Callable[[], None]):
        """
        Initialize the parser with callbacks for different content types
        
        Args:
            thinking_callback: Called when thinking content is parsed
            answer_chunk_callback: Called when regular answer content is parsed
            voice_answer_chunk_callback: Called when Section A voice content is parsed
            metadata_callback: Called when metadata content is parsed
            session_end_callback: Called when session end marker is found
        """
        self.thinking_callback = thinking_callback
        self.answer_chunk_callback = answer_chunk_callback
        self.voice_answer_chunk_callback = voice_answer_chunk_callback
        self.metadata_callback = metadata_callback
        self.session_end_callback = session_end_callback
        
        # Parser state
        self.full_response = ""
        self.current_state = ParseState.UNKNOWN
        self.thinking_processed = False
        self.pending_bracket_buffer = ""
        self.is_formatted_response = False
        
        # Content buffers
        self.metadata_content = ""
    
    def process_chunk(self, chunk: str) -> None:
        """
        Process a new chunk from the streaming response
        
        Args:
            chunk: New text chunk to process
        """
        self.full_response += chunk
        
        # logger.info(f"Processing chunk with full response: {self.full_response}")
        
        # Determine section type if unknown
        if self.current_state == ParseState.UNKNOWN:
            self._detect_response_type()
            return
        
        # Route to appropriate handler based on current state
        if self.current_state == ParseState.SECTION_A:
            self._handle_section_a()
        elif self.current_state == ParseState.SECTION_B:
            self._handle_section_b()
        elif self.current_state == ParseState.THINKING:
            self._handle_thinking_section()
        elif self.current_state == ParseState.ANSWER:
            self._handle_answer_section(chunk)
        elif self.current_state == ParseState.METADATA:
            self._handle_metadata_section(chunk)
        elif self.current_state == ParseState.COMPLETED:
            self._handle_completed_state(chunk)
        # SESSION_END state - skip all remaining content
    
    def finalize(self) -> None:
        """
        Finalize parsing and handle any remaining content
        """
        # Handle any remaining pending bracket buffer
        if self.pending_bracket_buffer.strip():
            if "{#NXENDX#}" in self.pending_bracket_buffer:
                self._handle_session_end_marker(self.pending_bracket_buffer)
            else:
                # Treat as answer content
                self.answer_chunk_callback(self.pending_bracket_buffer.strip())
        
        # Process any collected metadata
        if self.metadata_content.strip():
            self.metadata_callback(self.metadata_content.strip())
        logger.info("Finalized parsing with final answer: %s", self.full_response.strip())
    
    def _detect_response_type(self) -> None:
        """Detect the type of response based on initial content"""
        if "<sectionA>" in self.full_response:
            self.is_formatted_response = True
            self.current_state = ParseState.SECTION_A
            logger.info("Detected formatted response with XML sections")
        elif "<thinking>" in self.full_response:
            # Check if this is thinking within a sectioned response
            if "<sectionA>" in self.full_response:
                self.is_formatted_response = True
                self.current_state = ParseState.SECTION_A
                logger.info("Detected formatted response with XML sections and thinking")
            else:
                self.current_state = ParseState.THINKING
        elif len(self.full_response) >= 20:  # Wait longer to avoid premature detection
            # Check for partial section tags that might still be streaming
            if "<section" in self.full_response and not "<sectionA>" in self.full_response:
                # Partial section tag detected, wait for more content
                return
            
            self.current_state = ParseState.ANSWER
            # Check for immediate metadata
            if "[meta:docs]" in self.full_response:
                self._split_answer_and_metadata()
            else:
                if self.full_response.strip():
                    self.answer_chunk_callback(self.full_response.strip())
    
    def _handle_section_a(self) -> None:
        """Handle Section A parsing"""
        if "<sectionB>" not in self.full_response:
            return  # Still collecting Section A content
        
        # Extract Section A content (excluding XML tags)
        section_a_start = self.full_response.find("<sectionA>") + len("<sectionA>")
        section_b_start = self.full_response.find("<sectionB>")
        section_a_content = self.full_response[section_a_start:section_b_start].strip()
        
        # Remove any closing </sectionA> tag that might be present
        if section_a_content.endswith("</sectionA>"):
            section_a_content = section_a_content[:-len("</sectionA>")].strip()
        
        # Process Section A for thinking and answer content
        if "<thinking>" in section_a_content and "</thinking>" in section_a_content:
            thinking_content = self._extract_thinking_content(section_a_content)
            self.thinking_callback(thinking_content)
            
            # Extract answer content after thinking
            thinking_end = section_a_content.find("</thinking>") + len("</thinking>")
            answer_content = section_a_content[thinking_end:].strip()
        else:
            # No thinking section, entire Section A is answer
            answer_content = section_a_content
        
        # Split Section A content to separate answer from metadata
        if "[meta:docs]" in answer_content:
            parts = answer_content.split("[meta:docs]", 1)
            voice_content = parts[0].strip()
            metadata_part = "[meta:docs]" + parts[1]
            
            # Send clean voice content (without metadata)
            if voice_content:
                self.voice_answer_chunk_callback(voice_content)
            
            # Store metadata for later processing
            self.metadata_content = metadata_part
        else:
            # No metadata, send entire answer content as voice
            if answer_content.strip():
                self.voice_answer_chunk_callback(answer_content.strip())
        
        self.current_state = ParseState.SECTION_B
    
    def _handle_section_b(self) -> None:
        """Handle Section B parsing"""
        # Check for complete Section B
        if "</sectionB>" in self.full_response:
            section_b_content = self._extract_section_b_content()
            
            if section_b_content.strip():
                # Section B content should be treated as regular answer chunks (without XML tags)
                self.answer_chunk_callback(section_b_content.strip())
                logger.info("Sent Section B as answer chunk")
            
            # Check what comes after Section B
            self._handle_post_section_b_content()
            return
        
        # Get current Section B content to check for metadata or session end within it
        section_b_start = self.full_response.find("<sectionB>")
        if section_b_start != -1:
            section_b_content = self.full_response[section_b_start:]
            
            # Check for metadata or session end within Section B content only
            if "[meta:docs]" in section_b_content:
                self._handle_section_b_with_metadata()
            elif "{#NXENDX#}" in section_b_content:
                self._handle_section_b_with_session_end()
    
    def _handle_thinking_section(self) -> None:
        """Handle thinking section parsing for non-formatted responses"""
        if self.thinking_processed or "</thinking>" not in self.full_response:
            return
        
        thinking_content = self._extract_thinking_content(self.full_response)
        self.thinking_callback(thinking_content)
        self.thinking_processed = True
        
        # Process remaining content after thinking
        thinking_end = self.full_response.find("</thinking>") + len("</thinking>")
        remaining_content = self.full_response[thinking_end:].strip()
        
        if remaining_content:
            # Check if remaining content contains section tags - this means it's a formatted response
            if "<sectionA>" in remaining_content:
                self.is_formatted_response = True
                self.current_state = ParseState.SECTION_A
                logger.info("Detected XML sections after thinking - switching to formatted response mode")
                return
            elif "[meta:docs]" in remaining_content:
                self._split_answer_and_metadata(remaining_content)
                return
            else:
                if remaining_content.strip():
                    self.answer_chunk_callback(remaining_content.strip())
        
        # Only switch to ANSWER state if no sections were detected
        self.current_state = ParseState.ANSWER
    
    def _handle_answer_section(self, chunk: str) -> None:
        """Handle regular answer section parsing"""
        # Check for session end marker first
        if "{#NXENDX#}" in chunk:
            self._handle_session_end_marker(chunk)
            return
        
        # Handle pending bracket buffer and new chunk
        content_to_process = self.pending_bracket_buffer + chunk
        self.pending_bracket_buffer = ""
        
        # Look for potential metadata markers
        bracket_start = content_to_process.find('[')
        
        if bracket_start != -1:
            # Send content before bracket as answer
            if bracket_start > 0:
                self.answer_chunk_callback(content_to_process[:bracket_start])
            
            # Process bracket content
            bracket_content = content_to_process[bracket_start:]
            bracket_end = bracket_content.find(']')
            
            if bracket_end != -1:
                # Complete bracketed expression
                complete_bracket = bracket_content[:bracket_end + 1]
                remaining_content = bracket_content[bracket_end + 1:]
                
                if complete_bracket.startswith('[meta:docs]'):
                    # Switch to metadata processing
                    self.metadata_content = complete_bracket + remaining_content
                    self.current_state = ParseState.METADATA
                else:
                    # Not metadata, send as answer
                    self.answer_chunk_callback(complete_bracket)
                    if remaining_content:
                        self.answer_chunk_callback(remaining_content)
            else:
                # Incomplete bracket, buffer it
                self.pending_bracket_buffer = bracket_content
        else:
            # No brackets, send as answer
            self.answer_chunk_callback(content_to_process)
    
    def _handle_metadata_section(self, chunk: str) -> None:
        """Handle metadata section parsing"""
        self.metadata_content += chunk
    
    def _handle_completed_state(self, chunk: str) -> None:
        """Handle completed state (waiting for metadata or end)"""
        if "[meta:docs]" in chunk:
            meta_start = self.full_response.find("[meta:docs]")
            self.metadata_content = self.full_response[meta_start:]
            self.current_state = ParseState.METADATA
        elif "{#NXENDX#}" in chunk:
            self.session_end_callback()
            logger.info("SESSION_ENDED status sent due to {#NXENDX#} marker found after completed sections")
            self.current_state = ParseState.SESSION_END
    def _extract_thinking_content(self, text: str) -> str:
        """Extract thinking content from text"""
        thinking_start = text.find("<thinking>") + len("<thinking>")
        thinking_end = text.find("</thinking>")
        return text[thinking_start:thinking_end]
    
    def _extract_section_b_content(self) -> str:
        """Extract Section B content (excluding XML tags)"""
        section_b_start = self.full_response.find("<sectionB>") + len("<sectionB>")
        section_b_end = self.full_response.find("</sectionB>")
        return self.full_response[section_b_start:section_b_end].strip()
    
    def _handle_post_section_b_content(self) -> None:
        """Handle content that appears after Section B closes"""
        section_b_end = self.full_response.find("</sectionB>") + len("</sectionB>")
        remaining_content = self.full_response[section_b_end:].strip()
        
        if "[meta:docs]" in remaining_content:
            meta_start = remaining_content.find("[meta:docs]")
            self.metadata_content = remaining_content[meta_start:]
            self.current_state = ParseState.METADATA
        elif "{#NXENDX#}" in remaining_content:
            self.session_end_callback()
            logger.info("SESSION_ENDED status sent due to {#NXENDX#} marker found after Section B")
            self.current_state = ParseState.SESSION_END
        else:
            # Section B completed, wait for more content
            self.current_state = ParseState.COMPLETED
    
    def _handle_section_b_with_metadata(self) -> None:
        """Handle Section B that contains metadata"""
        section_b_start = self.full_response.find("<sectionB>") + len("<sectionB>")
        
        # Find metadata within Section B content only
        section_b_content = self.full_response[section_b_start:]
        meta_start_in_section_b = section_b_content.find("[meta:docs]")
        
        if meta_start_in_section_b != -1:
            # Extract Section B content before metadata
            section_b_answer_content = section_b_content[:meta_start_in_section_b].strip()
            
            if section_b_answer_content.strip():
                # Section B content should be treated as regular answer chunks (without XML tags)
                self.answer_chunk_callback(section_b_answer_content.strip())
                logger.info("Sent Section B as answer chunk")
            
            # Set metadata content starting from Section B metadata
            meta_start_global = section_b_start + meta_start_in_section_b
            self.metadata_content = self.full_response[meta_start_global:]
            self.current_state = ParseState.METADATA
    
    def _handle_section_b_with_session_end(self) -> None:
        """Handle Section B that contains session end marker"""
        section_b_start = self.full_response.find("<sectionB>") + len("<sectionB>")
        
        # Find session end marker within Section B content only
        section_b_content = self.full_response[section_b_start:]
        nxend_start_in_section_b = section_b_content.find("{#NXENDX#}")
        
        if nxend_start_in_section_b != -1:
            # Extract Section B content before session end marker
            section_b_answer_content = section_b_content[:nxend_start_in_section_b].strip()
            
            if section_b_answer_content.strip():
                # Section B content should be treated as regular answer chunks (without XML tags)
                self.answer_chunk_callback(section_b_answer_content.strip())
                logger.info("Sent Section B as answer chunk")
        
        self.session_end_callback()
        logger.info("SESSION_ENDED status sent due to {#NXENDX#} marker found in Section B")
        self.current_state = ParseState.SESSION_END
    
    def _split_answer_and_metadata(self, content: Optional[str] = None) -> None:
        """Split content into answer and metadata parts"""
        text = content or self.full_response
        parts = text.split("[meta:docs]", 1)
        
        if parts[0].strip():
            self.answer_chunk_callback(parts[0].strip())
        
        self.metadata_content = "[meta:docs]" + parts[1]
        self.current_state = ParseState.METADATA
    
    def _handle_session_end_marker(self, text: str) -> None:
        """Handle session end marker in text"""
        nxend_index = text.find("{#NXENDX#}")
        content_before_nxend = self.pending_bracket_buffer + text[:nxend_index]
        
        if content_before_nxend.strip():
            self.answer_chunk_callback(content_before_nxend.strip())
        
        self.session_end_callback()
        logger.info("SESSION_ENDED status sent due to {#NXENDX#} marker")
        self.current_state = ParseState.SESSION_END
        self.pending_bracket_buffer = ""


def create_parser(sse_handler, tts_streamer=None):
    """
    Factory function to create a GeneratorParser with appropriate callbacks
    
    Args:
        sse_handler: SSE handler for sending events
        tts_streamer: Optional TTS streamer for audio generation
        
    Returns:
        Configured GeneratorParser instance
    """
    # Create parser instance first to access its state
    parser_instance = None
    
    def thinking_callback(content: str):
        sse_handler.send('thinking', data={'content': content})
    
    def answer_chunk_callback(content: str):
        if content.strip():
            sse_handler.send('answer_chunk', data={'content': content})
            
            # Send to TTS streamer only when formatter is not enabled
            # (in formatter enabled case voice_answer_chunk_callback will do that instead)
            if tts_streamer and parser_instance and not parser_instance.is_formatted_response:
                try:
                    tts_streamer.append_text(content)
                except Exception as e:
                    logger.warning(f"Failed to add text to TTS streamer: {str(e)}")
    
    def voice_answer_chunk_callback(content: str):
        if content.strip():
            # dont send anymore since it's redundant with tts_audio chunk that also includes text
            # sse_handler.send('voice_answer_chunk', data={'content': content})
            
            # Send to TTS streamer if available (Section A is for voice)
            if tts_streamer:
                try:
                    tts_streamer.append_text(content)
                except Exception as e:
                    logger.warning(f"Failed to add voice text to TTS streamer: {str(e)}")
    
    def metadata_callback(content: str):
        # This will be handled by the calling code since it needs km_result for processing
        pass
    
    def session_end_callback():
        from src.models import SSEStatus
        sse_handler.send('status', message=SSEStatus.SESSION_ENDED)
    
    parser_instance = GeneratorParser(
        thinking_callback=thinking_callback,
        answer_chunk_callback=answer_chunk_callback,
        voice_answer_chunk_callback=voice_answer_chunk_callback,
        metadata_callback=metadata_callback,
        session_end_callback=session_end_callback
    )
    
    return parser_instance
