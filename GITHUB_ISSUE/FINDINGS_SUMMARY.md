# Investigation Summary: gpt-4o-transcribe-diarize Diarization Issue

**Date:** November 10, 2025  
**Status:** ❌ **Diarization NOT Working** - Documentation vs Reality Gap

---

## TL;DR

The `gpt-4o-transcribe-diarize` model **does not return speaker diarization data** through any documented API endpoint, despite official documentation claiming it does. This appears to be a significant gap between documentation and actual implementation.

---

## What We Tested

### 1. `/audio/transcriptions` REST API ❌
- **Status:** Accepts model, transcribes successfully
- **Problem:** Only returns `{"text": "..."}` without speaker segments
- **Tested:** Multiple parameter combinations, all response formats
- **Result:** No diarization data ever returned

### 2. Realtime API (`/realtime`) ❌  
- **Status:** Does NOT support `gpt-4o-transcribe-diarize`
- **Problem:** API schema only allows: `whisper-1`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`
- **Documentation says:** "Use this model via `/audio` and `/realtime` APIs"
- **Reality:** Model not accepted in Realtime API session configuration

---

## Key Findings

### ✅ What Works
- Model deployment in Azure AI Foundry
- API authentication (both API key and Entra ID)
- Audio transcription (text output is accurate)
- All HTTP requests return 200 OK

### ❌ What Doesn't Work
- **Speaker diarization** - No speaker labels returned
- **Speaker segments** - No segmentation by speaker
- **Realtime API** - Doesn't accept the diarize model
- **Response format** - No documented structure for diarization output

---

## Documentation Contradictions

### Official Documentation Claims:
> "The `gpt-4o-transcribe-diarize` speech to text model is released... Diarization is the process of identifying who spoke when in an audio stream... Use this model via the `/audio` and `/realtime` APIs."
>
> Source: [What's New - October 2025](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/whats-new#gpt-4o-audio-model-released)

### Reality Check:

| API Endpoint | Documentation | Actual Behavior |
|--------------|---------------|-----------------|
| `/audio/transcriptions` | ✅ Supported | ❌ No diarization data returned |
| `/realtime` | ✅ Supported | ❌ Model not in allowed enum values |
| Response Format | ? Undocumented | Only returns `text` field |
| Speaker Segments | ? Undocumented | Never appears in response |

---

## Technical Details

### Expected Response
```json
{
  "text": "Full transcript...",
  "segments": [
    {
      "speaker": "Speaker 1",
      "text": "Opening statement...",
      "start": 0.0,
      "end": 5.2
    },
    {
      "speaker": "Speaker 2",
      "text": "Response...",
      "start": 5.3,
      "end": 8.7
    }
  ]
}
```

### Actual Response
```json
{
  "text": "Full transcript with all speakers combined..."
}
```

### API Configuration Tested
```python
endpoint = "https://{resource}.openai.azure.com/openai/deployments/gpt-4o-transcribe-diarize/audio/transcriptions"
params = {
    "api-version": "2025-04-01-preview",
    "model": "gpt-4o-transcribe-diarize",
    "language": "en",
    "response_format": "json",  # Also tried: text, verbose_json (rejected)
    "timestamp_granularities": ["word", "segment"],
    "chunking_strategy": "auto",
    "include": ["logprobs"]
}
```

**Result:** 200 OK, but only `text` field returned.

---

## Possible Explanations

### 1. **Feature Not Yet Implemented** 🤔
- Announcement was premature
- Backend not deployed despite documentation

### 2. **Missing Documentation** 📚
- Different API endpoint exists but undocumented
- Required parameters not documented
- Response parsing method not documented

### 3. **Regional/Access Restrictions** 🌍
- Feature only in certain regions
- Requires allowlist/private preview access
- Not available despite public announcement

### 4. **Different Use Case** 🎯
- Model is for Realtime API WebSocket streaming only
- Batch transcription not supported
- Documentation incorrectly references `/audio` API

---

## What This Means for Users

### ❌ Currently Blocked:
- Cannot get speaker-labeled transcripts
- Cannot identify who spoke when
- Cannot use for legal depositions (original use case)
- Cannot use for meeting transcription with speaker attribution
- Must use alternative services (e.g., Azure Speech Service)

### ✅ Workarounds:
1. **Azure Speech Service** - Has working diarization via SDK
2. **Third-party services** - AssemblyAI, Rev.ai, etc.
3. **Post-processing** - Use separate speaker identification service

---

## Next Steps

### Recommended Actions:
1. **Azure Support Ticket** - Submit `ISSUE_REPORT.md` via Azure Portal
2. **GitHub Issue** - File issue using `GITHUB_ISSUE.md` on Azure-Samples/openai
3. **Microsoft Docs Feedback** - Report documentation gap on What's New page
4. **Alternative Solution** - Evaluate Azure Speech Service for diarization

### Questions to Ask Azure:
1. Where can `gpt-4o-transcribe-diarize` actually be used?
2. Is diarization feature actually deployed?
3. What's the correct API endpoint for diarization?
4. When will this be fixed/documented?
5. Is there a preview/beta access program?

---

## Test Environment

- **Region:** Sweden Central
- **API Version:** 2025-04-01-preview
- **Model:** gpt-4o-transcribe-diarize (successfully deployed)
- **Audio:** Legal deposition MP3, ~5 minutes, multiple speakers
- **Client:** Python requests library + REST API
- **Authentication:** Both API key and Entra ID tested

---

## Files in This Repository

- `ISSUE_REPORT.md` - Comprehensive technical report for Azure Support
- `GITHUB_ISSUE.md` - Concise GitHub issue template
- `FINDINGS_SUMMARY.md` - This summary document
- `scripts/test_rest_api.py` - Test script with full reproduction code
- `output/teresa_5min_rest_*.json` - Sample output showing missing segments

---

## Conclusion

The `gpt-4o-transcribe-diarize` model appears to be **announced but not functionally available**. The documentation claims it works via `/audio` and `/realtime` APIs, but:

- `/audio/transcriptions` returns no diarization data
- `/realtime` API doesn't accept the model

This is a significant blocker for users requiring speaker identification in transcripts. **Immediate action needed from Azure team** to either:
1. Enable the feature as documented, or
2. Update documentation to reflect actual capabilities

---

**Impact:** HIGH - Core feature not working as documented  
**Priority:** URGENT - Blocking production deployments  
**Audience:** Legal transcription, meeting transcription, customer service analytics
