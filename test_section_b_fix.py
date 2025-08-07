#!/usr/bin/env python3
"""
Test script to verify Section B parsing fix
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from generator_parser import GeneratorParser
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test response with metadata in Section A
test_response = """<sectionA>
CHANEL Shoe Boutique is on Level 3 <break/> CHANEL BEAUTÉ Boutique is on Level 3 <break/> 
[meta:docs] {"doc-ids": "doc-356,doc-407"}
</sectionA>
<sectionB>
📍 Level 3 – CHANEL Shoe Boutique  
⏰ 10 am – 10 pm  

📍 Level 3 – CHANEL BEAUTÉ Boutique  
⏰ 10 am – 10 pm  
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

# Test parsing by feeding chunks
print("=== Testing Section B parsing with metadata in Section A ===")
print()

# Simulate streaming chunks
chunks = [
    "<sectionA>\nCHANEL Shoe Boutique is on Level 3 <break/> CHANEL BEAUTÉ Boutique is on Level 3 <break/> \n[meta:docs] {\"doc-ids\": \"doc-356,doc-407\"}\n</sectionA>\n<sectionB>\n📍 Level 3 – CHANEL Shoe Boutique  \n⏰ 10 am – 10 pm  \n\n📍 Level 3 – CHANEL BEAUTÉ Boutique  \n⏰ 10 am – 10 pm  \n</sectionB>"
]

for i, chunk in enumerate(chunks):
    print(f"Processing chunk {i+1}: {repr(chunk[:50])}...")
    parser.process_chunk(chunk)

# Finalize
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

# Verify expected behavior
print(f"\n=== Verification ===")
expected_section_b = "📍 Level 3 – CHANEL Shoe Boutique  \n⏰ 10 am – 10 pm  \n\n📍 Level 3 – CHANEL BEAUTÉ Boutique  \n⏰ 10 am – 10 pm"

section_b_found = False
for chunk in results['answer_chunks']:
    if "📍 Level 3 – CHANEL Shoe Boutique" in chunk:
        section_b_found = True
        print("✅ Section B content found in answer chunks")
        break

if not section_b_found:
    print("❌ Section B content NOT found in answer chunks")

voice_section_a_found = False
for chunk in results['voice_answer_chunks']:
    if "CHANEL Shoe Boutique is on Level 3" in chunk:
        voice_section_a_found = True
        print("✅ Section A content found in voice answer chunks")
        break

if not voice_section_a_found:
    print("❌ Section A content NOT found in voice answer chunks")
