# Azure OpenAI Issue Report: gpt-4o-transcribe-diarize Not Returning Speaker Segments

**Date:** November 10, 2025  
**Reporter:** Arturo Quiroga  
**Severity:** High - Core functionality not working as documented

## Summary

The `gpt-4o-transcribe-diarize` model successfully transcribes audio but **does not return speaker diarization data** (speaker segments with labels like "Speaker 1", "Speaker 2"). The API only returns a simple `{"text": "..."}` field, missing the expected `segments` array with speaker attribution.

## Environment Details

- **Endpoint:** `aq-ai-foundry-sweden-central.openai.azure.com`
- **Region:** Sweden Central
- **API Version:** `2025-04-01-preview`
- **Model Deployment:** `gpt-4o-transcribe-diarize`
- **Authentication:** API Key (also tested with Azure Entra ID)
- **Client:** REST API (Python requests library)

## Expected Behavior

Based on the [official documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/whats-new#gpt-4o-audio-model-released):

> "The `gpt-4o-transcribe-diarize` speech to text model is released... Diarization is the process of identifying who spoke when in an audio stream. It transforms conversations into speaker-attributed transcripts..."

**Expected API Response:**
```json
{
  "text": "Full transcription...",
  "segments": [
    {
      "speaker": "Speaker 1",
      "text": "Today is Monday, December 13, 2021...",
      "start": 0.0,
      "end": 5.2
    },
    {
      "speaker": "Speaker 2",
      "text": "Thank you for being here...",
      "start": 5.3,
      "end": 8.7
    }
  ]
}
```

## Actual Behavior

**Actual API Response:**
```json
{
  "text": "Today is Monday, December 13, 2021. The time is 8.04 a.m. This is the deposition of Teresa Peters..."
}
```

Only the `text` field is returned. No speaker segments, no speaker labels, no timestamps with speaker attribution.

## Reproduction Steps

### 1. Test Audio File
- **Type:** Legal deposition recording (multiple speakers)
- **Format:** MP3
- **Duration:** ~5 minutes
- **Content:** Clear conversation with at least 2 distinct speakers (attorney and deponent)

### 2. API Request

**Endpoint:**
```
POST https://aq-ai-foundry-sweden-central.openai.azure.com/openai/deployments/gpt-4o-transcribe-diarize/audio/transcriptions?api-version=2025-04-01-preview
```

**Headers:**
```
api-key: <API_KEY>
Content-Type: multipart/form-data
```

**Form Data:**
```
file: <audio_file>
model: gpt-4o-transcribe-diarize
language: en
temperature: 0.0
response_format: json
timestamp_granularities: ["word", "segment"]
chunking_strategy: {"type": "auto"}
include: ["logprobs"]
```

### 3. Python Code to Reproduce

```python
import requests
import os

endpoint = "https://aq-ai-foundry-sweden-central.openai.azure.com"
api_key = os.getenv("AZURE_OPENAI_API_KEY")
api_version = "2025-04-01-preview"

url = f"{endpoint}/openai/deployments/gpt-4o-transcribe-diarize/audio/transcriptions"
headers = {"api-key": api_key}

with open("test_audio.mp3", "rb") as audio_file:
    files = {"file": ("test_audio.mp3", audio_file, "audio/mpeg")}
    data = {
        "model": "gpt-4o-transcribe-diarize",
        "language": "en",
        "temperature": "0.0",
        "response_format": "json",
        "timestamp_granularities": '["word", "segment"]',
        "chunking_strategy": '{"type": "auto"}',
        "include": '["logprobs"]'
    }
    
    response = requests.post(
        url,
        headers=headers,
        files=files,
        data=data,
        params={"api-version": api_version}
    )

print(response.json())
# Output: {"text": "Full transcription..."}
# Missing: segments field with speaker labels
```

## Additional Testing Conducted

### 1. Response Format Testing
- ✅ `response_format: json` - Works, returns only text
- ❌ `response_format: verbose_json` - **Explicitly rejected** with error:
  ```json
  {
    "error": {
      "message": "response_format 'verbose_json' is not compatible with model 'gpt-4o-transcribe-diarize'. Use 'json' or 'text' instead.",
      "type": "invalid_request_error",
      "param": "response_format",
      "code": "unsupported_value"
    }
  }
  ```

### 2. Parameter Combinations Tested
All return only the `text` field, no segments:
- With `timestamp_granularities: ["word", "segment"]`
- With `chunking_strategy: "auto"`
- With `include: ["logprobs"]`
- With and without `word-timestamps` flag
- Various combinations of the above

## Documentation Gaps

### What's Missing:
1. **No response schema documentation** showing what fields are returned
2. **No code samples** demonstrating how to access speaker segments
3. **No examples** of the diarization output format
4. **Conflicting information**: Model name suggests diarization, but API doesn't return it

### Relevant Documentation:
- [What's New - GPT-4o Audio Model](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/whats-new#gpt-4o-audio-model-released)
- [REST API Reference](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/reference-preview-latest)
- No specific "How to use diarization" guide exists

## Investigation Results: Realtime API

### Testing Realtime API Compatibility

We investigated whether the Realtime API supports `gpt-4o-transcribe-diarize` for transcription.

**Finding:** The Realtime API **does NOT support** `gpt-4o-transcribe-diarize` either.

According to the [API Reference (Components)](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/reference-preview#components):

```
input_audio_transcription | object | Configuration of the transcription model
└─ model | enum | The model to use for transcription. Can be `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, or `whisper-1`
   Possible values: `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, `whisper-1`
```

The `gpt-4o-transcribe-diarize` model is **conspicuously absent** from the allowed values.

### Documentation Contradictions

1. **What's New page says:**
   > "Use this model via the `/audio` and `/realtime` APIs."
   
2. **Reality:**
   - `/audio/transcriptions` REST endpoint: Accepts the model but returns only text
   - `/realtime` API: Does NOT accept `gpt-4o-transcribe-diarize` in session configuration

3. **Audio Events Reference:**
   Lists `gpt-4o-transcribe-diarize` under `RealtimeAudioInputTranscriptionModel` allowed values, but the actual API schema contradicts this.

## Questions for Azure Team

1. **Where can `gpt-4o-transcribe-diarize` actually be used?**
   - Not working in `/audio/transcriptions` (no speaker segments)
   - Not accepted in `/realtime` API (not in enum values)
   - Is there a third, undocumented API endpoint?

2. **Is this model fully deployed?**
   - The model deployment works in Azure AI Foundry
   - The API accepts requests without error
   - But diarization data is never returned

3. **What's the correct API endpoint/method?**
   - Should we use a different URL path?
   - Different API version?
   - Different request format?

4. **Response format discrepancy:**
   - What should the response look like when diarization works?
   - Should it be in the main response or a separate field?
   - Are there missing documentation examples?

5. **Is this feature actually released?**
   - October 2025 announcement says "released"
   - But no working implementation found in any API
   - Is this a premature announcement?

6. **Regional or preview limitations?**
   - Is diarization only in specific regions?
   - Requires allowlist access?
   - Still in private preview despite announcement?

## Impact

**Critical for Use Case:** Speaker diarization is essential for:
- Legal deposition transcription (identifying attorney vs. deponent)
- Meeting transcription (identifying different participants)
- Customer service calls (identifying agent vs. customer)
- Interview transcription (identifying interviewer vs. interviewee)

Without speaker labels, the transcription is significantly less useful for these applications.

## Workaround Attempts

None successful. The only option is to use alternative services (e.g., Azure Speech Service with diarization enabled) which defeats the purpose of using the `gpt-4o-transcribe-diarize` model.

## Suggested Actions

1. **Clarify documentation** - Add clear examples showing diarization response format
2. **Update API** - Enable speaker segments in `/audio/transcriptions` endpoint response
3. **Provide migration guide** - If diarization requires Realtime API, document how to migrate
4. **Error messaging** - If feature not available, return clear error message instead of silently omitting data

## Supporting Files

- Full test script: `scripts/test_rest_api.py`
- Sample output: `output/teresa_5min_rest_20251110_151749.json`
- Test audio: `test_audio/teresa_5min.mp3` (legal deposition)

## Contact Information

**Name:** Arturo Quiroga  
**Organization:** Microsoft  
**Use Case:** Legal deposition transcription with speaker identification  
**Urgency:** High - Blocking production deployment

---

## Appendix: Full API Response Debug Output

```
============================================================
REST API Transcription
============================================================
Endpoint: https://aq-ai-foundry-sweden-central.openai.azure.com/
API Version: 2025-04-01-preview
Audio File: test_audio/teresa_5min.mp3
Model: gpt-4o-transcribe-diarize
Language: en
Temperature: 0.0
Response Format: json
Timestamp Granularities: ['word', 'segment']
Chunking Strategy: auto
============================================================

✓ Transcription completed in 90.27 seconds

RAW API RESPONSE:
{"text":"Today is Monday, December 13, 2021. The time is 8.04 a.m. This is the deposition of Teresa Peters..."}

MISSING FIELDS:
- segments (array of speaker-labeled segments)
- words (array of word-level timestamps)
- logprobs (log probabilities despite include=['logprobs'])
```

**Status Code:** 200 OK  
**Response Size:** ~15 KB (text only)  
**Expected Size:** ~50-100 KB (with segments, words, logprobs)
