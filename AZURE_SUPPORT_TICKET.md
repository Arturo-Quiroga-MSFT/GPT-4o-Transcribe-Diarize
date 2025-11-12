# Azure Support Ticket: gpt-4o-transcribe-diarize Not Returning Speaker Diarization Data

---

## Quick Summary for Support Portal Form:

**Issue Title:**
```
gpt-4o-transcribe-diarize model returns only text without speaker diarization segments
```

**Problem Type:** Technical Issue

**Service:** Azure AI Foundry / Azure OpenAI Service

**Problem Category:** Audio/Speech Services

**Severity:** B - Moderate Business Impact (or C - Minimal Impact, depending on your needs)

**Short Description (for summary field):**
```
The gpt-4o-transcribe-diarize model successfully transcribes audio but does not return speaker diarization data (speaker segments/labels) as documented. API returns only {"text": "..."} without the expected segments array containing speaker attribution. Tested both /audio/transcriptions REST API and verified Realtime API doesn't support the model. Documentation claims feature is released and available, but implementation doesn't match.
```

---

## Detailed Description for Ticket Body:

### Issue Summary

The `gpt-4o-transcribe-diarize` model, announced as released in October 2025, does not return speaker diarization data despite documentation stating it does. The API successfully transcribes audio but returns only a plain text field without speaker segments or labels.

### Environment Details

- **Azure Subscription ID:** [YOUR_SUBSCRIPTION_ID]
- **Resource Name:** aq-ai-foundry-sweden-central
- **Resource Group:** [YOUR_RESOURCE_GROUP]
- **Region:** Sweden Central
- **Deployment Name:** gpt-4o-transcribe-diarize
- **API Version:** 2025-04-01-preview
- **Model Version:** Latest available
- **Client Type:** REST API (Python requests library)
- **Authentication:** API Key (also tested with Microsoft Entra ID)

### Expected Behavior

