#!/usr/bin/env python3
"""
Process deposition audio files using East US 2 deployment with 5-minute chunks
"""

import os
import sys
import json
import requests
import subprocess
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load East US 2 environment variables
load_dotenv('.env.eastus2')

CHUNK_DURATION = 300  # 5 minutes
MAX_RETRIES = 3
RETRY_DELAY = 30  # seconds
DELAY_BETWEEN_CHUNKS = 10  # seconds - prevent rate limiting

def get_duration(file):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file]
    return float(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip())

def split_audio(audio_file, chunk_dur=CHUNK_DURATION):
    duration = get_duration(audio_file)
    if duration <= chunk_dur:
        return [audio_file]
    
    output_dir = Path(audio_file).parent / "chunks_5min_eastus2"
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
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT_EASTUS2")
    api_key = os.getenv("AZURE_OPENAI_API_KEY_EASTUS2")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION_EASTUS2")
    model = os.getenv("MODEL_DEPLOYMENT_NAME_EASTUS2")
    
    url = f"{endpoint}openai/deployments/{model}/audio/transcriptions?api-version={api_version}"
    headers = {"api-key": api_key}
    
    print(f"  Transcribing {Path(audio_file).name}...")
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            start = datetime.now()
            
            with open(audio_file, 'rb') as f:
                files = {'file': (Path(audio_file).name, f, 'audio/mpeg')}
                data = {
                    'model': model,
                    'response_format': 'diarized_json',
                    'chunking_strategy': 'auto',
                    'language': 'en',
                    'temperature': '0'
                }
                response = requests.post(url, headers=headers, files=files, data=data, timeout=300)
            
            if response.status_code == 500:
                if attempt < MAX_RETRIES:
                    print(f"  ⚠ Server error (attempt {attempt}/{MAX_RETRIES}), retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    print(f"  ✗ Error 500 after {MAX_RETRIES} attempts: {response.text}")
                    return None
            
            if response.status_code != 200:
                print(f"  ✗ Error {response.status_code}: {response.text}")
                return None
            
            duration = (datetime.now() - start).total_seconds()
            result = response.json()
            usage = result.get('usage', {})
            
            print(f"  ✓ Done in {duration:.1f}s - Tokens: {usage.get('total_tokens', 0):,}, Segments: {len(result.get('segments', []))}")
            return result
            
        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"  ⚠ Error: {e}, retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                print(f"  ✗ Failed after {MAX_RETRIES} attempts: {e}")
                return None
    
    return None

def main():
    dep_dir = Path("depositions")
    all_audio_files = list(dep_dir.rglob("*.mp3"))
    
    # Filter out files in 'chunks' directories and files with '_chunk' in name
    audio_files = [
        f for f in all_audio_files 
        if 'chunk' not in str(f).lower()
    ]
    
    print(f"\nProcessing {len(audio_files)} files with 5-minute chunks (East US 2)\n")
    
    for audio_file in audio_files:
        print(f"\n{audio_file.name}")
        print("-" * 60)
        
        chunks = split_audio(str(audio_file))
        print(f"  Split into {len(chunks)} chunk(s)")
        
        all_results = []
        for i, chunk in enumerate(chunks):
            result = transcribe(chunk)
            if result:
                all_results.append(result)
            
            # Add delay between chunks to avoid rate limiting (except after last chunk)
            if i < len(chunks) - 1 and result:
                print(f"  → Waiting {DELAY_BETWEEN_CHUNKS}s before next chunk...")
                time.sleep(DELAY_BETWEEN_CHUNKS)
        
        if all_results:
            # Save merged result
            output_dir = Path("output/depositions_eastus2")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{Path(audio_file).stem}.json"
            
            with open(output_file, 'w') as f:
                json.dump({"chunks": all_results}, f, indent=2)
            
            print(f"  ✓ Saved to {output_file}")

if __name__ == "__main__":
    main()
