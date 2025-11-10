# Azure OpenAI GPT-4o-Transcribe-Diarize Testing Suite

This repository contains comprehensive test scripts for the Azure OpenAI `gpt-4o-transcribe-diarize` model, specifically designed for litigation deposition audio file analysis.

## Author

**Arturo Quiroga**  
Senior Partner Solutions Architect  
Enterprise Partner Solutions - Microsoft America

This test suite provides enterprise-grade tools for evaluating and implementing the gpt-4o-transcribe-diarize model in legal and professional audio transcription workflows.

## Model Overview

The `gpt-4o-transcribe-diarize` model is an Automatic Speech Recognition (ASR) model that:
- Converts spoken language into text in real-time
- **Identifies who spoke when** (diarization) - critical for legal proceedings
- Supports 100+ languages
- Provides ultra-low latency with high accuracy
- Available via `/audio/transcriptions` REST API

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

### Chunking Strategy
Server-side Voice Activity Detection (VAD) for optimal audio segmentation:
- `prefix_padding_ms`: Audio before speech (default: 300ms)
- `silence_duration_ms`: Silence threshold to detect speech end (default: 200ms)
- `threshold`: Sensitivity (0.0-1.0, default: 0.5) - higher for noisy environments

## Repository Structure

```
GPT-4o-Transcribe-Diarize/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── test_audio/                  # Place your test audio files here
│   └── .gitkeep
├── output/                      # Transcription results
│   └── .gitkeep
├── scripts/
│   ├── test_sdk.py             # Python SDK-based tests
│   ├── test_rest_api.py        # Direct REST API tests
│   ├── test_parameters.py      # Systematic parameter testing
│   └── utils.py                # Shared utilities
└── config/
    └── .env.example            # Environment variable template
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
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint (e.g., https://your-resource.openai.azure.com)
- `AZURE_OPENAI_API_KEY`: Your API key (or use Entra ID authentication)
- `AZURE_OPENAI_API_VERSION`: API version (default: 2025-01-01-preview)

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
| `language` | string | ISO-639-1 code (e.g., `en`) | Auto-detect |
| `prompt` | string | Free-text guidance for style/context | - |
| `response_format` | object | Output format (json/text/srt/vtt) | json |
| `temperature` | float | Sampling temperature (0-1) | 0 |
| `timestamp_granularities` | array | `['word']` and/or `['segment']` | ['segment'] |
| `stream` | boolean | Enable streaming response | false |

### Advanced Parameters

#### Chunking Strategy (VAD)
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

### Response Format

With diarization, the response includes speaker identification:

```json
{
  "text": "Full transcript",
  "segments": [
    {
      "id": 0,
      "speaker": "SPEAKER_00",
      "start": 0.0,
      "end": 5.2,
      "text": "This is the attorney speaking.",
      "tokens": [...],
      "temperature": 0.0,
      "avg_logprob": -0.25,
      "compression_ratio": 1.3,
      "no_speech_prob": 0.01
    },
    {
      "id": 1,
      "speaker": "SPEAKER_01",
      "start": 5.5,
      "end": 12.8,
      "text": "This is the witness responding.",
      ...
    }
  ],
  "words": [
    {
      "word": "This",
      "start": 0.0,
      "end": 0.3,
      "speaker": "SPEAKER_00"
    },
    ...
  ]
}
```

## Best Practices for Legal Depositions

### 1. Audio Quality
- Use high-quality recordings (minimum 16kHz sampling rate)
- WAV, MP3, FLAC formats supported
- Minimize background noise

### 2. Language Specification
Always specify the language for:
- Better accuracy
- Lower latency
```python
language="en"  # English
```

### 3. Prompt Engineering
Provide context for better transcription:
```python
prompt="Legal deposition with attorney and witness. Expect legal terminology, medical terms, and technical language."
```

### 4. Temperature Setting
- Use `0.0` (default) for deterministic, focused transcription
- Increase slightly (0.1-0.2) if model seems too conservative

### 5. Chunking Strategy
For noisy courtroom environments:
```python
chunking_strategy={
    "type": "server_vad",
    "threshold": 0.6,  # Higher threshold for noisy environments
    "silence_duration_ms": 300,  # Longer pause detection
    "prefix_padding_ms": 400  # More context before speech
}
```

### 6. Timestamp Granularities
Request both for detailed analysis:
```python
timestamp_granularities=["word", "segment"]
```

### 7. Log Probabilities
Enable for quality assessment:
```python
include=["logprobs"],
response_format={"type": "json"}
```

## Supported Audio Formats
- WAV
- MP3
- M4A
- FLAC
- WebM
- OGG

## Limitations
- Maximum file size: Check Azure OpenAI limits
- Real-time processing depends on audio length
- Diarization accuracy varies with audio quality and speaker overlap

## API Versions
- Current: `2025-01-01-preview` (recommended)
- Previous: `2024-11-01-preview`

## Authentication Options

### API Key (Simplest)
```python
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2025-01-01-preview",
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
    api_version="2025-01-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
```

## Resources
- [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-foundry/openai/)
- [API Reference](https://learn.microsoft.com/azure/ai-foundry/openai/reference-preview-latest)
- [Audio Transcription Quickstart](https://learn.microsoft.com/azure/ai-foundry/openai/whisper-quickstart)

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
