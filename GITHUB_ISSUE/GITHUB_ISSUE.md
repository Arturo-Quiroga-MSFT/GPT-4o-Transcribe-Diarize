# gpt-4o-transcribe-diarize model not returning speaker diarization segments

## Description

The `gpt-4o-transcribe-diarize` model successfully transcribes audio but **does not return speaker diarization data**. The API only returns `{"text": "..."}` without the expected `segments` array containing speaker labels.

## Environment

- **Endpoint:** Sweden Central
- **API Version:** `2025-04-01-preview`
- **Model:** `gpt-4o-transcribe-diarize`
- **Client:** REST API (`/audio/transcriptions`)

## Expected vs. Actual

### Expected Response
```json
{
  "text": "Full transcription...",
  "segments": [
    {"speaker": "Speaker 1", "text": "...", "start": 0.0, "end": 5.2},
    {"speaker": "Speaker 2", "text": "...", "start": 5.3, "end": 8.7}
  ]
}
```

### Actual Response
```json
{
  "text": "Full transcription..."
}
```

## Reproduction

```python
import requests

url = "https://{endpoint}.openai.azure.com/openai/deployments/gpt-4o-transcribe-diarize/audio/transcriptions?api-version=2025-04-01-preview"
headers = {"api-key": api_key}

with open("audio.mp3", "rb") as f:
    response = requests.post(
        url,
        headers=headers,
        files={"file": ("audio.mp3", f, "audio/mpeg")},
        data={
            "model": "gpt-4o-transcribe-diarize",
            "language": "en",
            "response_format": "json",
            "timestamp_granularities": '["word", "segment"]'
        }
    )

print(response.json())
# Output: {"text": "..."}  <-- Missing segments!
```

## Testing Results

- ✅ Transcription works correctly
- ❌ No speaker segments returned
- ❌ `verbose_json` explicitly rejected: `"response_format 'verbose_json' is not compatible with model 'gpt-4o-transcribe-diarize'"`
- ❌ All parameter combinations tried (timestamp_granularities, chunking_strategy, include) - no segments

## Investigation Results

### Realtime API Compatibility
**The Realtime API does NOT support `gpt-4o-transcribe-diarize` either.**

According to the [API reference](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/reference-preview#components), the Realtime API's `input_audio_transcription.model` field only accepts:
- `gpt-4o-transcribe`
- `gpt-4o-mini-transcribe`
- `whisper-1`

The `gpt-4o-transcribe-diarize` model is **not listed** as a valid option for Realtime API transcription.

### Documentation Contradiction

The [What's New](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/whats-new#gpt-4o-audio-model-released) page states:

> "Use this model via the `/audio` and `/realtime` APIs."

However:
- **`/audio/transcriptions` endpoint**: Only returns `{"text": "..."}` without speaker segments
- **`/realtime` API**: Does not accept `gpt-4o-transcribe-diarize` in `input_audio_transcription.model`

## Questions

1. **Where can `gpt-4o-transcribe-diarize` actually be used?** Neither `/audio` nor `/realtime` APIs appear to support it properly.
2. What is the correct API endpoint/method to access diarization features?
3. Is the diarization feature deployed but undocumented?
4. Is there a different API version that supports this model?

## Impact

**Blocking production use** - Speaker identification is critical for:
- Legal depositions (attorney vs. deponent)
- Meeting transcriptions (multiple participants)
- Customer service calls (agent vs. customer)

## Documentation

The [What's New](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/whats-new#gpt-4o-audio-model-released) page states:

> "The `gpt-4o-transcribe-diarize` speech to text model is released... Diarization is the process of identifying who spoke when in an audio stream."

However, no documentation shows:
- Response format with speaker segments
- Code examples using diarization
- How to access speaker labels

## Request

Please either:
1. **Fix the API** to return speaker segments as documented
2. **Update documentation** to clarify if/how diarization works
3. **Provide clear error** if feature not available rather than silently omitting data

---

**Related Repositories:**
- Azure OpenAI Python SDK
- Azure AI Foundry documentation

**Use Case:** Legal transcription requiring speaker identification
