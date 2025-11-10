#!/usr/bin/env python3
"""
Test script for Azure OpenAI gpt-4o-transcribe-diarize model using REST API with Entra ID authentication
Uses Microsoft Entra ID (Azure AD) for authentication instead of API keys
"""

import os
import sys
import argparse
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_auth_headers() -> Dict[str, str]:
    """
    Get authentication headers using Microsoft Entra ID
    
    Returns:
        Dictionary of headers with Bearer token
    """
    print("Authenticating with Microsoft Entra ID...")
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "multipart/form-data"
    }
    
    print("✓ Successfully obtained Entra ID token")
    return headers


def build_multipart_data(
    audio_file_path: str,
    model: str,
    language: Optional[str] = None,
    response_format: str = "json",
    temperature: float = 0.0,
    timestamp_granularities: Optional[List[str]] = None,
    chunking_strategy: Optional[str] = None,
    include: Optional[List[str]] = None,
    stream: bool = False
) -> Dict[str, Any]:
    """
    Build multipart form data for the API request
    
    Args:
        audio_file_path: Path to audio file
        model: Model deployment name
        language: Language code (ISO-639-1)
        response_format: Format type
        temperature: Sampling temperature
        timestamp_granularities: Timestamp levels
        chunking_strategy: VAD configuration
        include: Additional info to include (e.g., logprobs)
        stream: Enable streaming
    
    Returns:
        Dictionary suitable for requests.post files parameter
    """
    # Read audio file
    audio_file = open(audio_file_path, 'rb')
    
    # Build form data
    files = {
        'file': (Path(audio_file_path).name, audio_file, 'audio/wav')
    }
    
    data = {
        'model': (None, model),
        'temperature': (None, str(temperature)),
        'stream': (None, str(stream).lower())
    }
    
    if language:
        data['language'] = (None, language)
    
    if response_format in ['json', 'text', 'srt', 'vtt']:
        data['response_format'] = (None, response_format)
    
    if timestamp_granularities:
        for granularity in timestamp_granularities:
            data[f'timestamp_granularities'] = (None, granularity)
    
    if chunking_strategy:
        data['chunking_strategy'] = (None, chunking_strategy)
    
    if include:
        for item in include:
            data[f'include'] = (None, item)
    
    return files, data, audio_file


