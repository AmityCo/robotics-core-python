"""
QuickReply Manager Module
Handles quickreply query requests with caching for improved performance
"""

import json
import logging
import requests
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel

from .cache_config import create_cache
from .app_config import config

logger = logging.getLogger(__name__)

# Create dedicated cache for quickreply queries
quickreply_cache = create_cache("quickreply_memory", backend="mem://", enabled=True)

class QuickReplyRequest(BaseModel):
    """Request model for quickreply queries"""
    config_id: str
    query: str
    language: str

class QuickReplyResponse(BaseModel):
    """Response model for quickreply queries"""
    script: Optional[str] = None
    metadata: Optional[Any] = None
    query: Optional[str] = None

class QuickReplyResult(BaseModel):
    """Result model containing processed quickreply data"""
    has_script: bool
    has_metadata_only: bool
    data: Optional[Dict[str, Any]] = None
    metadata_only: Optional[Any] = None

# Module-level cached function for quickreply queries
@quickreply_cache.early(ttl="15m", early_ttl="3m")
async def _query_quickreply_cached(config_id: str, query: str, language: str) -> Optional[Dict[str, Any]]:
    """
    Cached function to query the quickreply API
    
    Args:
        config_id: Configuration ID
        query: User query/transcript
        language: Language code
        
    Returns:
        Quickreply API response data if successful, None otherwise
    """
    logger.info(f"Cache MISS: Querying quickreply API for config_id: {config_id}, query: '{query[:50]}...', language: {language}")
    
    payload = {
        "configId": config_id,
        "query": query,
        "language": language
    }
    
    try:
        response = requests.post(
            config.QUICKREPLY_API_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=config.REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Quickreply API response received for config_id: {config_id}")
            return data
        else:
            logger.warning(f"Quickreply API returned status {response.status_code} for config_id: {config_id}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Request error while querying quickreply API: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while querying quickreply API: {str(e)}")
        return None

class QuickReplyManager:
    """
    Manager class for handling quickreply queries with caching
    """
    
    def __init__(self):
        """Initialize the QuickReply manager"""
        pass
    
    async def query_quickreply(self, request: QuickReplyRequest) -> QuickReplyResult:
        """
        Query quickreply API with caching support
        
        Args:
            request: QuickReplyRequest containing config_id, query, and language
            
        Returns:
            QuickReplyResult with processed data and flags
        """
        logger.info(f"Checking for quickreply with config_id: {request.config_id}, query: '{request.query[:50]}...', language: {request.language}")
        
        try:
            # Query the cached API function
            data = await _query_quickreply_cached(request.config_id, request.query, request.language)
            
            if not data:
                logger.info("No quickreply data found - proceeding with normal flow")
                return QuickReplyResult(has_script=False, has_metadata_only=False)
            
            # Parse the response
            script = data.get('script', '').strip()
            metadata = data.get('metadata')
            
            if script:
                # Full quickreply with script - use quickreply flow
                logger.info(f"Quickreply with script found: {data.get('query', '')}")
                return QuickReplyResult(
                    has_script=True,
                    has_metadata_only=False,
                    data=data
                )
            elif metadata:
                # Quickreply with only metadata - use normal flow but preserve metadata
                logger.info("Quickreply with metadata only found - will use normal flow with preserved metadata")
                return QuickReplyResult(
                    has_script=False,
                    has_metadata_only=True,
                    metadata_only=metadata
                )
            else:
                logger.info("No quickreply script or metadata found - proceeding with normal flow")
                return QuickReplyResult(has_script=False, has_metadata_only=False)
                
        except Exception as e:
            logger.warning(f"Failed to check quickreply: {str(e)}")
            # Return empty result to continue with normal flow if quickreply check fails
            return QuickReplyResult(has_script=False, has_metadata_only=False)
    
    def process_quickreply_script(self, quickreply_data: Dict[str, Any]) -> Tuple[str, Optional[Any]]:
        """
        Process quickreply script data and extract script content and metadata
        
        Args:
            quickreply_data: The quickreply data containing script and metadata
            
        Returns:
            Tuple of (script_content, processed_metadata)
        """
        script_content = quickreply_data.get('script', '')
        metadata = quickreply_data.get('metadata')
        
        # Process metadata if present
        processed_metadata = None
        if metadata:
            try:
                # If metadata is a string, try to parse it as JSON
                if isinstance(metadata, str):
                    try:
                        processed_metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        # If it's not valid JSON, send as raw content
                        processed_metadata = {'raw': metadata}
                else:
                    processed_metadata = metadata
                    
                logger.info(f"Processed quickreply metadata: {processed_metadata}")
            except Exception as e:
                logger.warning(f"Failed to process quickreply metadata: {str(e)}")
                processed_metadata = {'raw': str(metadata)}
        
        return script_content, processed_metadata
    
    def split_script_into_chunks(self, script_content: str) -> list[str]:
        """
        Split script content into chunks based on <break/> tags
        
        Args:
            script_content: The script content to split
            
        Returns:
            List of script chunks
        """
        chunks = []
        
        # Check if script content contains <break/> tags for chunking
        if '<break/>' in script_content:
            # Split by <break/> and process each chunk separately
            raw_chunks = script_content.split('<break/>')
            logger.info(f"Splitting quickreply script into {len(raw_chunks)} chunks using <break/> delimiter")
            
            for i, chunk in enumerate(raw_chunks):
                if chunk.strip():  # Only process non-empty chunks
                    # Add <break/> back to all chunks except the last one to maintain TTS behavior
                    chunk_content = chunk.strip()
                    if i < len(raw_chunks) - 1:  # Not the last chunk
                        chunk_content += '<break/>'
                    chunks.append(chunk_content)
                    logger.debug(f"Prepared quickreply chunk {i+1}/{len(raw_chunks)}: '{chunk_content[:50]}...'")
        else:
            # Return the script content as a single chunk if no <break/> tags
            chunks.append(script_content)
        
        return chunks

# Convenience functions for easy usage
async def query_quickreply(config_id: str, query: str, language: str) -> QuickReplyResult:
    """
    Convenience function to query quickreply
    
    Args:
        config_id: Configuration ID
        query: User query/transcript
        language: Language code
        
    Returns:
        QuickReplyResult with processed data and flags
    """
    manager = QuickReplyManager()
    request = QuickReplyRequest(config_id=config_id, query=query, language=language)
    return await manager.query_quickreply(request)

def process_quickreply_script(quickreply_data: Dict[str, Any]) -> Tuple[str, Optional[Any]]:
    """
    Convenience function to process quickreply script data
    
    Args:
        quickreply_data: The quickreply data containing script and metadata
        
    Returns:
        Tuple of (script_content, processed_metadata)
    """
    manager = QuickReplyManager()
    return manager.process_quickreply_script(quickreply_data)

def split_script_into_chunks(script_content: str) -> list[str]:
    """
    Convenience function to split script content into chunks
    
    Args:
        script_content: The script content to split
        
    Returns:
        List of script chunks
    """
    manager = QuickReplyManager()
    return manager.split_script_into_chunks(script_content)
