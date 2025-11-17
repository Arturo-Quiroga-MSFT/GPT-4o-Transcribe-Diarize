#!/usr/bin/env python3
"""
Quick processing script with smaller chunks (10 minutes) for faster processing
"""

import os
import sys
import json
import requests
import subprocess
from datetime import datetime
from pathlib import Path
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

CHUNK_DURATION = 600  # 10 minutes

def get_duration(file):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file]
    return float(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip())

def split_audio(audio_file, chunk_dur=CHUNK_DURATION):
    duration = get_duration(audio_file)
    if duration <= chunk_dur:
        return [audio_file]
    
    output_dir = Path(audio_file).parent / "chunks_10min"
    output_dir.mkdir(exist_ok=True)
    base = Path(audio_file).stem
    num = int((duration / chunk_dur) + 1)
    chunks = []
    
    for i in range(num):
        chunk_file = output_dir / f"{base}_chunk{i+1:02d}.mp3"
        cmd = ['ffmpeg', '-i', audio_file, '-ss', str(i * chunk_dur), '-t', str(chunk_dur), '-acodec', 'copy', '-y', str(chunk_file)]
        subprocess.run(cmd, capture_output=True)
        chunks.append(str(chunk_file))
        print(f"  Created chunk {i+1}/{num}: {chunk_file.name}")
    
    return chunks

def transcribe(audio_file):
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
    url = f"{endpoint}openai/deployments/gpt-4o-transcribe-diarize/audio/transcriptions?api-version={api_version}"
    
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    headers = {"Authorization": f"Bearer {token.token}"}
    
    print(f"  Transcribing {Path(audio_file).name}...")
    start = datetime.now()
    
    with open(audio_file, 'rb') as f:
        files = {'file': (Path(audio_file).name, f, 'audio/mpeg')}
        data = {'model': 'gpt-4o-transcribe-diarize', 'response_format': 'diarized_json', 'chunking_strategy': 'auto', 'language': 'en', 'temperature': '0'}
        response = requests.post(url, headers=headers, files=files, data=data, timeout=300)
    
    if response.status_code != 200:
        print(f"  ✗ Error {response.status_code}: {response.text}")
        return None
    
    duration = (datetime.now() - start).total_seconds()
    result = response.json()
    usage = result.get('usage', {})
    
    print(f"  ✓ Done in {duration:.1f}s - Tokens: {usage.get('total_tokens', 0):,}, Segments: {len(result.get('segments', []))}")
    return result

def main():
    dep_dir = Path("depositions")
    audio_files = list(dep_dir.rglob("*.mp3"))
    
    print(f"\nProcessing {len(audio_files)} files with 10-minute chunks\n")
    
    for audio_file in audio_files:
        print(f"\n{audio_file.name}")
        print("-" * 60)
        
        chunks = split_audio(str(audio_file))
        print(f"  Split into {len(chunks)} chunk(s)")
        
        all_results = []
        for chunk in chunks:
            result = transcribe(chunk)
            if result:
                all_results.append(result)
        
        if all_results:
            # Save merged result
            output_dir = Path("output/depositions_10min")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{Path(audio_file).stem}.json"
            
            with open(output_file, 'w') as f:
                json.dump({"chunks": all_results}, f, indent=2)
            
            print(f"  ✓ Saved to {output_file}")

if __name__ == "__main__":
    main()
