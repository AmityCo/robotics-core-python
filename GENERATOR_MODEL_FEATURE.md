# Generator Model Configuration Feature

## Overview
Added support for configuring the OpenAI generator model per language in the localization configuration. This allows different languages to use different OpenAI models instead of being limited to the default `gpt-4.1-mini`. Also added support for response formatting with `generatorFormatTextPromptUrl`.

## Changes Made

### 1. Added `generatorModel` field to LocalizationConfig
**File:** `src/org_config.py`
- Added `generatorModel: Optional[str] = None` to the `LocalizationConfig` class
- This field allows each language localization to specify its own OpenAI model

### 2. Added `generatorFormatTextPromptUrl` field to LocalizationConfig
**File:** `src/org_config.py`
- Added `generatorFormatTextPromptUrl: Optional[str] = None` to the `LocalizationConfig` class
- This field allows configuring response formatting guidelines URL for structured output

### 3. Updated generator logic to use localization model and formatting
**File:** `src/generator.py`
- Modified the model selection logic in `stream_answer_with_openai_with_config()` 
- **Priority order:** `request.model` > `localization_config.generatorModel` > `"gpt-4.1-mini"` (default)
- Added formatting template logic that creates structured responses with `<sectionA>` and `<sectionB>` XML tags
- Added detailed logging to show which source the model came from

### 4. Updated answer flow to parse XML formatted responses
**File:** `src/answer_flow_sse.py`
- Removed duplicate model extraction logic (now handled in generator)
- Added XML section parsing for `<sectionA>` and `</sectionA>`, `<sectionB>` and `</sectionB>` tags
- Section A content is sent as regular answer chunks
- Section B content is sent as `formatted_answer` SSE events
- Handles thinking sections within Section A
- Supports metadata and session end markers

## Usage

### Configuration
In your organization configuration, you can now specify different models and formatting per language:

```json
{
  "localization": [
    {
      "language": "en-US",
      "generatorModel": "gpt-4o-mini",
      "generatorFormatTextPromptUrl": "https://example.com/format-en.txt",
      // ... other fields
    },
    {
      "language": "th-TH", 
      "generatorModel": "gpt-4o",
      "generatorFormatTextPromptUrl": "https://example.com/format-th.txt",
      // ... other fields
    }
  ]
}
```

### Formatted Response Structure
When `generatorFormatTextPromptUrl` is configured, the response follows this XML structure:

```xml
<sectionA>
<thinking>Intent: locate Chanel shop; Relevant docs: doc-407; Resolution: direct document retrieval</thinking>
Chanel is on Level 3 <break/> 
Opening Hours: 10am - 10pm <break/> 
Category: Beauty & Personal Care <break/> 
(Located in the CHANEL BEAUTÉ Boutique) <break/>
</sectionA>
<sectionB>
📍 Level 3  
⏰ 10 am – 10 pm  
• CHANEL BEAUTÉ Boutique, Beauty & Personal Care  
</sectionB>
```

### SSE Events
- **Section A** content is sent as regular `answer_chunk` events
- **Section B** content is sent as `formatted_answer` events
- **Thinking** sections within Section A are sent as `thinking` events

### Priority
The model selection follows this priority:
1. **Request Override:** If `OpenAIGenerationRequest.model` is provided
2. **Localization Config:** If `localization_config.generatorModel` is set for the language
3. **Default:** Falls back to `"gpt-4.1-mini"`

### Logging
The system now logs which source the model came from:
- `"Using OpenAI model from request: {model}"` - when request overrides
- `"Using OpenAI model from localization config: {model}"` - when using localization config
- `"Using default OpenAI model: {model}"` - when using default

## Backward Compatibility
This change is fully backward compatible. Existing configurations without the `generatorModel` or `generatorFormatTextPromptUrl` fields will continue to use the default `gpt-4.1-mini` model and standard response format.
