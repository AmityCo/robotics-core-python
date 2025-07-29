"""
Cached Requests Handler Module
Provides cached HTTP requests with drop-in replacement for requests.get()
"""

import logging
import requests
from typing import Optional, Dict, Any, Union
from requests import Response
from .cache_config import create_cache
from .app_config import AppConfig

logger = logging.getLogger(__name__)

# Create dedicated cache for HTTP requests - similar config to org_config cache
requests_cache = create_cache("requests_cache_memory", backend="mem://", enabled=True)

class CachedResponse:
    """
    A response-like object that mimics requests.Response for cached content
    """
    def __init__(self, text: str, status_code: int = 200, encoding: str = 'utf-8', 
                 headers: Optional[Dict[str, str]] = None, url: str = ""):
        self.text = text
        self.status_code = status_code
        self.encoding = encoding
        self.headers = headers or {}
        self.url = url
        self.ok = 200 <= status_code < 300
        self.content = text.encode(encoding)
    
    def json(self):
        """Parse response as JSON"""
        import json
        return json.loads(self.text)

class RequestsHandler:
    """
    Cached HTTP requests handler that provides drop-in replacement for requests.get()
    with automatic UTF-8 encoding and caching for template URLs
    """
    
    def __init__(self, default_timeout: int = None):
        """
        Initialize the RequestsHandler
        
        Args:
            default_timeout: Default timeout for requests (defaults to app config)
        """
        self.default_timeout = default_timeout or AppConfig.REQUEST_TIMEOUT
        
    @requests_cache.early(ttl="15m", early_ttl="3m")
    async def _fetch_url_content(self, url: str, timeout: int) -> Dict[str, Any]:
        """
        Fetch content from URL with caching
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary containing response data
            
        Raises:
            requests.RequestException: If the request fails
        """
        logger.info(f"Fetching content from URL: {url}")
        
        try:
            response = requests.get(url, timeout=timeout)
            
            # Ensure UTF-8 encoding for proper character handling (Thai/Chinese)
            response.encoding = 'utf-8'
            
            # Store response data for caching
            response_data = {
                'text': response.text,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'url': response.url,
                'encoding': response.encoding
            }
            
            logger.info(f"Successfully fetched content from {url} (status: {response.status_code})")
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to fetch content from {url}: {str(e)}")
            raise
    
    async def get(self, url: str, timeout: Optional[int] = None, 
                  **kwargs) -> Union[Response, CachedResponse]:
        """
        GET request with caching for template URLs
        
        Args:
            url: URL to request
            timeout: Request timeout (defaults to app config)
            **kwargs: Additional arguments (for compatibility, but cached requests ignore most)
            
        Returns:
            Response object (either real requests.Response or CachedResponse)
        """
        actual_timeout = timeout or self.default_timeout
        
        # Check if this looks like a template URL that should be cached
        should_cache = self._should_cache_url(url)
        
        if should_cache:
            try:
                # Try to get cached content
                response_data = await self._fetch_url_content(url, actual_timeout)
                
                # Return cached response object
                return CachedResponse(
                    text=response_data['text'],
                    status_code=response_data['status_code'],
                    encoding=response_data['encoding'],
                    headers=response_data['headers'],
                    url=response_data['url']
                )
            except Exception as e:
                logger.warning(f"Cache fetch failed for {url}, falling back to direct request: {str(e)}")
                # Fall through to direct request
        
        # For non-cacheable URLs or cache failures, make direct request
        response = requests.get(url, timeout=actual_timeout, **kwargs)
        response.encoding = 'utf-8'  # Always ensure UTF-8 encoding
        return response
    
    def get_sync(self, url: str, timeout: Optional[int] = None, 
                 **kwargs) -> Response:
        """
        Synchronous GET request without caching (for compatibility)
        
        Args:
            url: URL to request
            timeout: Request timeout (defaults to app config)
            **kwargs: Additional arguments passed to requests.get
            
        Returns:
            requests.Response object
        """
        actual_timeout = timeout or self.default_timeout
        response = requests.get(url, timeout=actual_timeout, **kwargs)
        response.encoding = 'utf-8'  # Always ensure UTF-8 encoding
        return response
    
    def _should_cache_url(self, url: str) -> bool:
        """
        Determine if a URL should be cached based on patterns
        
        Args:
            url: URL to check
            
        Returns:
            True if URL should be cached
        """
        # Cache template URLs and other static content
        cache_patterns = [
            'template',
            'prompt',
            'system',
            'affirmation',
            'validator',
            '.txt',
            '.md',
            '.json',
            # Add other patterns as needed
        ]
        
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in cache_patterns)

# Global instance for convenience
_requests_handler = RequestsHandler()

# Drop-in replacement functions
async def get(url: str, timeout: Optional[int] = None, **kwargs) -> Union[Response, CachedResponse]:
    """
    Cached GET request - drop-in replacement for requests.get()
    
    Args:
        url: URL to request
        timeout: Request timeout (defaults to app config)
        **kwargs: Additional arguments
        
    Returns:
        Response object with automatic UTF-8 encoding
    """
    return await _requests_handler.get(url, timeout, **kwargs)

def get_sync(url: str, timeout: Optional[int] = None, **kwargs) -> Response:
    """
    Synchronous GET request without caching - for compatibility
    
    Args:
        url: URL to request
        timeout: Request timeout (defaults to app config)
        **kwargs: Additional arguments passed to requests.get
        
    Returns:
        requests.Response object with UTF-8 encoding
    """
    return _requests_handler.get_sync(url, timeout, **kwargs)

# For backwards compatibility and easier imports
async def cached_get(url: str, timeout: Optional[int] = None, **kwargs) -> Union[Response, CachedResponse]:
    """
    Explicitly cached GET request
    
    Args:
        url: URL to request
        timeout: Request timeout (defaults to app config)
        **kwargs: Additional arguments
        
    Returns:
        Response object with automatic UTF-8 encoding and caching
    """
    return await get(url, timeout, **kwargs)

# Convenience function to clear cache
def clear_cache():
    """Clear the requests cache"""
    try:
        # This will clear the memory cache
        requests_cache.clear()
        logger.info("Requests cache cleared")
    except Exception as e:
        logger.warning(f"Failed to clear requests cache: {str(e)}")

# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_cached_requests():
        """Test the cached requests functionality"""
        
        # Test with a sample URL (replace with actual template URL for testing)
        test_url = "https://httpbin.org/get"
        
        try:
            print("Testing cached GET request...")
            
            # First request - should fetch from URL
            response1 = await get(test_url)
            print(f"First request status: {response1.status_code}")
            print(f"Response type: {type(response1)}")
            
            # Second request - should use cache if URL matches cache patterns
            response2 = await get(test_url)
            print(f"Second request status: {response2.status_code}")
            print(f"Response type: {type(response2)}")
            
            # Test synchronous version
            response3 = get_sync(test_url)
            print(f"Sync request status: {response3.status_code}")
            print(f"Sync response type: {type(response3)}")
            
        except Exception as e:
            print(f"Test failed: {str(e)}")
    
    # Configure logging for testing
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    asyncio.run(test_cached_requests())
