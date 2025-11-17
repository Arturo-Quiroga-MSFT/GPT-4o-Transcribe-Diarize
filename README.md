# Azure OpenAI GPT-4o-Transcribe-Diarize Testing Suite

This repository contains comprehensive test scripts for the Azure OpenAI `gpt-4o-transcribe-diarize` model, specifically designed for litigation deposition audio file analysis.

## Author

**Arturo Quiroga**  
Senior Partner Solutions Architect  
Enterprise Partner Solutions - Microsoft America

This test suite provides enterprise-grade tools for evaluating and implementing the gpt-4o-transcribe-diarize model in legal and professional audio transcription workflows.

## Model Overview

The `gpt-4o-transcribe-diarize` model is an Automatic Speech Recognition (ASR) model that:
- Converts spoken language into text
- **Identifies who spoke when** (diarization) - critical for legal proceedings
- Supports 100+ languages
- Provides high accuracy transcription with speaker identification
- Available via `/audio/transcriptions` REST API endpoint

### Important Discovery: `diarized_json` Response Format

**The key to enabling speaker diarization is using the undocumented `diarized_json` response format.**

While the official Azure OpenAI documentation lists `json`, `text`, `srt`, `vtt`, and `verbose_json` as available response formats, **only `diarized_json` returns speaker identification**. This was discovered through direct communication with Azure support engineering.

```python
response_format="diarized_json"  # Required for speaker diarization
```

**Without this specific format, you will only receive the full text without speaker labels.**

## Key Features for Legal Use

### Diarization
The model automatically identifies different speakers and attributes text to each speaker, transforming conversations into speaker-attributed transcripts. This is essential for:
- Depositions with multiple parties
- Witness testimonies
- Multi-party meetings
- Interview recordings

### Transcription Quality Controls
- **Language specification**: Improves accuracy and latency
- **Prompt guidance**: Free-text instructions for context (e.g., "expect legal terminology")
- **Temperature control**: Adjust randomness (0-1 range)
- **Log probabilities**: Understand model confidence in transcription
- **Timestamp granularities**: Word-level and segment-level timing

### Response Format for Diarization

⚠️ **CRITICAL DISCOVERY**: To get speaker diarization, you **must** use:

```python
response_format="diarized_json"
```

**This format is undocumented** but is the only way to receive speaker identification. Standard formats (`json`, `text`, `verbose_json`) return only the transcript text without speaker labels.

### Additional Parameters

- **`timestamp_granularities`**: Use `["segment"]` to get detailed timing for each speaker segment
- **`language`**: Specify `"en"` for English to improve accuracy
- **`temperature`**: Use `"0"` (as string) for deterministic output
- **`chunking_strategy`**: Use `"auto"` for automatic voice activity detection

## Repository Structure

```
GPT-4o-Transcribe-Diarize/
├── README.md                           # This file
├── SOLUTION_FOUND.md                   # Documentation of diarized_json discovery
├── GITHUB_RESPONSE.md                  # Comprehensive response for Azure documentation
├── requirements.txt                    # Python dependencies
├── .env.eastus2                        # East US 2 deployment credentials
├── depositions/                        # Legal deposition audio files
│   ├── Peters, Rod 12132021/          # ~30 minute deposition
│   └── Peters, Teresa 12132021/       # ~25 minute deposition
├── output/
│   └── depositions_eastus2/           # Production transcription results
│       ├── Rod Peters mp3.json        # Complete: 6 chunks, 630 segments, 76,988 tokens
│       └── Teresa Peters mp3.json     # Partial: 4/5 chunks (chunk 4 failed)
├── scripts/
│   ├── test_rest_api.py               # REST API with diarized_json support
│   ├── test_rest_api_entra.py         # Entra ID authentication version
│   ├── test_sdk.py                    # Python SDK tests
│   ├── test_eastus2.py                # East US 2 deployment validation
│   ├── process_depositions_eastus2.py # Production processing script (5-min chunks)
│   ├── retry_teresa_chunks.py         # Retry failed chunks
│   ├── retry_chunk4_only.py           # Aggressive retry for stubborn chunk
│   └── generate_text_outputs.py       # Convert JSON to readable text
└── test_audio/                        # Test audio samples
```

## Setup

