# Azure Support Ticket: Persistent 500 Errors with gpt-4o-transcribe-diarize Model

## Issue Summary
Experiencing persistent HTTP 500 server errors when calling the `/audio/transcriptions` endpoint with the `gpt-4o-transcribe-diarize` model across multiple Azure regions. The errors occur even with retry logic, increased TPM quotas, and optimized request parameters.

---

## Environment Details

### Affected Resources

**1. Sweden Central Deployment**
- **Resource Group**: AI-FOUNDRY-RG
- **Azure OpenAI Resource**: `aq-ai-foundry-sweden-central`
- **Endpoint**: `https://aq-ai-foundry-sweden-central.openai.azure.com/`
- **Model Deployment**: `gpt-4o-transcribe-diarize`
- **API Version**: `2025-04-01-preview`
- **TPM Quota**: 400,000 TPM

**2. East US 2 Deployment**
- **Resource Group**: aq-aoai-rg
- **Azure OpenAI Resource**: `admin-mi3d1g8d-eastus2`
- **Endpoint**: `https://admin-mi3d1g8d-eastus2.cognitiveservices.azure.com/`
- **Model Deployment**: `gpt-4o-transcribe-diarize`
- **API Version**: `2025-03-01-preview`
- **TPM Quota**: 400,000 TPM

---

## Problem Description

### ⚠️ CONFIRMED AZURE SERVICE OUTAGE - SWEDEN CENTRAL

**Resource Health Status:**
- **Sweden Central**: "Unavailable (Unplanned)" - **Multiple incidents throughout the day**
  - Incident 1: 09:41:25 EST - 10:09:50 EST
  - Incident 2: 10:50:29 EST - 11:09:50 EST  
  - Incident 3: 11:11:23 EST - 11:44:27 EST
  - Incident 4: 13:09:50 EST - **Ongoing**
- **East US 2**: Currently operational (no Resource Health issues)

**Azure Portal Message (Sweden Central):**
> "We are sorry, your Cognitive Services resource is unavailable. We're working to automatically recover your Cognitive Services resource and to determine the source of the problem. No additional action is required from you at this time."

**Resource ID Affected:**
- `/subscriptions/7a28b21e-0d3e-4435-a686-d92889d4ee96/resourcegroups/ai-foundry-rg/providers/microsoft.cognitiveservices/accounts/aq-ai-foundry-sweden-central`

**Pattern Observed:**
- Sweden Central has experienced **4 separate unplanned outages** on November 17, 2025
- Each outage lasts approximately 20-40 minutes
- East US 2 remained stable during this period
- Current outage started at 1:09 PM EST and is ongoing

### Issue Timeline
1. **Morning Instability**: Sweden Central experiencing intermittent outages starting 9:41 AM EST
2. **Switched to East US 2**: Successfully processed 30-minute deposition (6 chunks) around 11:00 AM EST
3. **Partial Success in East US 2**: Processed 4 of 5 chunks for second deposition around 11:30 AM EST
4. **Sweden Central Outage #4**: Current outage started at 1:09 PM EST - ongoing
5. **East US 2 Now Also Failing**: Around 12:00-12:30 PM EST, East US 2 also started returning 500 errors despite no Resource Health incidents
6. **Current State**: 
   - Sweden Central: Confirmed unavailable (Resource Health)
   - East US 2: Returns 500 errors but Resource Health shows healthy

### Error Details

**Error Response:**
```json
{
  "error": {
    "message": "The server had an error processing your request. Sorry about that! You can retry your request, or contact us through an Azure support request at: https://go.microsoft.com/fwlink/?linkid=2213926 if you keep seeing this error. (Please include the request ID c7091aef-2227-478b-923e-912a7614f952 in your email.)",
    "type": "server_error",
    "param": null,
    "code": null
  }
}
```

**Recent Request IDs:**
- `c7091aef-2227-478b-923e-912a7614f952` (East US 2 - Nov 17, ~12:30 PM EST)
- `9f91aa5b-8a2f-497b-a782-32e402263944` (East US 2 - Nov 17, ~12:28 PM EST)
- `c18e4406-7c08-4055-9df3-e63a7e1fab55` (East US 2 - Nov 17, earlier)
- `1e1d784c-7b6c-4da0-aed1-737c160c07c6` (East US 2 - Nov 17, earlier)

---

## Request Configuration

### Working Request Parameters
```python
POST {endpoint}/openai/deployments/gpt-4o-transcribe-diarize/audio/transcriptions?api-version={api_version}

Headers:
  api-key: {api_key}

Form Data:
  file: audio.mp3 (5-minute MP3 segment, ~3-5 MB)
  model: "gpt-4o-transcribe-diarize"
  response_format: "diarized_json"
  chunking_strategy: "auto"
  language: "en"
  temperature: "0"
  timestamp_granularities: "segment"

Timeout: 300 seconds
```

### Audio File Specifications
- **Format**: MP3
- **Chunk Duration**: 5 minutes (300 seconds)
- **File Size**: 3-5 MB per chunk
- **Content**: Legal deposition recordings, clear audio quality
- **Sample Rate**: Standard MP3 encoding

---

## Retry Logic Implemented

```python
MAX_RETRIES = 5-10 attempts
RETRY_DELAY = 45-60 seconds between attempts
TIMEOUT = 300 seconds per request
DELAY_BETWEEN_CHUNKS = 10-15 seconds
```

