#!/usr/bin/env python3
"""
Test script for Azure OpenAI gpt-4o-transcribe-diarize model using Python SDK with Entra ID
Uses Microsoft Entra ID (Azure AD) for authentication instead of API keys
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


def setup_client() -> AzureOpenAI:
    """
    Setup Azure OpenAI client with Entra ID authentication
    
    Returns:
        Configured AzureOpenAI client with Entra ID token provider
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
    
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
    
    print("Authenticating with Microsoft Entra ID...")
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), 
        "https://cognitiveservices.azure.com/.default"
    )
    
    client = AzureOpenAI(
        azure_ad_token_provider=token_provider,
        api_version=api_version,
        azure_endpoint=endpoint
    )
    
    print("✓ Successfully configured Azure OpenAI client with Entra ID")
    return client


def transcribe_audio(
    client: AzureOpenAI,
    audio_file_path: str,
    model: str = "gpt-4o-transcribe-diarize",
    language: Optional[str] = "en",
    response_format: str = "json",
    temperature: float = 0.0,
    timestamp_granularities: Optional[list] = None
) -> Dict[str, Any]:
    """
    Transcribe audio file with diarization using Azure OpenAI SDK
    
    Args:
        client: AzureOpenAI client instance
        audio_file_path: Path to the audio file
        model: Model deployment name
        language: ISO-639-1 language code (e.g., 'en')
        response_format: Format of the response (json, text, srt, vtt)
        temperature: Sampling temperature (0-1)
        timestamp_granularities: List of timestamp levels (word, segment)
    
    Returns:
        Transcription result dictionary
    """
    if not Path(audio_file_path).exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
    
    print(f"\n{'='*60}")
    print(f"SDK Transcription (Entra ID Auth)")
    print(f"{'='*60}")
    print(f"Audio File: {audio_file_path}")
    print(f"Model: {model}")
    print(f"Language: {language}")
    print(f"Response Format: {response_format}")
    print(f"Temperature: {temperature}")
    if timestamp_granularities:
        print(f"Timestamp Granularities: {timestamp_granularities}")
    print(f"{'='*60}\n")
    
    start_time = datetime.now()
    
    # Open and transcribe the audio file
    with open(audio_file_path, 'rb') as audio_file:
        # Build API call parameters
        api_params = {
            "model": model,
            "file": audio_file,
            "temperature": temperature
        }
        
        # Add optional parameters
        if language:
            api_params["language"] = language
        
        if response_format in ['json', 'text', 'srt', 'vtt']:
            api_params["response_format"] = response_format
        
        if timestamp_granularities:
            api_params["timestamp_granularities"] = timestamp_granularities
        
        # Note: chunking_strategy is required but handled by SDK automatically
        print("Calling Azure OpenAI API with Entra ID authentication...")
        
        try:
            transcript = client.audio.transcriptions.create(**api_params)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"\n✓ Transcription completed in {duration:.2f} seconds")
            
            # Convert to dictionary
            if response_format == 'json':
                result = transcript.model_dump() if hasattr(transcript, 'model_dump') else transcript
            else:
                result = {"text": str(transcript)}
            
            return {
                "result": result,
                "duration_seconds": duration,
                "timestamp": start_time.isoformat()
            }
            
        except Exception as e:
            print(f"\n✗ Transcription failed: {e}")
            raise


def save_results(
    result_data: Dict[str, Any],
    output_dir: str = "output",
    audio_filename: str = "transcription"
) -> str:
    """
    Save transcription results to JSON file
    
    Args:
        result_data: Result dictionary from transcription
        output_dir: Directory to save output file
        audio_filename: Original audio filename for naming
    
    Returns:
        Path to the saved output file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = Path(audio_filename).stem
    output_file = os.path.join(output_dir, f"{base_name}_sdk_entra_{timestamp}.json")
    
    # Create output structure
    output_data = {
        "metadata": {
            "transcription_date": result_data["timestamp"],
            "duration_seconds": result_data["duration_seconds"],
            "audio_file": audio_filename,
            "api_method": "Python SDK (Entra ID)",
            "authentication": "Microsoft Entra ID"
        },
        "transcription": result_data["result"]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Results saved to: {output_file}")
    return output_file


def display_transcription_summary(result: Dict[str, Any]):
    """
    Display a summary of the transcription results with speaker diarization
    
    Args:
        result: Transcription result dictionary
    """
    print(f"\n{'='*60}")
    print("TRANSCRIPTION SUMMARY")
    print(f"{'='*60}\n")
    
    # Display full transcript
    if 'text' in result:
        print(f"Full Transcript:\n{result['text']}\n")
    
    # Display segments with speaker diarization
    if 'segments' in result:
        print(f"{'='*60}")
        print("SPEAKER DIARIZATION (Segments)")
        print(f"{'='*60}\n")
        
        for segment in result['segments']:
            speaker = segment.get('speaker', 'Unknown')
            start = segment.get('start', 0)
            end = segment.get('end', 0)
            text = segment.get('text', '')
            
            # Additional metadata
            avg_logprob = segment.get('avg_logprob')
            no_speech_prob = segment.get('no_speech_prob')
            
            print(f"[{start:.2f}s - {end:.2f}s] {speaker}:")
            print(f"  {text.strip()}")
            
            if avg_logprob is not None:
                print(f"  Avg Log Prob: {avg_logprob:.4f}")
            if no_speech_prob is not None:
                print(f"  No Speech Prob: {no_speech_prob:.4f}")
            print()
    
    # Display word-level timestamps if available
    if 'words' in result:
        print(f"{'='*60}")
        print(f"Word-level timestamps available: {len(result['words'])} words")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Test Azure OpenAI gpt-4o-transcribe-diarize with SDK and Entra ID"
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
        "--response-format",
        type=str,
        default="json",
        choices=["json", "text", "srt", "vtt"],
        help="Response format (default: json)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature 0-1 (default: 0.0 for deterministic)"
    )
    parser.add_argument(
        "--word-timestamps",
        action="store_true",
        help="Include word-level timestamps in response"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Output directory for results (default: output)"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to file, only display"
    )
    
    args = parser.parse_args()
    
    try:
        # Setup client with Entra ID
        client = setup_client()
        
        # Build timestamp granularities
        timestamp_granularities = None
        if args.word_timestamps:
            timestamp_granularities = ["word", "segment"]
        
        # Transcribe audio
        result_data = transcribe_audio(
            client=client,
            audio_file_path=args.audio,
            model=args.model,
            language=args.language,
            response_format=args.response_format,
            temperature=args.temperature,
            timestamp_granularities=timestamp_granularities
        )
        
        # Display summary
        display_transcription_summary(result_data["result"])
        
        # Save results
        if not args.no_save:
            save_results(
                result_data=result_data,
                output_dir=args.output_dir,
                audio_filename=args.audio
            )
        
        print("\n✓ Test completed successfully with Entra ID authentication!")
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
