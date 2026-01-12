#!/usr/bin/env python3
"""
Retry only chunk 4 for Teresa Peters with aggressive retry strategy
"""
import os
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

# Aggressive configuration for stubborn chunk
MAX_RETRIES = 10
RETRY_DELAY = 60  # 1 minute between retries
REQUEST_TIMEOUT = 300

def transcribe_chunk(chunk_path: Path, attempt: int = 1) -> dict:
    """Transcribe chunk 4 with very aggressive retry logic"""
    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/audio/transcriptions?api-version={AZURE_OPENAI_API_VERSION}"
    
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
            print(f"  → Attempt {attempt}/{MAX_RETRIES} at {time.strftime('%H:%M:%S')}")
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
                    "elapsed": elapsed,
                    "attempt": attempt
                }
            elif response.status_code == 500:
                if attempt < MAX_RETRIES:
                    print(f"  ⚠ Server error (attempt {attempt}/{MAX_RETRIES}), waiting {RETRY_DELAY}s before retry...")
                    time.sleep(RETRY_DELAY)
                    return transcribe_chunk(chunk_path, attempt + 1)
                else:
                    return {
                        "success": False,
                        "error": response.json(),
                        "status_code": 500,
                        "attempt": attempt
                    }
            else:
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code,
                    "attempt": attempt
                }
        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"  ⚠ Exception (attempt {attempt}/{MAX_RETRIES}): {str(e)}, waiting {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                return transcribe_chunk(chunk_path, attempt + 1)
            else:
                return {
                    "success": False,
                    "error": str(e),
                    "attempt": attempt
                }

def main():
    print("\n" + "="*60)
    print("Retrying Teresa Peters Chunk 4 with aggressive retry logic")
    print("="*60)
    
    chunk_path = Path("depositions/Peters, Teresa 12132021/chunks_5min_eastus2/Teresa Peters mp3_chunk04.mp3")
    
    if not chunk_path.exists():
        print(f"\n✗ Chunk file not found: {chunk_path}")
        return
    
    print(f"\nChunk: {chunk_path.name}")
    print(f"Max retries: {MAX_RETRIES}")
    print(f"Retry delay: {RETRY_DELAY}s")
    print(f"Timeout: {REQUEST_TIMEOUT}s")
    print("\nStarting transcription...\n")
    
    result = transcribe_chunk(chunk_path)
    
    if result["success"]:
        data = result["data"]
        total_tokens = data.get("usage", {}).get("total_tokens", 0)
        num_segments = len(data.get("segments", []))
        
        print(f"\n✓ SUCCESS after {result['attempt']} attempts!")
        print(f"  Time: {result['elapsed']:.1f}s")
        print(f"  Tokens: {total_tokens:,}")
        print(f"  Segments: {num_segments}")
        
        # Load existing file and add chunk 4
        existing_file = Path("output/depositions_eastus2/Teresa Peters mp3.json")
        with open(existing_file, 'r') as f:
            existing_data = json.load(f)
        
        # Add chunk 4
        chunk4_data = {
            "chunk_number": 4,
            "text": data.get("text", ""),
            "segments": data.get("segments", []),
            "usage": data.get("usage", {})
        }
        
        all_chunks = existing_data["chunks"] + [chunk4_data]
        all_chunks.sort(key=lambda x: x.get("chunk_number", 0))
        
        # Save
        output_data = {"chunks": all_chunks}
        with open(existing_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n✓ Updated {existing_file}")
        
        # Final statistics
        total_tokens = sum(c.get("usage", {}).get("total_tokens", 0) for c in all_chunks)
        total_segments = sum(len(c.get("segments", [])) for c in all_chunks)
        print(f"  → Total chunks: 5/5 (COMPLETE!)")
        print(f"  → Total tokens: {total_tokens:,}")
        print(f"  → Total segments: {total_segments}")
    else:
        print(f"\n✗ FAILED after {result.get('attempt', 0)} attempts")
        print(f"  Error: {json.dumps(result.get('error'), indent=2)}")
        print("\nYou may want to try again later or wait a few minutes before retrying.")

if __name__ == "__main__":
    main()
