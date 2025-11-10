#!/usr/bin/env python3
"""
Comprehensive parameter testing script for gpt-4o-transcribe-diarize
Tests various parameter combinations systematically and generates comparison reports
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ParameterTester:
    """Class to systematically test different parameter combinations"""
    
    def __init__(self, audio_file_path: str, model: str = "gpt-4o-transcribe-diarize", 
                 use_entra_id: bool = False):
        """
        Initialize parameter tester
        
        Args:
            audio_file_path: Path to audio file for testing
            model: Model deployment name
            use_entra_id: Use Entra ID authentication
        """
        self.audio_file_path = audio_file_path
        self.model = model
        self.use_entra_id = use_entra_id
        self.prompts_supported = "diarize" not in model.lower()
        self.chunking_strategy = "auto"
        self.client = self._setup_client()
        self.results: List[Dict[str, Any]] = []
        
    def _setup_client(self) -> AzureOpenAI:
        """Setup Azure OpenAI client with appropriate authentication"""
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-03-01-preview")
        
        if not endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
        
        if self.use_entra_id:
            print("Using Microsoft Entra ID authentication...")
            credential = DefaultAzureCredential()
            token = credential.get_token("https://cognitiveservices.azure.com/.default")
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_version=api_version,
                azure_ad_token=token.token
            )
        else:
            print("Using API key authentication...")
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            if not api_key:
                raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_version=api_version,
                api_key=api_key
            )
        
        return client
    
    def test_temperature_variations(self, temperatures: List[float] = None) -> None:
        """
        Test different temperature values
        
        Args:
            temperatures: List of temperature values to test
        """
        if temperatures is None:
            temperatures = [0.0, 0.3, 0.5, 0.7, 1.0]
        
        print(f"\n{'='*60}")
        print(f"Testing Temperature Variations")
        print(f"{'='*60}\n")
        
        with open(self.audio_file_path, 'rb') as audio:
            for temp in temperatures:
                print(f"Testing temperature: {temp}")
                start_time = datetime.now()
                
                try:
                    result = self.client.audio.transcriptions.create(
                        file=audio,
                        model=self.model,
                        temperature=temp,
                        response_format="json",
                        timestamp_granularities=["segment"],
                        chunking_strategy=self.chunking_strategy
                    )
                    
                    duration = (datetime.now() - start_time).total_seconds()
                    
                    self.results.append({
                        "test_type": "temperature",
                        "parameter": "temperature",
                        "value": temp,
                        "duration_seconds": duration,
                        "timestamp": start_time.isoformat(),
                        "text": result.text,
                        "segment_count": len(result.segments) if hasattr(result, 'segments') else 0,
                        "success": True
                    })
                    
                    print(f"  ✓ Completed in {duration:.2f}s")
                    print(f"  Text length: {len(result.text)} chars")
                    if hasattr(result, 'segments'):
                        print(f"  Segments: {len(result.segments)}")
                    
                except Exception as e:
                    print(f"  ✗ Error: {str(e)}")
                    self.results.append({
                        "test_type": "temperature",
                        "parameter": "temperature",
                        "value": temp,
                        "timestamp": start_time.isoformat(),
                        "error": str(e),
                        "success": False
                    })
                
                # Reset file pointer for next iteration
                audio.seek(0)
    
    def test_language_detection(self, languages: List[Optional[str]] = None) -> None:
        """
        Test explicit language vs auto-detection
        
        Args:
            languages: List of language codes to test (None means auto-detect)
        """
        if languages is None:
            languages = [None, "en", "es", "fr", "de"]
        
        print(f"\n{'='*60}")
        print(f"Testing Language Settings")
        print(f"{'='*60}\n")
        
        with open(self.audio_file_path, 'rb') as audio:
            for lang in languages:
                lang_label = lang if lang else "auto-detect"
                print(f"Testing language: {lang_label}")
                start_time = datetime.now()
                
                try:
                    kwargs = {
                        "file": audio,
                        "model": self.model,
                        "response_format": "json",
                        "timestamp_granularities": ["segment"],
                        "chunking_strategy": self.chunking_strategy
                    }
                    if lang:
                        kwargs["language"] = lang
                    
                    result = self.client.audio.transcriptions.create(**kwargs)
                    duration = (datetime.now() - start_time).total_seconds()
                    
                    detected_language = getattr(result, 'language', 'unknown')
                    
                    self.results.append({
                        "test_type": "language",
                        "parameter": "language",
                        "value": lang_label,
                        "detected_language": detected_language,
                        "duration_seconds": duration,
                        "timestamp": start_time.isoformat(),
                        "text": result.text,
                        "success": True
                    })
                    
                    print(f"  ✓ Completed in {duration:.2f}s")
                    print(f"  Detected language: {detected_language}")
                    
                except Exception as e:
                    print(f"  ✗ Error: {str(e)}")
                    self.results.append({
                        "test_type": "language",
                        "parameter": "language",
                        "value": lang_label,
                        "timestamp": start_time.isoformat(),
                        "error": str(e),
                        "success": False
                    })
                
                audio.seek(0)
    
    def test_prompt_variations(self, prompts: List[Optional[str]] = None) -> None:
        """
        Test different prompt strategies
        
        Args:
            prompts: List of prompts to test
        """
        if prompts is None:
            prompts = [
                None,
                "This is a legal deposition.",
                "This is a formal legal proceeding. Please transcribe accurately with proper speaker attribution.",
                "Deposition testimony for litigation. Include technical legal terms correctly.",
                "Q&A format deposition with attorney and witness."
            ]
        
        if not self.prompts_supported:
            print("Prompt parameter not supported for this model; skipping prompt tests.")
            self.results.append({
                "test_type": "prompt",
                "parameter": "prompt",
                "value": "skipped",
                "timestamp": datetime.now().isoformat(),
                "error": "prompt unsupported for model",
                "success": False
            })
            return

        print(f"\n{'='*60}")
        print(f"Testing Prompt Variations")
        print(f"{'='*60}\n")
        
        with open(self.audio_file_path, 'rb') as audio:
            for i, prompt in enumerate(prompts):
                prompt_label = f"prompt_{i}" if prompt else "no_prompt"
                print(f"Testing: {prompt_label}")
                if prompt:
                    print(f"  Prompt: {prompt}")
                
                start_time = datetime.now()
                
                try:
                    kwargs = {
                        "file": audio,
                        "model": self.model,
                        "response_format": "json",
                        "timestamp_granularities": ["segment"],
                        "chunking_strategy": self.chunking_strategy
                    }
                    if prompt:
                        kwargs["prompt"] = prompt
                    
                    result = self.client.audio.transcriptions.create(**kwargs)
                    duration = (datetime.now() - start_time).total_seconds()
                    
                    self.results.append({
                        "test_type": "prompt",
                        "parameter": "prompt",
                        "value": prompt_label,
                        "prompt_text": prompt,
                        "duration_seconds": duration,
                        "timestamp": start_time.isoformat(),
                        "text": result.text,
                        "segment_count": len(result.segments) if hasattr(result, 'segments') else 0,
                        "success": True
                    })
                    
                    print(f"  ✓ Completed in {duration:.2f}s")
                    
                except Exception as e:
                    print(f"  ✗ Error: {str(e)}")
                    self.results.append({
                        "test_type": "prompt",
                        "parameter": "prompt",
                        "value": prompt_label,
                        "prompt_text": prompt,
                        "timestamp": start_time.isoformat(),
                        "error": str(e),
                        "success": False
                    })
                
                audio.seek(0)
    
    def test_response_formats(self, formats: List[str] = None) -> None:
        """
        Test different response formats
        
        Args:
            formats: List of response formats to test
        """
        if formats is None:
            formats = ["json", "text", "srt", "vtt"]
        
        print(f"\n{'='*60}")
        print(f"Testing Response Formats")
        print(f"{'='*60}\n")
        
        with open(self.audio_file_path, 'rb') as audio:
            for fmt in formats:
                print(f"Testing format: {fmt}")
                start_time = datetime.now()
                
                try:
                    result = self.client.audio.transcriptions.create(
                        file=audio,
                        model=self.model,
                        response_format=fmt,
                        chunking_strategy=self.chunking_strategy
                    )
                    
                    duration = (datetime.now() - start_time).total_seconds()
                    
                    # Handle different response types
                    if fmt in ["json", "verbose_json"]:
                        text = result.text
                        has_segments = hasattr(result, 'segments')
                    else:
                        text = str(result)
                        has_segments = False
                    
                    self.results.append({
                        "test_type": "response_format",
                        "parameter": "response_format",
                        "value": fmt,
                        "duration_seconds": duration,
                        "timestamp": start_time.isoformat(),
                        "text_length": len(text),
                        "has_segments": has_segments,
                        "success": True
                    })
                    
                    print(f"  ✓ Completed in {duration:.2f}s")
                    print(f"  Text length: {len(text)} chars")
                    
                except Exception as e:
                    print(f"  ✗ Error: {str(e)}")
                    self.results.append({
                        "test_type": "response_format",
                        "parameter": "response_format",
                        "value": fmt,
                        "timestamp": start_time.isoformat(),
                        "error": str(e),
                        "success": False
                    })
                
                audio.seek(0)
    
    def test_timestamp_granularities(self) -> None:
        """Test different timestamp granularity combinations"""
        
        granularity_configs = [
            (["segment"], "segment_only"),
            (["word"], "word_only"),
            (["word", "segment"], "word_and_segment")
        ]
        
        print(f"\n{'='*60}")
        print(f"Testing Timestamp Granularities")
        print(f"{'='*60}\n")
        
        with open(self.audio_file_path, 'rb') as audio:
            for granularities, label in granularity_configs:
                print(f"Testing: {label}")
                start_time = datetime.now()
                
                try:
                    result = self.client.audio.transcriptions.create(
                        file=audio,
                        model=self.model,
                        response_format="json",
                        timestamp_granularities=granularities,
                        chunking_strategy=self.chunking_strategy
                    )
                    
                    duration = (datetime.now() - start_time).total_seconds()
                    
                    has_words = hasattr(result, 'words') and result.words
                    has_segments = hasattr(result, 'segments') and result.segments
                    word_count = len(result.words) if has_words else 0
                    segment_count = len(result.segments) if has_segments else 0
                    
                    self.results.append({
                        "test_type": "timestamp_granularity",
                        "parameter": "timestamp_granularities",
                        "value": label,
                        "granularities": granularities,
                        "duration_seconds": duration,
                        "timestamp": start_time.isoformat(),
                        "has_words": has_words,
                        "has_segments": has_segments,
                        "word_count": word_count,
                        "segment_count": segment_count,
                        "success": True
                    })
                    
                    print(f"  ✓ Completed in {duration:.2f}s")
                    print(f"  Words: {word_count}, Segments: {segment_count}")
                    
                except Exception as e:
                    print(f"  ✗ Error: {str(e)}")
                    self.results.append({
                        "test_type": "timestamp_granularity",
                        "parameter": "timestamp_granularities",
                        "value": label,
                        "granularities": granularities,
                        "timestamp": start_time.isoformat(),
                        "error": str(e),
                        "success": False
                    })
                
                audio.seek(0)
    
    def generate_report(self, output_dir: str = "output") -> str:
        """
        Generate comprehensive test report
        
        Args:
            output_dir: Directory to save report
        
        Returns:
            Path to report file
        """
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(output_dir, f"parameter_test_report_{timestamp}.json")
        
        # Calculate statistics
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.get('success', False))
        failed_tests = total_tests - successful_tests
        
        # Group by test type
        test_types = {}
        for result in self.results:
            test_type = result.get('test_type', 'unknown')
            if test_type not in test_types:
                test_types[test_type] = []
            test_types[test_type].append(result)
        
        # Calculate average durations
        avg_durations = {}
        for test_type, results in test_types.items():
            durations = [r.get('duration_seconds', 0) for r in results if r.get('success', False)]
            if durations:
                avg_durations[test_type] = sum(durations) / len(durations)
        
        report = {
            "summary": {
                "audio_file": self.audio_file_path,
                "model": self.model,
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": f"{(successful_tests/total_tests)*100:.2f}%" if total_tests > 0 else "0%",
                "test_date": timestamp,
                "average_durations": avg_durations
            },
            "results_by_type": test_types,
            "all_results": self.results
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print("TEST REPORT SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {report['summary']['success_rate']}")
        print(f"\nAverage Durations by Test Type:")
        for test_type, avg_duration in avg_durations.items():
            print(f"  {test_type}: {avg_duration:.2f}s")
        print(f"\n✓ Full report saved to: {report_file}")
        print(f"{'='*60}\n")
        
        return report_file


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive parameter testing for gpt-4o-transcribe-diarize"
    )
    parser.add_argument(
        "--audio",
        type=str,
        required=True,
        help="Path to audio file for testing"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-transcribe-diarize",
        help="Model deployment name"
    )
    parser.add_argument(
        "--use-entra-id",
        action="store_true",
        help="Use Microsoft Entra ID authentication"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Output directory for reports"
    )
    parser.add_argument(
        "--test-temperature",
        action="store_true",
        help="Test temperature variations"
    )
    parser.add_argument(
        "--test-language",
        action="store_true",
        help="Test language detection and settings"
    )
    parser.add_argument(
        "--test-prompt",
        action="store_true",
        help="Test different prompt strategies"
    )
    parser.add_argument(
        "--test-format",
        action="store_true",
        help="Test different response formats"
    )
    parser.add_argument(
        "--test-timestamps",
        action="store_true",
        help="Test timestamp granularities"
    )
    parser.add_argument(
        "--test-all",
        action="store_true",
        help="Run all tests"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize tester
        tester = ParameterTester(
            audio_file_path=args.audio,
            model=args.model,
            use_entra_id=args.use_entra_id
        )
        
        print(f"\n{'='*60}")
        print("PARAMETER TESTING SUITE")
        print(f"{'='*60}")
        print(f"Audio File: {args.audio}")
        print(f"Model: {args.model}")
        print(f"{'='*60}\n")
        
        # Run selected tests
        if args.test_all or args.test_temperature:
            tester.test_temperature_variations()
        
        if args.test_all or args.test_language:
            tester.test_language_detection()
        
        if args.test_all or args.test_prompt:
            tester.test_prompt_variations()
        
        if args.test_all or args.test_format:
            tester.test_response_formats()
        
        if args.test_all or args.test_timestamps:
            tester.test_timestamp_granularities()
        
        # Generate report
        if tester.results:
            tester.generate_report(output_dir=args.output_dir)
            print("\n✓ All tests completed successfully!")
        else:
            print("\n⚠ No tests were run. Use --test-all or specific --test-* flags")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
