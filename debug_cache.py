#!/usr/bin/env python3
"""
Debug script to test cache functionality
"""

import logging
import asyncio
from src.org_config import org_config_cache

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def main():
    print("=== Cache Debug Info ===")
    print(f"Cache type: {type(org_config_cache)}")
    print(f"Cache backend: {getattr(org_config_cache, '_cache_url', 'Not found')}")
    print(f"Cache enabled: {getattr(org_config_cache, '_is_enable', 'Not found')}")
    
    # Test cache functionality
    @org_config_cache.early(ttl="15m", early_ttl="3m")
    async def test_cached_function(param: str):
        logger.info(f"Function executing with param: {param}")
        return f"result_for_{param}"
    
    print("\n=== Testing Cache ===")
    print("First call:")
    result1 = await test_cached_function("test_param")
    print(f"Result 1: {result1}")
    
    print("\nSecond call (should be cached):")
    result2 = await test_cached_function("test_param")
    print(f"Result 2: {result2}")
    
    print("\nThird call with different param:")
    result3 = await test_cached_function("different_param")
    print(f"Result 3: {result3}")

if __name__ == "__main__":
    asyncio.run(main())
