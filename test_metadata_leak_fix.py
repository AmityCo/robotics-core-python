#!/usr/bin/env python3
"""
Test script to verify metadata doesn't leak into voice answer chunks
This tests the fix for the issue where [meta:docs] was appearing in TTS audio output.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from generator_parser import GeneratorParser
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test response with metadata in Section A (similar to the problem case)
test_response_with_metadata = """<sectionA>
CHANEL Shoe Boutique is on Level 3 <break/> CHANEL BEAUTÉ Boutique is also on Level 3 <break/> Both are located on Level 3 of Pavilion Kuala Lumpur <break/> [meta:docs] {"doc-ids": "doc-356,doc-407"}
</sectionA>
<sectionB>
📍 **CHANEL Shoe Boutique**  
Level 3 of Pavilion Kuala Lumpur  
⏰ Operating Hours: 10:00 AM - 10:00 PM  

📍 **CHANEL BEAUTÉ Boutique**  
Level 3 of Pavilion Kuala Lumpur  
⏰ Operating Hours: 10:00 AM - 10:00 PM  
</sectionB>"""

# Callback tracking
results = {
    'thinking': [],
    'answer_chunks': [],
    'voice_answer_chunks': [],
    'metadata': [],
    'session_ended': False
}

def thinking_callback(content: str):
    print(f"THINKING: {content}")
    results['thinking'].append(content)

def answer_chunk_callback(content: str):
    print(f"ANSWER_CHUNK: {content}")
    results['answer_chunks'].append(content)

def voice_answer_chunk_callback(content: str):
    print(f"VOICE_ANSWER_CHUNK: {content}")
    results['voice_answer_chunks'].append(content)

def metadata_callback(content: str):
    print(f"METADATA: {content}")
    results['metadata'].append(content)

def session_end_callback():
    print("SESSION_END")
    results['session_ended'] = True

# Create parser
parser = GeneratorParser(
    thinking_callback=thinking_callback,
    answer_chunk_callback=answer_chunk_callback,
    voice_answer_chunk_callback=voice_answer_chunk_callback,
    metadata_callback=metadata_callback,
    session_end_callback=session_end_callback
)

# Test parsing by feeding the complete response as one chunk
print("=== Testing metadata leak fix in Section A ===")
print()

parser.process_chunk(test_response_with_metadata)
parser.finalize()

print("\n=== Results Summary ===")
print(f"Voice answer chunks: {len(results['voice_answer_chunks'])}")
for i, chunk in enumerate(results['voice_answer_chunks']):
    print(f"  Voice {i+1}: {repr(chunk)}")

print(f"\nAnswer chunks: {len(results['answer_chunks'])}")
for i, chunk in enumerate(results['answer_chunks']):
    print(f"  Answer {i+1}: {repr(chunk)}")

print(f"\nMetadata: {len(results['metadata'])}")
for i, meta in enumerate(results['metadata']):
    print(f"  Meta {i+1}: {repr(meta)}")

# Critical verification: Check that voice chunks don't contain metadata
print(f"\n=== Critical Verification ===")
voice_has_metadata = False
for chunk in results['voice_answer_chunks']:
    if "[meta:docs]" in chunk:
        voice_has_metadata = True
        print(f"❌ METADATA LEAK DETECTED in voice chunk: {repr(chunk)}")
        break

if not voice_has_metadata:
    print("✅ NO metadata leak detected in voice answer chunks")

# Verify that Section A content (without metadata) is in voice chunks
voice_has_section_a = False
for chunk in results['voice_answer_chunks']:
    if "CHANEL Shoe Boutique is on Level 3" in chunk and "[meta:docs]" not in chunk:
        voice_has_section_a = True
        print("✅ Section A content (without metadata) found in voice chunks")
        break

if not voice_has_section_a:
    print("❌ Section A content NOT found in voice chunks")

# Verify that metadata is properly captured
metadata_captured = False
for meta in results['metadata']:
    if "[meta:docs]" in meta and "doc-356,doc-407" in meta:
        metadata_captured = True
        print("✅ Metadata properly captured in metadata callback")
        break

if not metadata_captured:
    print("❌ Metadata NOT properly captured")

# Verify that Section B is in answer chunks
section_b_found = False
for chunk in results['answer_chunks']:
    if "CHANEL Shoe Boutique" in chunk and "📍" in chunk:
        section_b_found = True
        print("✅ Section B content found in answer chunks")
        break

if not section_b_found:
    print("❌ Section B content NOT found in answer chunks")

print("\n=== Test Summary ===")
if not voice_has_metadata and voice_has_section_a and metadata_captured and section_b_found:
    print("🎉 ALL TESTS PASSED - Metadata leak fix is working correctly!")
else:
    print("💥 SOME TESTS FAILED - Fix needs more work")
