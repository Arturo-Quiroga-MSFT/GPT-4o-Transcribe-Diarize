#!/usr/bin/env python3
"""
Generate human-readable text transcripts from JSON outputs
"""
import json
from pathlib import Path
from datetime import timedelta

def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    minutes = total_seconds // 60
    secs = total_seconds % 60
    return f"{minutes:02d}:{secs:02d}"

def generate_text_transcript(json_path: Path, output_path: Path):
    """Generate a formatted text transcript from JSON"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    chunks = data.get("chunks", [])
    
    # Collect statistics
    total_tokens = 0
    total_segments = 0
    speakers = set()
    
    with open(output_path, 'w') as out:
        # Write header
        out.write("=" * 80 + "\n")
        out.write(f"TRANSCRIPT: {json_path.stem}\n")
        out.write("=" * 80 + "\n\n")
        
        # Process each chunk
        for i, chunk in enumerate(chunks, 1):
            chunk_num = chunk.get("chunk_number", i)
            segments = chunk.get("segments", [])
            usage = chunk.get("usage", {})
            
            total_tokens += usage.get("total_tokens", 0)
            total_segments += len(segments)
            
            out.write(f"--- Chunk {chunk_num} ---\n\n")
            
            # Write segments with speaker labels and timestamps
            for seg in segments:
                speaker = seg.get("speaker", "?")
                speakers.add(speaker)
                text = seg.get("text", "").strip()
                start = seg.get("start", 0)
                timestamp = format_timestamp(start)
                
                out.write(f"[{timestamp}] Speaker {speaker}: {text}\n")
            
            out.write("\n")
        
        # Write footer with statistics
        out.write("=" * 80 + "\n")
        out.write(f"STATISTICS\n")
        out.write("=" * 80 + "\n")
        out.write(f"Total Chunks: {len(chunks)}\n")
        out.write(f"Total Segments: {total_segments:,}\n")
        out.write(f"Total Tokens: {total_tokens:,}\n")
        out.write(f"Speakers Identified: {len(speakers)} ({', '.join(sorted(speakers))})\n")
        
        if len(chunks) > 0:
            last_chunk = chunks[-1]
            last_segments = last_chunk.get("segments", [])
            if last_segments:
                last_timestamp = last_segments[-1].get("end", 0)
                out.write(f"Duration: {format_timestamp(last_timestamp)} ({last_timestamp:.1f}s)\n")
        
        out.write("=" * 80 + "\n")
    
    return {
        "chunks": len(chunks),
        "segments": total_segments,
        "tokens": total_tokens,
        "speakers": len(speakers)
    }

def main():
    output_dir = Path("output/depositions_eastus2")
    text_output_dir = output_dir / "text_transcripts"
    text_output_dir.mkdir(exist_ok=True)
    
    print("\n" + "=" * 80)
    print("Generating Text Transcripts from JSON")
    print("=" * 80 + "\n")
    
    json_files = list(output_dir.glob("*.json"))
    
    for json_file in json_files:
        print(f"Processing: {json_file.name}")
        
        text_file = text_output_dir / f"{json_file.stem}.txt"
        stats = generate_text_transcript(json_file, text_file)
        
        print(f"  ✓ Generated: {text_file.name}")
        print(f"    → Chunks: {stats['chunks']}, Segments: {stats['segments']:,}, "
              f"Tokens: {stats['tokens']:,}, Speakers: {stats['speakers']}")
        print()
    
    print("=" * 80)
    print(f"All text transcripts saved to: {text_output_dir}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