### Prerequisites
- Python 3.8+
- Azure OpenAI resource with `gpt-4o-transcribe-diarize` model deployed
- API key or Microsoft Entra ID credentials

### Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd GPT-4o-Transcribe-Diarize
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp config/.env.example .env
# Edit .env with your Azure OpenAI credentials
```

Required environment variables:
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint (e.g., https://your-resource.openai.azure.com/)
- `AZURE_OPENAI_API_KEY`: Your API key (or use Entra ID authentication)
- `AZURE_OPENAI_API_VERSION`: API version (default: 2025-04-01-preview)
- `MODEL_DEPLOYMENT_NAME`: Deployment name (default: gpt-4o-transcribe-diarize)

## Test Scripts

### 1. SDK-Based Test (`test_sdk.py`)
Uses the official `openai` Python package for simplified API interaction.

**Features:**
- Basic transcription with diarization
- Language specification
- Response format options (JSON, text, SRT, VTT)
- Timestamp granularities (word, segment)

**Usage:**
```bash
python scripts/test_sdk.py --audio test_audio/deposition.wav --language en
```

### 2. REST API Test (`test_rest_api.py`)
Direct HTTP calls to test all API parameters comprehensively.

**Features:**
- Full parameter control
- Chunking strategy configuration
- Temperature and sampling control
- Log probabilities retrieval
- Streaming support

**Usage:**
```bash
python scripts/test_rest_api.py --audio test_audio/deposition.wav --chunking-strategy server_vad
```

### 3. Parameter Testing Suite (`test_parameters.py`)
Systematic testing of parameter combinations for optimal settings discovery.

**Features:**
- Tests multiple temperature values
- Tests different chunking strategies
- Tests various prompt instructions
- Generates comparison reports
- Performance metrics (latency, accuracy indicators)

**Usage:**
```bash
python scripts/test_parameters.py --audio test_audio/deposition.wav --test-all
```

## API Parameters Reference

### Core Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `file` | binary | Audio file (required) | - |
| `model` | string | Model name: `gpt-4o-transcribe-diarize` | - |
| `chunking_strategy` | object | **REQUIRED**: VAD configuration (see below) | **REQUIRED** |
| `language` | string | ISO-639-1 code (e.g., `en`) | Auto-detect |
| `prompt` | string | Free-text guidance (not supported for diarization models) | - |
| `response_format` | object | Output format: `json`, `text`, `srt`, `vtt` (NOT `verbose_json`) | json |
| `temperature` | float | Sampling temperature (0-1) | 0 |
| `timestamp_granularities` | array | `['word']` and/or `['segment']` | ['segment'] |
| `stream` | boolean | Enable streaming response | false |

### Advanced Parameters

#### Chunking Strategy (VAD) - REQUIRED
⚠️ **This parameter is mandatory for `gpt-4o-transcribe-diarize`:**
```json
{
  "chunking_strategy": {
    "type": "server_vad",
    "prefix_padding_ms": 300,
    "silence_duration_ms": 200,
    "threshold": 0.5
  }
}
```

#### Include Options
- `logprobs`: Returns confidence scores (only with `response_format: json`)

### Response Format with `diarized_json`

When using `response_format="diarized_json"`, the response structure includes speaker identification:

```json
{
  "text": "Full transcript with all speakers combined",
  "segments": [
    {
      "type": "transcript.text.segment",
      "text": " This is the attorney speaking.",
      "speaker": "A",
      "start": 0.0,
      "end": 5.2,
      "id": "seg_0"
    },
    {
      "type": "transcript.text.segment",
      "text": " This is the witness responding.",
      "speaker": "B",
      "start": 5.5,
      "end": 12.8,
      "id": "seg_1"
    }
  ],
  "usage": {
    "prompt_tokens": 1234,
    "prompt_tokens_details": {
      "audio_tokens": 1200,
      "text_tokens": 34
    },
    "completion_tokens": 5678,
    "total_tokens": 6912
  }
}
```

**Key differences from standard formats:**
- Speakers are labeled alphabetically: `"A"`, `"B"`, `"C"`, etc.
- Each segment includes precise timestamps (start/end in seconds)
- Includes token usage details for cost tracking
- Text segments are precise with speaker attribution

## Best Practices for Legal Depositions

### ⚠️ Critical Requirements

1. **Use `response_format="diarized_json"`** - This is the ONLY way to get speaker diarization
2. **Chunk audio into 5-minute segments** - More reliable than larger chunks, reduces 500 errors
3. **Implement retry logic** - Azure OpenAI can experience intermittent 500 errors
4. **Add delays between requests** - 10-15 second delays prevent rate limiting
5. **Specify language** - Always include `language="en"` for better accuracy

### 1. Audio Chunking Strategy

For audio longer than 5 minutes, split into chunks:

```python
# Using ffmpeg to split into 5-minute (300 second) chunks
import subprocess