def transcribe_audio_rest(
    audio_file_path: str,
    model: str = "gpt-4o-transcribe-diarize",
    language: Optional[str] = "en",
    response_format: str = "json",
    temperature: float = 0.0,
    timestamp_granularities: Optional[List[str]] = None,
    chunking_strategy: Optional[str] = None,
    include: Optional[List[str]] = None,
    stream: bool = False
) -> Dict[str, Any]:
    """
    Transcribe audio using REST API with Entra ID authentication
    
    Args:
        audio_file_path: Path to audio file
        model: Model deployment name
        language: Language code
        response_format: Response format
        temperature: Sampling temperature
        timestamp_granularities: Timestamp detail levels
        chunking_strategy: Voice Activity Detection configuration
        include: Additional response data (e.g., logprobs)
        stream: Enable streaming
    
    Returns:
        Transcription result dictionary
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
    
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
    
    if not Path(audio_file_path).exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
    
    # Construct URL using Azure OpenAI deployment-based endpoint pattern
    url = f"{endpoint}openai/deployments/{model}/audio/transcriptions?api-version={api_version}"
    
    print(f"\n{'='*60}")
    print(f"REST API Transcription (Entra ID Auth)")
    print(f"{'='*60}")
    print(f"Endpoint: {endpoint}")
    print(f"API Version: {api_version}")
    print(f"Audio File: {audio_file_path}")
    print(f"Model: {model}")
    print(f"Language: {language}")
    print(f"Temperature: {temperature}")
    print(f"Response Format: {response_format}")
    if timestamp_granularities:
        print(f"Timestamp Granularities: {timestamp_granularities}")
    if chunking_strategy:
        print(f"Chunking Strategy: {chunking_strategy}")
    if include:
        print(f"Include: {include}")
    if stream:
        print(f"Streaming: Enabled")
    print(f"{'='*60}\n")
    
    start_time = datetime.now()
    
    # Get headers with Entra ID token (without Content-Type as requests will set it)
    auth_headers = get_auth_headers()
    headers = {k: v for k, v in auth_headers.items() if k != "Content-Type"}
    
    # Build multipart data
    files, data, audio_file_handle = build_multipart_data(
        audio_file_path=audio_file_path,
        model=model,
        language=language,
        response_format=response_format,
        temperature=temperature,
        timestamp_granularities=timestamp_granularities,
        chunking_strategy=chunking_strategy,
        include=include,
        stream=stream
    )
    
    try:
        # Make request
        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✓ Transcription completed in {duration:.2f} seconds")
        print(f"✓ Status Code: {response.status_code}")
        
        # Parse response based on format
        if response_format in ['json', 'verbose_json']:
            result = response.json()
        else:
            result = {"text": response.text}
        
        return {
            "result": result,
            "duration_seconds": duration,
            "timestamp": start_time.isoformat(),
            "status_code": response.status_code,
            "headers": dict(response.headers)
        }
        
    except requests.exceptions.HTTPError as e:
        print(f"\n✗ HTTP Error: {e}")
        print(f"Response: {e.response.text}")
        raise
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
    finally:
        audio_file_handle.close()


def save_results(
    result_data: Dict[str, Any],
    output_dir: str = "output",
    audio_filename: str = "transcription"
) -> str:
    """
    Save transcription results to file
    
    Args:
        result_data: Result dictionary
        output_dir: Output directory
        audio_filename: Base filename
    
    Returns:
        Path to saved file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = Path(audio_filename).stem
    output_file = os.path.join(output_dir, f"{base_name}_rest_entra_{timestamp}.json")
    
    output_data = {
        "metadata": {
            "transcription_date": result_data["timestamp"],
            "duration_seconds": result_data["duration_seconds"],
            "audio_file": audio_filename,
            "status_code": result_data["status_code"],
            "api_method": "REST API (Entra ID)",
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
    Display transcription summary with diarization
    
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
            
            # Additional info
            avg_logprob = segment.get('avg_logprob')
            no_speech_prob = segment.get('no_speech_prob')
            
            print(f"[{start:.2f}s - {end:.2f}s] {speaker}:")
            print(f"  {text.strip()}")
            
            if avg_logprob is not None:
                print(f"  Avg Log Prob: {avg_logprob:.4f}")
            if no_speech_prob is not None:
                print(f"  No Speech Prob: {no_speech_prob:.4f}")
            print()
    
    # Display word-level info if available
    if 'words' in result:
        print(f"{'='*60}")
        print(f"Word-level timestamps available: {len(result['words'])} words")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Test Azure OpenAI gpt-4o-transcribe-diarize with Entra ID authentication"
    )
    parser.add_argument(
        "--audio",
        type=str,
        required=True,
        help="Path to audio file"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-transcribe-diarize",
        help="Model deployment name"
    )
    parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Language code (ISO-639-1)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature 0-1"
    )
    parser.add_argument(
        "--response-format",
        type=str,
        default="json",
        choices=["json", "text", "srt", "vtt"],
        help="Response format"
    )
    parser.add_argument(
        "--word-timestamps",
        action="store_true",
        help="Include word-level timestamps"
    )
    parser.add_argument(
        "--include-logprobs",
        action="store_true",
        help="Include log probabilities"
    )
    parser.add_argument(
        "--chunking-strategy",
        type=str,
        choices=["server_vad", "none"],
        default="server_vad",
        help="Chunking strategy type"
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Enable streaming response"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Output directory"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to file"
    )
    
    args = parser.parse_args()
    
    try:
        # Build timestamp granularities
        timestamp_granularities = None
        if args.word_timestamps:
            timestamp_granularities = ["word", "segment"]
        
        # Build chunking strategy
        chunking_strategy = None
        if args.chunking_strategy == "server_vad":
            chunking_strategy = "auto"
            print("Using chunking_strategy='auto' (server-managed VAD)")
        
        # Build include list
        include = None
        if args.include_logprobs:
            if args.response_format not in ['json', 'verbose_json']:
                print("Warning: logprobs only works with json/verbose_json format")
            else:
                include = ["logprobs"]
        
        # Transcribe
        result_data = transcribe_audio_rest(
            audio_file_path=args.audio,
            model=args.model,
            language=args.language,
            response_format=args.response_format,
            temperature=args.temperature,
            timestamp_granularities=timestamp_granularities,
            chunking_strategy=chunking_strategy,
            include=include,
            stream=args.stream
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
