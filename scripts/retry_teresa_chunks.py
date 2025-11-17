#!/usr/bin/env python3
"""
Retry specific chunks for Teresa Peters deposition
"""
import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load East US 2 credentials
load_dotenv('.env.eastus2')

AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT_EASTUS2')
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY_EASTUS2')
AZURE_OPENAI_DEPLOYMENT = os.getenv('MODEL_DEPLOYMENT_NAME_EASTUS2')
AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION_EASTUS2')

# Configuration
MAX_RETRIES = 5  # Increased retries for stubborn chunks
RETRY_DELAY = 45  # Longer delay between retries
DELAY_BETWEEN_CHUNKS = 15  # Longer delay between chunks
REQUEST_TIMEOUT = 300  # 5-minute timeout

def transcribe_chunk(chunk_path: Path, attempt: int = 1) -> dict:
    """Transcribe a single chunk with retry logic"""
    url = f"{AZURE_OPENAI_ENDPOINT}openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/audio/transcriptions?api-version={AZURE_OPENAI_API_VERSION}"
    
    headers = {
        "api-key": AZURE_OPENAI_API_KEY
    }
    
    with open(chunk_path, "rb") as audio_file:
        files = {
            "file": (chunk_path.name, audio_file, "audio/mpeg")
        }
        data = {
            "model": AZURE_OPENAI_DEPLOYMENT,
            "response_format": "diarized_json",
            "chunking_strategy": "auto",
            "language": "en",
            "temperature": "0"
        }
        
        try:
            start_time = time.time()
            response = requests.post(
                url, 
                headers=headers, 
                files=files, 
                data=data,
                timeout=REQUEST_TIMEOUT
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "data": result,
                    "elapsed": elapsed
                }
            elif response.status_code == 500:
                if attempt < MAX_RETRIES:
                    print(f"  ⚠ Server error (attempt {attempt}/{MAX_RETRIES}), retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                    return transcribe_chunk(chunk_path, attempt + 1)
                else:
                    return {
                        "success": False,
                        "error": response.json(),
                        "status_code": 500
                    }
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }
        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"  ⚠ Exception (attempt {attempt}/{MAX_RETRIES}): {str(e)}, retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                return transcribe_chunk(chunk_path, attempt + 1)
            else:
                return {
                    "success": False,
                    "error": str(e)
                }

def main():
    # Load existing Teresa Peters JSON
    existing_file = Path("output/depositions_eastus2/Teresa Peters mp3.json")
    with open(existing_file, 'r') as f:
        existing_data = json.load(f)
    
    print("\nRetrying missing chunks for Teresa Peters deposition")
    print("=" * 60)
    
    # Chunks to retry
    chunks_to_retry = [
        ("depositions/Peters, Teresa 12132021/chunks_5min_eastus2/Teresa Peters mp3_chunk03.mp3", 3),
        ("depositions/Peters, Teresa 12132021/chunks_5min_eastus2/Teresa Peters mp3_chunk04.mp3", 4)
    ]
    
    new_chunks = []
    
    for chunk_path, chunk_num in chunks_to_retry:
        chunk_file = Path(chunk_path)
        
        if not chunk_file.exists():
            print(f"\n  ✗ Chunk file not found: {chunk_path}")
            continue
        
        print(f"\n  Transcribing chunk {chunk_num}/5: {chunk_file.name}...")
        result = transcribe_chunk(chunk_file)
        
        if result["success"]:
            data = result["data"]
            
            # Calculate statistics
            total_tokens = data.get("usage", {}).get("total_tokens", 0)
            num_segments = len(data.get("segments", []))
            
            print(f"  ✓ Done in {result['elapsed']:.1f}s - Tokens: {total_tokens:,}, Segments: {num_segments}")
            
            new_chunks.append({
                "chunk_number": chunk_num,
                "text": data.get("text", ""),
                "segments": data.get("segments", []),
                "usage": data.get("usage", {})
            })
            
            # Wait before next chunk
            if chunk_num < 4:
                print(f"  → Waiting {DELAY_BETWEEN_CHUNKS}s before next chunk...")
                time.sleep(DELAY_BETWEEN_CHUNKS)
        else:
            print(f"  ✗ Error {result.get('status_code', 'unknown')} after {MAX_RETRIES} attempts: {json.dumps(result.get('error'), indent=2)}")
    
    if new_chunks:
        # Insert new chunks in the correct position
        all_chunks = existing_data["chunks"] + new_chunks
        all_chunks.sort(key=lambda x: x.get("chunk_number", 0))
        
        # Save updated file
        output_data = {"chunks": all_chunks}
        with open(existing_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n  ✓ Updated {existing_file}")
        print(f"  → Total chunks now: {len(all_chunks)}")
        
        # Calculate totals
        total_tokens = sum(c.get("usage", {}).get("total_tokens", 0) for c in all_chunks)
        total_segments = sum(len(c.get("segments", [])) for c in all_chunks)
        print(f"  → Total tokens: {total_tokens:,}")
        print(f"  → Total segments: {total_segments}")
    else:
        print("\n  ✗ No chunks were successfully processed")

if __name__ == "__main__":
    main()
