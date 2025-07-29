"""
Cache Configuration Module
Centralized cache setup for the application using cashews with support for multiple cache instances
"""

import os
import logging
from cashews import Cache
from typing import Dict

logger = logging.getLogger(__name__)

# Global cache instances registry
_cache_instances: Dict[str, Cache] = {}

def create_cache(name: str = "default", backend: str = None, enabled: bool = None) -> Cache:
    """
    Create or get a cache instance
    
    Args:
        name: Name of the cache instance (default: "default")
        backend: Cache backend URL (default: auto-detect based on name)
        enabled: Enable/disable caching (default: from environment or True)
        
    Returns:
        Cache instance
    """
    if name in _cache_instances:
        return _cache_instances[name]
    
    # Create new cache instance
    cache = Cache()
    
    # Determine backend if not specified
    if backend is None:
        if name == "memory" or name.endswith("_memory"):
            backend = "mem://"
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            backend = redis_url
    
    # Determine if cache is enabled
    if enabled is None:
        cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    else:
        cache_enabled = enabled
    
    try:
        cache.setup(backend, enable=cache_enabled)
        logger.info(f"Cache '{name}' setup complete. Backend: {backend}, Enabled: {cache_enabled}")
    except Exception as e:
        logger.warning(f"Failed to setup cache '{name}' with backend {backend}. Falling back to memory cache: {str(e)}")
        # Fallback to memory cache if the specified backend is not available
        cache.setup("mem://", enable=cache_enabled)
        logger.info(f"Cache '{name}' using memory cache fallback. Enabled: {cache_enabled}")
    
    # Store in registry
    _cache_instances[name] = cache
    return cache

def get_cache(name: str = "default") -> Cache:
    """
    Get an existing cache instance or create a new one
    
    Args:
        name: Name of the cache instance
        
    Returns:
        Cache instance
    """
    if name not in _cache_instances:
        return create_cache(name)
    return _cache_instances[name]

def setup_cache():
    """
    Setup default cache configuration for backward compatibility
    Can be configured with environment variables:
    - REDIS_URL: Redis connection URL (default: redis://localhost:6379/0)
    - CACHE_ENABLED: Enable/disable caching (default: True)
    """
    return create_cache("default")

# Initialize default cache on module import for backward compatibility
default_cache = setup_cache()
