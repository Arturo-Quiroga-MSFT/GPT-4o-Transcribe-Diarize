# GitHub Issue Response - Documentation Request for `diarized_json`

## Response to @AndreeaEpure on Issue #43964

---

Thank you @AndreeaEpure for providing the solution! The `response_format="diarized_json"` parameter works perfectly. 

### ✅ Verified Working

I've successfully tested with both Python REST API and confirmed:

```python
with audio_path.open("rb") as audio_file:
    create_kwargs = dict(
        model="gpt-4o-transcribe-diarize",
        file=audio_file,
        response_format="diarized_json",  # ✅ WORKS!
        chunking_strategy="auto",
        language="en",
        temperature=0,
    )
```

**Test Results:**
- ✅ 5-minute legal deposition audio processed successfully
- ✅ 4 speakers correctly identified (labeled A, B, C, D)
- ✅ 126 segments with accurate timestamps
- ✅ 13,825 tokens total (4,851 input, 8,959 output)
- ✅ Response includes both full transcript text and speaker-segmented data

### 📋 Response Format

The `diarized_json` format returns:

```json
{
  "text": "Full transcript...",
  "segments": [
    {
      "type": "transcript.text.segment",
      "text": "What the speaker said",
      "speaker": "A",
      "start": 6.07,
      "end": 6.82,
      "id": "seg_1"
    },
    ...
  ],
  "usage": {
    "type": "tokens",
    "total_tokens": 13825,
    "input_tokens": 4851,
    "output_tokens": 8959
  }
}
```

### 📚 Documentation Needs

However, **`diarized_json` is completely undocumented**. Could you please help ensure this gets added to:

#### 1. API Reference Documentation
- **Location**: [Azure OpenAI Audio Transcriptions API Reference](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/reference-preview)
- **Needed**: Add `diarized_json` to the `response_format` enum
- **Current issue**: Only lists `json`, `text`, `srt`, `vtt`, `verbose_json`

#### 2. Response Schema Documentation
- **Needed**: Document the segment structure returned by `diarized_json`:
  ```typescript
  {
    type: "transcript.text.segment",
    text: string,
    speaker: string,  // e.g., "A", "B", "C", "D"
    start: number,    // seconds
    end: number,      // seconds
    id: string        // e.g., "seg_1"
  }
  ```

#### 3. What's New Page
- **Location**: [What's New - GPT-4o Audio Model Released](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/whats-new#gpt-4o-audio-model-released)
- **Current text**: "Use this model via the `/audio` and `/realtime` APIs."
- **Needed**: Add working code example showing `diarized_json` usage

#### 4. Code Examples
Add examples in official documentation for:
- Python (REST API and SDK)
- .NET
- JavaScript/TypeScript
- Azure CLI

Example for Python:
```python
import os
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2025-04-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

with open("audio.mp3", "rb") as audio_file:
    transcription = client.audio.transcriptions.create(
        model="gpt-4o-transcribe-diarize",
        file=audio_file,
        response_format="diarized_json",  # Required for speaker diarization
        chunking_strategy="auto",
        language="en"
    )

# Access speaker-segmented transcript
for segment in transcription.segments:
    print(f"[{segment.start:.2f}s - {segment.end:.2f}s] Speaker {segment.speaker}:")
    print(f"  {segment.text}")
```

#### 5. Model Limitations
- **Needed**: Document the 25-minute (1500 second) limit per audio file
- **Needed**: Provide guidance on handling longer audio files (chunking strategies)

#### 6. Important Notes to Add

**Note about `chunking_strategy`:**
- Required parameter: `chunking_strategy="auto"` or `"server_vad"`
- Using `"auto"` is recommended (not well documented currently)

**Note about `verbose_json`:**
- Clarify that `verbose_json` is NOT compatible with diarization models
- Error message: `"response_format 'verbose_json' is not compatible with model 'gpt-4o-transcribe-diarize'"`

**Note about Realtime API:**
- Clarify that `gpt-4o-transcribe-diarize` is NOT available in the Realtime API
- Only available via `/audio/transcriptions` endpoint

### 🎯 Impact

This feature is critical for:
- ✅ Legal depositions (attorney vs. deponent identification)
- ✅ Meeting transcriptions (multiple participants)
- ✅ Customer service calls (agent vs. customer)
- ✅ Interviews and podcasts
- ✅ Any multi-speaker audio analysis

The feature works excellently, but without documentation, users cannot discover or use it properly.

### 🙏 Request

Could you:
1. Confirm this will be added to official documentation
2. Provide an estimated timeline for documentation updates
3. Let us know if there are any other undocumented parameters or features we should be aware of

Thank you again for the solution! This unblocks our production use case.

---

**Testing Environment:**
- Region: Sweden Central
- API Version: `2025-04-01-preview`
- Model: `gpt-4o-transcribe-diarize`
- Authentication: Microsoft Entra ID
- Audio format: MP3, mono/stereo, various bitrates tested
