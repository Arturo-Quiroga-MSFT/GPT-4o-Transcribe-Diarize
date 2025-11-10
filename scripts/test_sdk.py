#!/usr/bin/env python3
"""
Test script for Azure OpenAI gpt-4o-transcribe-diarize model using Python SDK
Designed for testing litigation deposition audio files with speaker diarization
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def setup_client(use_entra_id: bool = False) -> AzureOpenAI:
    """
    Setup Azure OpenAI client with either API key or Entra ID authentication
    
    Args:
        use_entra_id: If True, use Microsoft Entra ID authentication, else use API key
    
    Returns:
        Configured AzureOpenAI client
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
    
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
    
    if use_entra_id:
        print("Using Microsoft Entra ID authentication...")
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), 
            "https://cognitiveservices.azure.com/.default"
        )
        client = AzureOpenAI(
            azure_ad_token_provider=token_provider,
            api_version=api_version,
            azure_endpoint=endpoint
        )
    else:
        print("Using API key authentication...")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")
        
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint
        )
    
    return client


def transcribe_audio(
    client: AzureOpenAI,
    audio_file_path: str,
    model: str = "gpt-4o-transcribe-diarize",
    language: Optional[str] = "en",
    prompt: Optional[str] = None,
    response_format: str = "verbose_json",
    temperature: float = 0.0,
    timestamp_granularities: Optional[list] = None
) -> Dict[str, Any]:
    """
    Transcribe audio file with diarization using Azure OpenAI
    
    Args:
        client: AzureOpenAI client instance
        audio_file_path: Path to the audio file
        model: Model deployment name
        language: ISO-639-1 language code (e.g., 'en')
        prompt: Optional text to guide the model's style or provide context
        response_format: Format of the response (json, verbose_json, text, srt, vtt)
        temperature: Sampling temperature (0-1)
        timestamp_granularities: List of timestamp levels (word, segment)
    
    Returns:
        Transcription result dictionary
    """
    if not Path(audio_file_path).exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
    
    print(f"\n{'='*60}")
    print(f"Transcribing: {audio_file_path}")
    print(f"Model: {model}")
    print(f"Language: {language}")
    print(f"Temperature: {temperature}")
    print(f"Response Format: {response_format}")
    if prompt:
        print(f"Prompt: {prompt}")
    if timestamp_granularities:
        print(f"Timestamp Granularities: {timestamp_granularities}")
    print(f"{'='*60}\n")
    
    start_time = datetime.now()
    
    with open(audio_file_path, 'rb') as audio_file:
        # Build parameters
        params = {
            "file": audio_file,
            "model": model,
            "response_format": response_format,
            "temperature": temperature
        }
        
        if language:
            params["language"] = language
        
        if prompt:
            params["prompt"] = prompt
        
        if timestamp_granularities:
            params["timestamp_granularities"] = timestamp_granularities
        
        # Make the transcription request
        result = client.audio.transcriptions.create(**params)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"✓ Transcription completed in {duration:.2f} seconds")
    
    return {
        "result": result,
        "duration_seconds": duration,
        "timestamp": start_time.isoformat()
    }


def save_results(
    result_data: Dict[str, Any],
    output_dir: str = "output",
    audio_filename: str = "transcription"
) -> str:
    """
    Save transcription results to file
    
    Args:
        result_data: Dictionary containing transcription result and metadata
        output_dir: Directory to save results
        audio_filename: Base filename for output
    
    Returns:
        Path to saved file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = Path(audio_filename).stem
    output_file = os.path.join(output_dir, f"{base_name}_{timestamp}.json")
    
    # Convert result to dict if it's not already
    result = result_data["result"]
    if hasattr(result, 'model_dump'):
        result_dict = result.model_dump()
    elif hasattr(result, 'to_dict'):
        result_dict = result.to_dict()
    else:
        result_dict = dict(result)
    
    # Create output data
    output_data = {
        "metadata": {
            "transcription_date": result_data["timestamp"],
            "duration_seconds": result_data["duration_seconds"],
            "audio_file": audio_filename
        },
        "transcription": result_dict
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Results saved to: {output_file}")
    return output_file


def display_transcription_summary(result: Any):
    """
    Display a summary of the transcription with speaker diarization
    
    Args:
        result: Transcription result object
    """
    print(f"\n{'='*60}")
    print("TRANSCRIPTION SUMMARY")
    print(f"{'='*60}\n")
    
    # Handle different result formats
    if hasattr(result, 'text'):
        text = result.text
    elif isinstance(result, dict) and 'text' in result:
        text = result['text']
    else:
        text = str(result)
    
    print(f"Full Transcript:\n{text}\n")
    
    # Try to display segments with speaker information
    if hasattr(result, 'segments') and result.segments:
        print(f"{'='*60}")
        print("SPEAKER DIARIZATION (Segments)")
        print(f"{'='*60}\n")
        
        for segment in result.segments:
            speaker = getattr(segment, 'speaker', 'Unknown')
            start = getattr(segment, 'start', 0)
            end = getattr(segment, 'end', 0)
            seg_text = getattr(segment, 'text', '')
            
            print(f"[{start:.2f}s - {end:.2f}s] {speaker}:")
            print(f"  {seg_text.strip()}\n")
    
    # Try to display words if available
    if hasattr(result, 'words') and result.words:
        print(f"{'='*60}")
        print(f"Word-level timestamps available: {len(result.words)} words")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Test Azure OpenAI gpt-4o-transcribe-diarize model with Python SDK"
    )
    parser.add_argument(
        "--audio",
        type=str,
        required=True,
        help="Path to audio file to transcribe"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-transcribe-diarize",
        help="Model deployment name (default: gpt-4o-transcribe-diarize)"
    )
    parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Language code (ISO-639-1, e.g., 'en' for English)"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Optional prompt to guide the model (e.g., 'Legal deposition with attorney and witness')"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature 0-1 (default: 0.0 for deterministic)"
    )
    parser.add_argument(
        "--response-format",
        type=str,
        default="verbose_json",
        choices=["json", "verbose_json", "text", "srt", "vtt"],
        help="Response format (default: verbose_json)"
    )
    parser.add_argument(
        "--word-timestamps",
        action="store_true",
        help="Include word-level timestamps"
    )
    parser.add_argument(
        "--use-entra-id",
        action="store_true",
        help="Use Microsoft Entra ID authentication instead of API key"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory to save results (default: output)"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to file"
    )
    
    args = parser.parse_args()
    
    try:
        # Setup client
        client = setup_client(use_entra_id=args.use_entra_id)
        
        # Determine timestamp granularities
        timestamp_granularities = None
        if args.word_timestamps:
            timestamp_granularities = ["word", "segment"]
        
        # Transcribe audio
        result_data = transcribe_audio(
            client=client,
            audio_file_path=args.audio,
            model=args.model,
            language=args.language,
            prompt=args.prompt,
            response_format=args.response_format,
            temperature=args.temperature,
            timestamp_granularities=timestamp_granularities
        )
        
        # Display summary
        display_transcription_summary(result_data["result"])
        
        # Save results if requested
        if not args.no_save:
            save_results(
                result_data=result_data,
                output_dir=args.output_dir,
                audio_filename=args.audio
            )
        
        print("\n✓ Test completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
