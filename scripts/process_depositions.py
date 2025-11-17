#!/usr/bin/env python3
"""
Process deposition audio files with automatic chunking for files longer than 25 minutes
Handles the gpt-4o-transcribe-diarize model's 1500-second (25 minute) limit
"""

import os
import sys
import json
import requests
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Model limits
MAX_DURATION_SECONDS = 1500  # 25 minutes
CHUNK_DURATION_SECONDS = 1400  # 23.3 minutes (leave buffer for processing)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 10


def get_audio_duration(audio_file: str) -> float:
    """Get audio duration in seconds using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"  ⚠ Warning: Could not determine audio duration: {e}")
        return 0


def split_audio(audio_file: str, chunk_duration: int = CHUNK_DURATION_SECONDS) -> List[str]:
    """
    Split audio file into chunks using ffmpeg
    
    Returns:
        List of chunk file paths
    """
    duration = get_audio_duration(audio_file)
    
    if duration <= MAX_DURATION_SECONDS:
        return [audio_file]
    
    print(f"  → Audio duration: {duration:.1f}s ({duration/60:.1f} min) - splitting into chunks...")
    
    output_dir = Path(audio_file).parent / "chunks"
    output_dir.mkdir(exist_ok=True)
    
    base_name = Path(audio_file).stem
    num_chunks = int((duration / chunk_duration) + 1)
    
    chunk_files = []
    
    for i in range(num_chunks):
        start_time = i * chunk_duration
        chunk_file = output_dir / f"{base_name}_chunk_{i+1:02d}.mp3"
        
        # Use ffmpeg to extract chunk
        cmd = [
            'ffmpeg',
            '-i', audio_file,
            '-ss', str(start_time),
            '-t', str(chunk_duration),
            '-acodec', 'copy',
            '-y',  # Overwrite output file
            str(chunk_file)
        ]
        
        print(f"    → Creating chunk {i+1}/{num_chunks} (start: {start_time}s)...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"    ✗ Error creating chunk: {result.stderr}")
            continue
        
        chunk_files.append(str(chunk_file))
        print(f"    ✓ Created: {chunk_file.name}")
    
    print(f"  ✓ Split into {len(chunk_files)} chunks")
    return chunk_files


def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers using Microsoft Entra ID"""
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    return {"Authorization": f"Bearer {token.token}"}