According to the [What's New documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/whats-new#gpt-4o-audio-model-released):

> "The gpt-4o-transcribe-diarize speech to text model is released. This is an Automatic Speech Recognition (ASR) model... Diarization is the process of identifying who spoke when in an audio stream. It transforms conversations into speaker-attributed transcripts... Use this model via the /audio and /realtime APIs."

**Expected API Response:**
```json
{
  "text": "Full transcription of the audio...",
  "segments": [
    {
      "speaker": "Speaker 1",
      "text": "Opening statement from first speaker...",
      "start": 0.0,
      "end": 5.2
    },
    {
      "speaker": "Speaker 2",
      "text": "Response from second speaker...",
      "start": 5.3,
      "end": 8.7
    }
  ]
}
```

### Actual Behavior

**Actual API Response:**
```json
{
  "text": "Full transcription of the audio with all speakers combined without any speaker identification or segmentation."
}
```

The API returns only a `text` field. No `segments` array, no speaker labels, no speaker attribution whatsoever.

### Reproduction Steps

#### 1. Test Audio
- Type: Legal deposition recording with multiple distinct speakers
- Format: MP3
- Duration: ~5 minutes
- Content: Clear conversation with attorney and deponent (2+ speakers)

#### 2. API Request

**Endpoint:**
```
POST https://aq-ai-foundry-sweden-central.openai.azure.com/openai/deployments/gpt-4o-transcribe-diarize/audio/transcriptions?api-version=2025-04-01-preview
```

**Headers:**
```
api-key: [REDACTED]
Content-Type: multipart/form-data
```

**Form Data:**
```
file: [audio_file.mp3]
model: gpt-4o-transcribe-diarize
language: en
temperature: 0.0
response_format: json
timestamp_granularities: ["word", "segment"]
chunking_strategy: {"type": "auto"}
include: ["logprobs"]
```

#### 3. Python Reproduction Code

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

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")

# Output:
# Status Code: 200
# Response: {"text": "Today is Monday, December 13, 2021..."}
# Missing: segments field with speaker labels
```

### Testing Performed

#### Test 1: Response Format Variations
- ✅ `response_format: json` - Returns 200 OK, but only text field
- ✅ `response_format: text` - Returns plain text, no structure
- ❌ `response_format: verbose_json` - Explicitly rejected with error:
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

#### Test 2: Parameter Combinations
All return only the `text` field without segments:
- With `timestamp_granularities: ["word", "segment"]`
- With `chunking_strategy: "auto"` and `"server_vad"`
- With `include: ["logprobs"]`
- With and without `word-timestamps` flag
- Various temperature values (0.0, 0.5, 1.0)
- Different languages (en, en-US)

#### Test 3: Authentication Methods
- API Key authentication: Same result
- Microsoft Entra ID authentication: Same result

#### Test 4: Realtime API Compatibility
Investigated whether Realtime API supports the model differently.

**Finding:** The [Realtime API Reference](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/reference-preview#components) shows `input_audio_transcription.model` only accepts:
- `gpt-4o-transcribe`
- `gpt-4o-mini-transcribe`
- `whisper-1`

The `gpt-4o-transcribe-diarize` model is **not listed** as a valid option for Realtime API.

### Documentation Contradictions

1. **What's New Page Claims:**
   - "The gpt-4o-transcribe-diarize model is released"
   - "Use this model via the /audio and /realtime APIs"

2. **Reality:**
   - `/audio/transcriptions` API: Accepts model but returns no diarization data
   - `/realtime` API: Does not accept model in session configuration enum
   - No documentation shows response structure with speaker segments
   - No code samples demonstrate accessing diarization output
   - No examples of expected JSON structure

### Business Impact

**Severity: Moderate to High**

This issue is blocking production deployment for:
- Legal deposition transcription (requiring speaker identification: attorney vs. deponent)
- Meeting transcription with multiple participants
- Customer service call analysis (agent vs. customer identification)
- Interview transcription with interviewer/interviewee attribution

Without speaker diarization, the transcripts are significantly less useful and require manual post-processing to identify speakers, defeating the purpose of using this specialized model.

### Additional Context

**GitHub Issues Created:**
- Azure-Samples/openai: https://github.com/Azure-Samples/openai/issues/177
- Azure/azure-sdk-for-python: https://github.com/Azure/azure-sdk-for-python/issues/43964
- Azure/azure-rest-api-specs: https://github.com/Azure/azure-rest-api-specs/issues/38741

**Supporting Files Available:**
- Full test scripts with reproduction code
- Sample output JSON files
- Raw API response debug output
- Comprehensive testing documentation

### Questions for Support Team

1. **Is the diarization feature actually deployed?**
   - Model deployment works in Azure AI Foundry
   - API accepts requests without error (200 OK)
   - But diarization data is never returned

2. **What is the correct API endpoint?**
   - Is there a different URL path we should use?
   - Different API version required?
   - Different request format needed?

3. **Where can this model be used?**
   - Documentation says `/audio` and `/realtime` APIs
   - `/audio/transcriptions` doesn't return segments
   - `/realtime` doesn't accept the model
   - Is there a third endpoint?

4. **What should the response format be?**
   - No documentation shows speaker segment structure
   - Is `segments` the correct field name?
   - Should it be nested differently?
   - Are there examples we can reference?

5. **Regional or access restrictions?**
   - Is diarization only available in specific regions?
   - Does it require allowlist access?
   - Is it still in private preview despite announcement?

6. **Timeline for resolution?**
   - When will this feature work as documented?
   - Should we use an alternative service in the meantime?
   - Will there be a migration path once it's fixed?

### Requested Actions

Please either:
1. **Enable the diarization feature** to return speaker segments as documented
2. **Provide correct documentation** showing how to access diarization if it exists
3. **Update the documentation** to accurately reflect current capabilities
4. **Provide workaround guidance** if feature is not yet available
5. **Clarify release status** if this was a premature announcement

### Customer Information

- **Name:** Arturo Quiroga
- **Organization:** Microsoft
- **Email:** [YOUR_EMAIL]
- **Phone:** [YOUR_PHONE]
- **Use Case:** Legal transcription requiring speaker identification
- **Urgency:** High - Blocking production deployment
- **Preferred Contact Method:** Email / Teams

### Attachments to Include

1. **Test Script:** Python script demonstrating the issue
2. **Sample Output:** JSON file showing response without segments
3. **API Debug Logs:** Raw HTTP request/response details
4. **Audio Sample:** (Optional) Small test audio file if needed for reproduction

---

## For Support Portal Upload:

**Suggested Attachments:**
1. `scripts/test_rest_api.py` - Full reproduction script
2. `output/teresa_5min_rest_20251110_151749.json` - Sample output file
3. `ISSUE_REPORT.md` - Comprehensive technical documentation
4. Test audio file (if support requests it)

**Tracking:**
- Support Ticket ID: [Will be provided by Azure Support]
- Created Date: November 12, 2025
- Expected Response Time: Within 24-48 hours (depending on severity level)

---

## Post-Submission Checklist

After submitting the ticket:
- [ ] Save the ticket ID/reference number
- [ ] Monitor email for support responses
- [ ] Be prepared to provide additional information if requested
- [ ] Have test environment ready for support team to replicate
- [ ] Keep GitHub issues updated with support ticket progress
- [ ] Escalate internally if no response within SLA timeframe

---

**End of Support Ticket Content**
