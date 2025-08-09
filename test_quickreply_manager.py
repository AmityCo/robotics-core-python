#!/usr/bin/env python3
"""
Test script to verify quickreply_manager functionality
"""

import logging
import asyncio
from src.quickreply_manager import query_quickreply, process_quickreply_script, split_script_into_chunks

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_quickreply_manager():
    """Test the quickreply manager functionality"""
    
    print("=== Testing QuickReply Manager ===")
    
    # Test parameters (replace with real values for actual testing)
    test_config_id = "test_config"
    test_query = "hello"
    test_language = "en-US"
    
    print(f"\n1. Testing quickreply query with:")
    print(f"   Config ID: {test_config_id}")
    print(f"   Query: {test_query}")
    print(f"   Language: {test_language}")
    
    try:
        result = await query_quickreply(test_config_id, test_query, test_language)
        print(f"   Result: has_script={result.has_script}, has_metadata_only={result.has_metadata_only}")
        
        if result.has_script and result.data:
            print(f"\n2. Testing script processing:")
            script_content, metadata = process_quickreply_script(result.data)
            print(f"   Script length: {len(script_content)} characters")
            print(f"   Has metadata: {metadata is not None}")
            
            print(f"\n3. Testing script chunking:")
            chunks = split_script_into_chunks(script_content)
            print(f"   Number of chunks: {len(chunks)}")
            for i, chunk in enumerate(chunks):
                print(f"   Chunk {i+1}: '{chunk[:50]}{'...' if len(chunk) > 50 else ''}'")
        
    except Exception as e:
        print(f"   Error: {str(e)}")
        # This is expected if the API is not available or returns 404/500
        print("   (This is expected if the quickreply API is not available)")

if __name__ == "__main__":
    asyncio.run(test_quickreply_manager())
