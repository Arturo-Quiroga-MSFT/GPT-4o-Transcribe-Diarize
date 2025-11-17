#!/usr/bin/env python3
"""Quick test to verify East US 2 API is responding"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load East US 2 environment variables
load_dotenv('.env.eastus2')

def test_api():
    """Test with the small 5-minute audio file"""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT_EASTUS2")
    api_key = os.getenv("AZURE_OPENAI_API_KEY_EASTUS2")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION_EASTUS2")
    model = os.getenv("MODEL_DEPLOYMENT_NAME_EASTUS2")
    
    url = f"{endpoint}openai/deployments/{model}/audio/transcriptions?api-version={api_version}"
    
    print("Testing East US 2 deployment with small audio file (teresa_5min.mp3)...")
    print(f"Endpoint: {url}")
    print(f"Region: East US 2")
    print()
    
    headers = {"api-key": api_key}
    audio_file = "test_audio/teresa_5min.mp3"
    
    with open(audio_file, 'rb') as f:
        files = {'file': (Path(audio_file).name, f, 'audio/mpeg')}
        data = {
            'model': model,
            'response_format': 'diarized_json',
            'chunking_strategy': 'auto',
            'language': 'en',
            'temperature': '0'
        }
        
        print("Sending request (timeout: 120s)...")
        response = requests.post(url, headers=headers, files=files, data=data, timeout=120)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            segments = len(result.get('segments', []))
            tokens = result.get('usage', {}).get('total_tokens', 0)
            print(f"✓ Success! Segments: {segments}, Tokens: {tokens:,}")
            print(f"\n✓ East US 2 deployment is working correctly!")
        else:
            print(f"✗ Error: {response.text}")

if __name__ == "__main__":
    test_api()