**Results**: All retry attempts fail with identical 500 errors

---

## What We've Tried

### Troubleshooting Steps Taken:
1. ✅ Reduced chunk size from 10 minutes to 5 minutes
2. ✅ Increased TPM quota to 400,000 in both regions
3. ✅ Implemented aggressive retry logic (5-10 attempts)
4. ✅ Added delays between requests (10-15 seconds)
5. ✅ Verified request parameters match working examples
6. ✅ Tested with different audio chunks (same file that worked previously)
7. ✅ Switched between regions (Sweden Central → East US 2 → back)
8. ✅ Checked Azure Activity Logs (no errors shown, only "Informational" entries)
9. ✅ Verified API key authentication working (no 401/403 errors)
10. ✅ Confirmed deployment exists and is active in both regions

### What Worked Previously (Nov 17, ~10:00-11:30 AM EST):
- Successfully processed 30-minute audio file (6 chunks) in East US 2
- Token usage: 76,988 tokens, 630 segments
- Processing time: ~7.6 minutes for 6 chunks
- Occasional retries succeeded on second attempt

### Current Behavior (Nov 17, ~12:00 PM EST onwards):
- **100% failure rate** for the same audio chunks
- Same request parameters that worked earlier
- Both regions affected simultaneously
- No error patterns or helpful diagnostics in Azure portal

---

## Business Impact

**Use Case**: Legal deposition transcription for litigation
- **Criticality**: High - required for court proceedings
- **Timeline**: Time-sensitive legal deadlines
- **Data**: 2 depositions (~30 min and ~25 min)
- **Status**: 1 complete (Rod Peters), 1 partial (Teresa Peters - missing chunk 4 of 5)

**Cost Impact**:
- Deployed resources in two regions for redundancy
- Increased TPM quotas beyond default
- Unable to utilize provisioned capacity

---

## Questions for Azure Support

1. **Sweden Central Stability**: Why has Sweden Central experienced 4 separate unplanned outages today? Is there a systemic issue?
2. **ETA for Resolution**: When do you expect Sweden Central service to be restored?
3. **East US 2 Mystery**: Why is East US 2 returning 500 errors when Resource Health shows it's healthy?
4. **Request IDs Investigation**: Can you investigate the East US 2 request IDs to determine why they're failing despite healthy status?
5. **Regional Recommendations**: Given Sweden Central's instability today, which region is most reliable for `gpt-4o-transcribe-diarize` in production?
6. **Service SLA**: Does this qualify for SLA credits given multiple outages in Sweden Central?
7. **Root Cause**: What is causing the repeated Sweden Central outages?
8. **Proactive Monitoring**: Why wasn't there notification about these repeated service disruptions?

---

## Expected Behavior

Based on successful processing earlier today:
- 5-minute audio chunks should process in 70-85 seconds
- Occasional 500 errors acceptable if retry succeeds
- Should be able to process 5-6 chunks sequentially with delays between requests

---

## Additional Context

### Related GitHub Issue
- **Issue #43964**: Original issue where we discovered the undocumented `diarized_json` response format
- **Azure Engineer Response**: @AndreeaEpure confirmed `response_format="diarized_json"` is correct approach
- **Repository**: https://github.com/Arturo-Quiroga-MSFT/GPT-4o-Transcribe-Diarize

### Documentation Gaps
This experience has highlighted that the `gpt-4o-transcribe-diarize` model has:
1. Undocumented `diarized_json` response format (critical for speaker identification)
2. Inconsistent regional stability
3. Unclear service health/status visibility
4. Limited diagnostic information in error responses

---

## Requested Actions

1. **Critical**: Provide ETA for service restoration in both regions
2. **Immediate**: Confirm this is a known outage affecting multiple customers
3. **Short-term**: Update Azure Service Health dashboard with outage details and status
4. **Medium-term**: Provide root cause analysis once service is restored
5. **Long-term**: Implement better proactive notification for service disruptions
6. **SLA Review**: Evaluate eligibility for service credits given business-critical impact

## Service Impact Metrics

**Prior to Outage (Working Period: ~10:00 AM - 1:00 PM EST):**
- ✅ Successfully processed 10 chunks (~50 minutes of audio)
- ✅ Processing time: 70-85 seconds per 5-minute chunk
- ✅ Token usage: ~13,000 tokens per chunk
- ✅ Success rate: ~90% (occasional retries needed but succeeded)

**During Outage (After 1:09 PM EST):**
- ❌ Sweden Central: 100% failure rate - Confirmed unavailable by Resource Health
- ❌ East US 2: 100% failure rate with 500 errors - BUT Resource Health shows healthy
- ❌ All retry attempts exhausted (5-10 attempts per chunk)
- ❌ No successful requests for 2+ hours in either region
- ⚠️ **Discrepancy**: East US 2 Resource Health indicates "Available" but API returns 500 errors

---

## Contact Information

**Submitter**: Arturo Quiroga  
**Role**: Senior Partner Solutions Architect, Microsoft America  
**GitHub**: Arturo-Quiroga-MSFT  
**Priority**: High - Business-critical application blocked  

---

## Attachments

Please find attached:
1. Full request/response logs with timestamps
2. Screenshots of Azure portal Activity Logs
3. Python scripts demonstrating the issue
4. Successfully processed output from earlier today (for comparison)

---

**Submission Date**: November 17, 2025  
**Last Updated**: November 17, 2025, 12:30 PM EST
