# SOLUTION FOUND: Undocumented `diarized_json` Response Format

## Summary

Azure support engineer [@AndreeaEpure](https://github.com/AndreeaEpure) provided the solution on GitHub issue [#43964](https://github.com/Azure/azure-sdk-for-python/issues/43964):

**Use `response_format="diarized_json"` instead of `"json"`**

This is an **undocumented response format** specifically for the `gpt-4o-transcribe-diarize` model.

## Working Example

```python
with audio_path.open("rb") as audio_file:
    create_kwargs = dict(
        model="gpt-4o-transcribe-diarize",
        file=audio_file,
        response_format="diarized_json",  # KEY PARAMETER
        chunking_strategy="auto",
        language="en",
        temperature=0,
    )
```

## Response Format

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
    "total_tokens": 13810,
    "input_tokens": 4851,
    "output_tokens": 8959
  }
}
```

### Segment Fields

- `type`: Always "transcript.text.segment"
- `text`: The spoken text for this segment
- `speaker`: Speaker label (A, B, C, D, etc.)
- `start`: Start time in seconds (float)
- `end`: End time in seconds (float)
- `id`: Unique segment identifier (seg_1, seg_2, etc.)

## Testing Results

✅ **VERIFIED WORKING** - Tested on 5-minute legal deposition audio:

- **Speakers Detected**: 4 speakers (A, B, C, D)
- **Segments**: 126 segments with accurate timestamps
- **Accuracy**: Correctly identified attorney (A), deponent (D), court reporter (B), and clerk (C)
- **Timestamps**: Precise to hundredths of seconds
- **Token Usage**: 13,810 total tokens (4,851 input, 8,959 output)

## Updated REST API Command

```bash
python scripts/test_rest_api.py \
  --audio test_audio/teresa_5min.mp3 \
  --response-format diarized_json \
  --chunking-strategy server_vad
```

## Documentation Issues

### What's Missing

1. **`diarized_json` is not documented** anywhere in:
   - [Audio API Reference](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/reference-preview)
   - [What's New page](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/whats-new#gpt-4o-audio-model-released)
   - Model quickstarts or guides

2. **Response format options** only list:
   - `json`
   - `text`
   - `srt`
   - `vtt`
   - `verbose_json` (explicitly rejected for diarization models)

3. **No code examples** showing diarization usage

### What Should Be Added

1. Add `diarized_json` to response format enum in API specs
2. Document the segment structure with speaker labels
3. Provide code examples in Python, .NET, JavaScript
4. Update "What's New" with actual working examples
5. Add to quickstart/tutorial documentation

## Use Cases Now Unblocked

✅ Legal depositions with speaker identification  
✅ Meeting transcriptions with multiple participants  
✅ Customer service call analysis (agent vs. customer)  
✅ Interview transcriptions  
✅ Podcast/video content with multiple speakers  

## Requirements

- **Model**: `gpt-4o-transcribe-diarize`
- **API Version**: `2025-04-01-preview` (or later)
- **Response Format**: `diarized_json` (required for diarization)
- **Chunking Strategy**: `auto` or `server_vad` (recommended)
- **Region**: Sweden Central (or other supported regions)

## Next Steps

1. ✅ Test and verify solution works
2. ⏳ Update GitHub issues with solution
3. ⏳ Request documentation updates from Microsoft
4. ⏳ Close Azure Support ticket with solution
5. ⏳ Implement in production code

## Credits

Solution discovered by Azure support engineer [@AndreeaEpure](https://github.com/AndreeaEpure) on November 17, 2025.

## Related Issues

- [Azure/azure-sdk-for-python #43964](https://github.com/Azure/azure-sdk-for-python/issues/43964)
- [Azure-Samples/openai #177](https://github.com/Azure-Samples/openai/issues/177)
- [Azure/azure-rest-api-specs #38741](https://github.com/Azure/azure-rest-api-specs/issues/38741)
