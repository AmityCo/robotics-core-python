#!/usr/bin/env python3
"""
Test script to verify org_config caching is working
"""

import logging
import asyncio
import time
from src.org_config import OrgConfig

# Configure logging to see cache behavior
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_caching():
    """Test that caching works by calling the same org_id twice"""
    
    # Initialize org config
    org_config = OrgConfig()
    
    # Test org_id (replace with a real one from your DB)
    test_org_id = "kl-dev"
    
    print("=== Testing Cache Behavior ===")
    
    print("\n1. First call (should hit database):")
    start_time = time.time()
    result1 = await org_config._load_config_from_db(test_org_id)
    end_time = time.time()
    print(f"   Time taken: {end_time - start_time:.3f} seconds")
    print(f"   Result found: {result1 is not None}")
    
    print("\n2. Second call (should use cache):")
    start_time = time.time()
    result2 = await org_config._load_config_from_db(test_org_id)
    end_time = time.time()
    print(f"   Time taken: {end_time - start_time:.3f} seconds")
    print(f"   Result found: {result2 is not None}")
    print(f"   Results match: {result1 == result2}")
    
    print("\n3. Third call with same org_id (should still use cache):")
    start_time = time.time()
    result3 = await org_config._load_config_from_db(test_org_id)
    end_time = time.time()
    print(f"   Time taken: {end_time - start_time:.3f} seconds")
    print(f"   Result found: {result3 is not None}")
    print(f"   Results match: {result1 == result3}")
    
    # If the cache is working, the second and third calls should be much faster
    # and you should only see "Cache MISS" log message for the first call

if __name__ == "__main__":
    asyncio.run(test_caching())