def split_audio(input_file, chunk_duration=300):
    """Split audio into chunks of specified duration"""
    subprocess.run([
        'ffmpeg', '-i', input_file,
        '-f', 'segment',
        '-segment_time', str(chunk_duration),
        '-c', 'copy',
        f'{input_file}_chunk%02d.mp3'
    ])
```

**Why 5 minutes?**
- API limit: 25 minutes (1500 seconds) maximum
- Reliability: Shorter chunks have lower failure rates
- Error recovery: Easier to retry individual failed chunks

### 2. Retry Logic Implementation

```python
MAX_RETRIES = 3
RETRY_DELAY = 30  # seconds

def transcribe_with_retry(audio_file, attempt=1):
    try:
        response = requests.post(url, headers=headers, files=files, data=data, timeout=300)
        if response.status_code == 500 and attempt < MAX_RETRIES:
            print(f"⚠ Server error (attempt {attempt}/{MAX_RETRIES}), retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
            return transcribe_with_retry(audio_file, attempt + 1)
        return response
    except Exception as e:
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
            return transcribe_with_retry(audio_file, attempt + 1)
        raise
```

### 3. Request Parameters

**Working configuration:**
```python
data = {
    'model': 'gpt-4o-transcribe-diarize',  # Exact model name
    'response_format': 'diarized_json',     # Required for diarization
    'chunking_strategy': 'auto',            # Auto voice detection
    'language': 'en',                       # Specify language
    'temperature': '0',                     # Deterministic output
    'timestamp_granularities': 'segment'    # Get timing info
}
```

### 4. Regional Considerations

**Observed stability differences:**
- **East US 2**: More stable, occasional retries succeed
- **Sweden Central**: Frequent 500 errors even with increased TPM quotas

**Recommendation:** Deploy to East US 2 for production workloads involving legal depositions.

### 5. Audio Quality
- Use high-quality recordings (minimum 16kHz sampling rate)
- MP3, WAV, FLAC formats supported
- Minimize background noise
- Ensure clear speaker separation

### 6. Processing Time Estimates

Based on production testing with legal depositions:
- **Processing rate**: ~75-85 seconds per 5-minute chunk
- **Token usage**: ~13,000 tokens per 5-minute chunk
- **Segments**: ~100-120 segments per 5-minute chunk

**Example: 30-minute deposition**
- 6 chunks × 80 seconds = ~8 minutes processing time
- ~78,000 tokens total
- ~630 speaker segments

## Supported Audio Formats
- WAV
- MP3
- M4A
- FLAC
- WebM
- OGG

## Production Experience & Limitations

### Successfully Tested
✅ **Rod Peters Deposition** (30 minutes)
- 6 chunks processed successfully
- 630 segments with 5 speakers identified
- 76,988 tokens
- Processing time: ~7.6 minutes
- **100% success rate**

✅ **Teresa Peters Deposition** (25 minutes)  
- 4 of 5 chunks processed (80% complete)
- 402 segments with multiple speakers
- 50,310 tokens
- 1 chunk experienced persistent 500 errors

### Known Limitations
- **Maximum audio duration: 1500 seconds (25 minutes)** per API request
- Maximum file size: 25 MB
- **Intermittent 500 errors**: Specific chunks can fail repeatedly even with retry logic
- **Regional variability**: Some Azure regions more stable than others
- Diarization accuracy depends on audio quality and speaker overlap
- No control over speaker label assignment (alphabetical: A, B, C, etc.)

### Workarounds for 500 Errors
1. Reduce chunk size (5 minutes works better than 10 minutes)
2. Implement aggressive retry logic (5-10 attempts with 45-60 second delays)
3. Try different Azure regions
4. Process failed chunks separately
5. Accept partial results when necessary (e.g., 4/5 chunks = 80% coverage)

## API Versions and Endpoints

### Azure OpenAI Deployment-Based Endpoint
For models deployed to Azure OpenAI resources (endpoints like `*.openai.azure.com`):

- **API Version**: `2025-04-01-preview` (latest for gpt-4o-transcribe-diarize)
- **Endpoint Pattern**: `https://<resource>.openai.azure.com/openai/deployments/<deployment-name>/audio/transcriptions?api-version=2025-04-01-preview`
- **Authentication**: API key or Microsoft Entra ID

Example configuration:
```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-04-01-preview
MODEL_DEPLOYMENT_NAME=gpt-4o-transcribe-diarize
```

### Azure AI Foundry Models Endpoint (Alternative)
For models deployed to Azure AI Foundry resources (endpoints like `*.services.ai.azure.com`):

- **API Version**: `preview` (literal string, not date-based)
- **Endpoint Pattern**: `https://<resource>.services.ai.azure.com/openai/v1/audio/transcriptions?api-version=preview`
- **Authentication**: API key or Microsoft Entra ID
- **Note**: Uses model name in request body instead of deployment path

> **Important**: This repository is configured for **Azure OpenAI deployment-based endpoints**. If your model is deployed to Azure AI Foundry, update the endpoint URL pattern in the scripts.

## Authentication Options

### REST API with Requests (Recommended for Production)
```python
import requests

url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{MODEL_DEPLOYMENT_NAME}/audio/transcriptions?api-version={API_VERSION}"

headers = {
    "api-key": AZURE_OPENAI_API_KEY
}

with open(audio_file, "rb") as f:
    files = {"file": (audio_file.name, f, "audio/mpeg")}
    data = {
        "model": "gpt-4o-transcribe-diarize",
        "response_format": "diarized_json",
        "chunking_strategy": "auto",
        "language": "en",
        "temperature": "0",
        "timestamp_granularities": "segment"
    }
    
    response = requests.post(url, headers=headers, files=files, data=data, timeout=300)
    result = response.json()
```

### API Key with OpenAI SDK (Alternative)
```python
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2025-03-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
```

### Microsoft Entra ID (More Secure)
```python
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), 
    "https://cognitiveservices.azure.com/.default"
)

client = AzureOpenAI(
    azure_ad_token_provider=token_provider,
  api_version="2025-03-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
```

## Key Findings & Documentation Gaps

### Critical Undocumented Feature
The `diarized_json` response format is **not documented** in official Azure OpenAI documentation but is **essential** for speaker diarization. This was discovered through:
1. GitHub issue #43964 raised by this repository author
2. Response from Azure support engineer (@AndreeaEpure) confirming the undocumented parameter
3. Production testing validating the solution

### Documentation Request Filed
A comprehensive documentation request has been submitted to Azure (see `GITHUB_RESPONSE.md`) requesting:
- Official documentation of `diarized_json` format
- Clear examples in quickstart guides
- Updated API reference with speaker diarization examples
- Best practices for legal/professional use cases

### Files in This Repository
- **SOLUTION_FOUND.md**: Detailed explanation of the `diarized_json` discovery
- **GITHUB_RESPONSE.md**: Full documentation request for Azure team
- **Production scripts**: Working examples of legal deposition processing

## Resources
- [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-foundry/openai/)
- [API Reference](https://learn.microsoft.com/azure/ai-foundry/openai/reference-preview-latest)
- [Audio Transcription Quickstart](https://learn.microsoft.com/azure/ai-foundry/openai/whisper-quickstart)
- [GitHub Issue #43964](https://github.com/Azure/azure-rest-api-specs/issues/43964) - Original issue that led to discovery

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page or submit a pull request.

## License

This project is provided as-is for educational and evaluation purposes.

## Contact

For questions or feedback regarding this test suite:
- **Author:** Arturo Quiroga
- **Role:** Senior Partner Solutions Architect, Microsoft America
- **Focus:** Enterprise Partner Solutions

---

*Built with enterprise requirements in mind for legal and professional audio transcription workflows.*
