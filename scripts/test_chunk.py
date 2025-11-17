#!/usr/bin/env python3
"""Quick test to verify API is responding"""

import os
import requests
from pathlib import Path
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

def test_api():
    """Test with the small 5-minute audio file"""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
    model = "gpt-4o-transcribe-diarize"
    
    url = f"{endpoint}openai/deployments/{model}/audio/transcriptions?api-version={api_version}"
    
    print("Testing with small audio file (teresa_5min.mp3)...")
    print(f"Endpoint: {url}")
    
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    headers = {"Authorization": f"Bearer {token.token}"}
    
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
        else:
            print(f"✗ Error: {response.text}")

if __name__ == "__main__":
    test_api()