def transcribe_audio_chunk(
    audio_file_path: str,
    chunk_num: int = 1,
    total_chunks: int = 1,
    model: str = "gpt-4o-transcribe-diarize",
    language: str = "en",
    temperature: float = 0.0
) -> Dict[str, Any]:
    """
    Transcribe a single audio chunk with diarization (with retry logic)
    
    Returns:
        Dictionary with result, timing, and token usage
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
    
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
    
    url = f"{endpoint}openai/deployments/{model}/audio/transcriptions?api-version={api_version}"
    
    chunk_label = f"[Chunk {chunk_num}/{total_chunks}]" if total_chunks > 1 else ""
    
    # Retry loop for transient errors
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if attempt > 1:
                print(f"  → {chunk_label} Retry attempt {attempt}/{MAX_RETRIES}...")
            else:
                print(f"  → {chunk_label} Starting transcription...")
            
            start_time = datetime.now()
            
            # Get authentication headers
            headers = get_auth_headers()
            
            # Build multipart form data
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'file': (Path(audio_file_path).name, audio_file, 'audio/mpeg')
                }
                
                data = {
                    'model': model,
                    'response_format': 'diarized_json',
                    'chunking_strategy': 'auto',
                    'language': language,
                    'temperature': str(temperature)
                }
                
                # Make request
                response = requests.post(url, headers=headers, files=files, data=data)
                
                # Check for errors
                if response.status_code == 500:
                    error_data = response.json()
                    print(f"  ⚠ {chunk_label} Server error (attempt {attempt}/{MAX_RETRIES})")
                    
                    if attempt < MAX_RETRIES:
                        print(f"    Waiting {RETRY_DELAY_SECONDS}s before retry...")
                        time.sleep(RETRY_DELAY_SECONDS)
                        continue
                    else:
                        print(f"  ✗ API Error (Status {response.status_code}):")
                        print(f"  {json.dumps(error_data, indent=2)}")
                        response.raise_for_status()
                
                elif response.status_code != 200:
                    print(f"  ✗ API Error (Status {response.status_code}):")
                    print(f"  {json.dumps(response.json(), indent=2)}")
                    response.raise_for_status()
            
            # Success!
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = response.json()
            
            # Extract token usage
            usage = result.get('usage', {})
            total_tokens = usage.get('total_tokens', 0)
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            
            # Get audio token details if available
            input_details = usage.get('input_token_details', {})
            audio_tokens = input_details.get('audio_tokens', 0)
            text_tokens = input_details.get('text_tokens', 0)
            
            print(f"  ✓ {chunk_label} Completed in {duration:.2f}s")
            print(f"    Tokens: {total_tokens:,} (Input: {input_tokens:,}, Output: {output_tokens:,})")
            print(f"    Segments: {len(result.get('segments', []))}")
            
            return {
                "result": result,
                "duration_seconds": duration,
                "timestamp": start_time.isoformat(),
                "chunk_number": chunk_num,
                "usage": {
                    "total_tokens": total_tokens,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "audio_tokens": audio_tokens,
                    "text_tokens": text_tokens
                }
            }
            
        except requests.exceptions.HTTPError as e:
            if attempt < MAX_RETRIES and e.response.status_code == 500:
                continue
            raise
        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"  ⚠ {chunk_label} Error: {e}")
                print(f"    Waiting {RETRY_DELAY_SECONDS}s before retry...")
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            raise
    
    # Should not reach here
    raise Exception(f"Failed after {MAX_RETRIES} attempts")


def merge_transcriptions(chunk_results: List[Dict[str, Any]], chunk_duration: int) -> Dict[str, Any]:
    """
    Merge multiple chunk transcriptions into a single result
    
    Args:
        chunk_results: List of transcription results from chunks
        chunk_duration: Duration of each chunk in seconds
    
    Returns:
        Merged transcription result
    """
    if len(chunk_results) == 1:
        return chunk_results[0]
    
    print(f"  → Merging {len(chunk_results)} chunks...")
    
    # Combine text
    full_text = " ".join(chunk["result"]["text"] for chunk in chunk_results)
    
    # Combine segments with adjusted timestamps
    all_segments = []
    time_offset = 0
    
    for chunk in chunk_results:
        chunk_segments = chunk["result"].get("segments", [])
        
        for segment in chunk_segments:
            adjusted_segment = segment.copy()
            adjusted_segment["start"] += time_offset
            adjusted_segment["end"] += time_offset
            adjusted_segment["id"] = f"seg_{len(all_segments) + 1}"
            all_segments.append(adjusted_segment)
        
        time_offset += chunk_duration
    
    # Aggregate usage stats
    total_usage = {
        "total_tokens": sum(c["usage"]["total_tokens"] for c in chunk_results),
        "input_tokens": sum(c["usage"]["input_tokens"] for c in chunk_results),
        "output_tokens": sum(c["usage"]["output_tokens"] for c in chunk_results),
        "audio_tokens": sum(c["usage"]["audio_tokens"] for c in chunk_results),
        "text_tokens": sum(c["usage"]["text_tokens"] for c in chunk_results)
    }
    
    total_duration = sum(c["duration_seconds"] for c in chunk_results)
    
    print(f"  ✓ Merged {len(all_segments)} total segments")
    print(f"  ✓ Total processing time: {total_duration:.2f}s")
    print(f"  ✓ Total tokens: {total_usage['total_tokens']:,}")
    
    return {
        "result": {
            "text": full_text,
            "segments": all_segments,
            "usage": {
                "type": "tokens",
                **total_usage
            }
        },
        "duration_seconds": total_duration,
        "timestamp": chunk_results[0]["timestamp"],
        "usage": total_usage,
        "chunks_processed": len(chunk_results)
    }


def format_text_output(result: Dict[str, Any]) -> str:
    """Format transcription result as readable text with speaker labels"""
    lines = []
    lines.append("=" * 80)
    lines.append("DEPOSITION TRANSCRIPTION WITH SPEAKER DIARIZATION")
    lines.append("=" * 80)
    lines.append("")
    
    # Add full transcript
    if 'text' in result:
        lines.append("FULL TRANSCRIPT:")
        lines.append("-" * 80)
        lines.append(result['text'])
        lines.append("")
    
    # Add speaker-segmented transcript
    if 'segments' in result:
        lines.append("")
        lines.append("=" * 80)
        lines.append("SPEAKER-SEGMENTED TRANSCRIPT")
        lines.append("=" * 80)
        lines.append("")
        
        current_speaker = None
        speaker_text = []
        
        for segment in result['segments']:
            speaker = segment.get('speaker', 'Unknown')
            text = segment.get('text', '').strip()
            
            # Group consecutive segments from same speaker
            if speaker != current_speaker:
                # Output previous speaker's text
                if current_speaker and speaker_text:
                    lines.append(f"\n[Speaker {current_speaker}]")
                    lines.append(''.join(speaker_text))
                    lines.append("")
                
                # Start new speaker
                current_speaker = speaker
                speaker_text = [text]
            else:
                speaker_text.append(text)
        
        # Output final speaker's text
        if current_speaker and speaker_text:
            lines.append(f"\n[Speaker {current_speaker}]")
            lines.append(''.join(speaker_text))
            lines.append("")
    
    return '\n'.join(lines)


def save_results(
    transcription_data: Dict[str, Any],
    audio_file: str,
    model: str,
    output_dir: str = "output/depositions"
) -> Tuple[str, str]:
    """Save transcription results to JSON and text files"""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = Path(audio_file)
    base_name = audio_path.stem.replace(' ', '_')
    
    # Save JSON with full data
    json_file = os.path.join(output_dir, f"{base_name}_{timestamp}.json")
    json_data = {
        "metadata": {
            "transcription_date": transcription_data["timestamp"],
            "duration_seconds": transcription_data["duration_seconds"],
            "audio_file": audio_file,
            "model": model,
            "authentication": "Microsoft Entra ID",
            "chunks_processed": transcription_data.get("chunks_processed", 1)
        },
        "usage": transcription_data["usage"],
        "transcription": transcription_data["result"]
    }
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    # Save text file with formatted output
    text_file = os.path.join(output_dir, f"{base_name}_{timestamp}.txt")
    text_content = format_text_output(transcription_data["result"])
    
    # Add metadata header to text file
    metadata_lines = [
        "=" * 80,
        "METADATA",
        "=" * 80,
        f"Date: {transcription_data['timestamp']}",
        f"Audio File: {audio_path.name}",
        f"Processing Time: {transcription_data['duration_seconds']:.2f} seconds",
        f"Model: {model}",
        f"Chunks Processed: {transcription_data.get('chunks_processed', 1)}",
        f"Total Tokens: {transcription_data['usage']['total_tokens']:,}",
        f"  - Input Tokens: {transcription_data['usage']['input_tokens']:,}",
        f"  - Output Tokens: {transcription_data['usage']['output_tokens']:,}",
        f"  - Audio Tokens: {transcription_data['usage']['audio_tokens']:,}",
        f"  - Text Tokens: {transcription_data['usage']['text_tokens']:,}",
        "",
        ""
    ]
    
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(metadata_lines))
        f.write(text_content)
    
    print(f"  ✓ Saved JSON: {json_file}")
    print(f"  ✓ Saved text: {text_file}")
    
    return json_file, text_file


def process_deposition(audio_file: str) -> Dict[str, Any]:
    """Process a single deposition audio file (with automatic chunking if needed)"""
    print(f"  → Checking audio duration...")
    duration = get_audio_duration(audio_file)
    print(f"  ✓ Duration: {duration:.1f}s ({duration/60:.1f} minutes)")
    
    # Authenticate once
    print(f"  → Authenticating with Microsoft Entra ID...")
    get_auth_headers()  # This will cache credentials
    print(f"  ✓ Successfully authenticated")
    
    # Split if necessary
    if duration > MAX_DURATION_SECONDS:
        chunk_files = split_audio(audio_file, CHUNK_DURATION_SECONDS)
    else:
        chunk_files = [audio_file]
    
    # Process all chunks
    chunk_results = []
    for i, chunk_file in enumerate(chunk_files, 1):
        try:
            result = transcribe_audio_chunk(
                chunk_file,
                chunk_num=i,
                total_chunks=len(chunk_files)
            )
            chunk_results.append(result)
        except Exception as e:
            print(f"  ✗ Error processing chunk {i}: {e}")
            raise
    
    # Merge results if multiple chunks
    merged_result = merge_transcriptions(chunk_results, CHUNK_DURATION_SECONDS)
    
    # Save results
    json_path, text_path = save_results(merged_result, audio_file, "gpt-4o-transcribe-diarize")
    
    return {
        "audio_file": Path(audio_file).name,
        "success": True,
        "duration_seconds": merged_result["duration_seconds"],
        "usage": merged_result["usage"],
        "json_output": json_path,
        "text_output": text_path,
        "segments_count": len(merged_result["result"].get('segments', [])),
        "chunks_processed": merged_result.get("chunks_processed", 1),
        "audio_duration_seconds": duration
    }


def process_all_depositions(depositions_dir: str = "depositions") -> List[Dict[str, Any]]:
    """Process all audio files in the depositions directory"""
    depositions_path = Path(depositions_dir)
    
    if not depositions_path.exists():
        raise FileNotFoundError(f"Depositions directory not found: {depositions_dir}")
    
    # Find all MP3 files (excluding chunks directory)
    audio_files = [f for f in depositions_path.rglob("*.mp3") if "chunks" not in f.parts]
    
    if not audio_files:
        raise FileNotFoundError(f"No MP3 files found in {depositions_dir}")
    
    print(f"\n{'='*80}")
    print(f"PROCESSING {len(audio_files)} DEPOSITION AUDIO FILE(S)")
    print(f"{'='*80}\n")
    
    results = []
    
    for idx, audio_file in enumerate(audio_files, 1):
        print(f"\n[{idx}/{len(audio_files)}] Processing: {audio_file.name}")
        print("-" * 80)
        
        try:
            result = process_deposition(str(audio_file))
            results.append(result)
            print(f"  ✓ Successfully processed {audio_file.name}")
            
        except Exception as e:
            print(f"  ✗ Error processing {audio_file.name}: {e}")
            results.append({
                "audio_file": audio_file.name,
                "success": False,
                "error": str(e)
            })
    
    return results


def print_summary(results: List[Dict[str, Any]]):
    """Print summary of all processing results"""
    print(f"\n\n{'='*80}")
    print("PROCESSING SUMMARY")
    print(f"{'='*80}\n")
    
    total_files = len(results)
    successful = sum(1 for r in results if r.get('success'))
    failed = total_files - successful
    
    total_duration = sum(r.get('duration_seconds', 0) for r in results if r.get('success'))
    total_tokens = sum(r.get('usage', {}).get('total_tokens', 0) for r in results if r.get('success'))
    total_segments = sum(r.get('segments_count', 0) for r in results if r.get('success'))
    total_chunks = sum(r.get('chunks_processed', 0) for r in results if r.get('success'))
    
    print(f"Total files processed: {total_files}")
    print(f"  ✓ Successful: {successful}")
    print(f"  ✗ Failed: {failed}")
    print()
    
    if successful > 0:
        print(f"Total processing time: {total_duration:.2f} seconds ({total_duration/60:.1f} minutes)")
        print(f"Average time per file: {total_duration/successful:.2f} seconds")
        print(f"Total tokens used: {total_tokens:,}")
        print(f"Average tokens per file: {total_tokens//successful:,}")
        print(f"Total segments: {total_segments:,}")
        print(f"Total chunks processed: {total_chunks}")
        print()
    
    print("Individual Results:")
    print("-" * 80)
    for result in results:
        if result.get('success'):
            print(f"\n✓ {result['audio_file']}")
            print(f"  Audio duration: {result.get('audio_duration_seconds', 0)/60:.1f} minutes")
            print(f"  Processing time: {result['duration_seconds']:.2f}s")
            print(f"  Chunks: {result.get('chunks_processed', 1)}")
            print(f"  Tokens: {result['usage']['total_tokens']:,} (Input: {result['usage']['input_tokens']:,}, Output: {result['usage']['output_tokens']:,})")
            print(f"  Audio tokens: {result['usage']['audio_tokens']:,}")
            print(f"  Segments: {result['segments_count']}")
            print(f"  JSON: {result['json_output']}")
            print(f"  Text: {result['text_output']}")
        else:
            print(f"\n✗ {result['audio_file']}")
            print(f"  Error: {result.get('error', 'Unknown error')}")
    
    print(f"\n{'='*80}\n")


def main():
    """Main processing function"""
    try:
        # Check for ffmpeg/ffprobe
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("\n✗ Error: ffmpeg and ffprobe are required for audio splitting")
            print("  Install with: brew install ffmpeg")
            return 1
        
        # Process all depositions
        results = process_all_depositions()
        
        # Print summary
        print_summary(results)
        
        # Return success if at least one file processed successfully
        return 0 if any(r.get('success') for r in results) else 1
        
    except Exception as e:
        print(f"\n✗ Fatal Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
