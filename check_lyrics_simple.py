#!/usr/bin/env python3
"""
Simple script to check lyrics in audio files
"""

import sys
import mutagen
from pathlib import Path

def check_lyrics_in_file(filepath):
    """Check what lyrics data exists in an audio file"""
    print(f"Checking: {filepath}")
    print("=" * 50)
    
    try:
        audio = mutagen.File(str(filepath))
        if not audio:
            print("ERROR: Could not read audio file")
            return
        
        print(f"Format: {type(audio).__name__}")
        
        lyrics_found = False
        
        # Check for lyrics field (FLAC/OGG)
        if 'lyrics' in audio:
            lyrics = audio['lyrics'][0] if isinstance(audio['lyrics'], list) else audio['lyrics']
            print(f"FOUND LYRICS: {len(lyrics)} characters")
            print(f"Preview: {lyrics[:200]}...")
            lyrics_found = True
        
        # Check for LYRICS field
        if 'LYRICS' in audio:
            lyrics = audio['LYRICS'][0] if isinstance(audio['LYRICS'], list) else audio['LYRICS']
            print(f"FOUND LYRICS (uppercase): {len(lyrics)} characters")
            lyrics_found = True
        
        # Check ID3 USLT tags
        if hasattr(audio, 'tags') and audio.tags:
            for frame in audio.tags.values():
                if hasattr(frame, 'FrameID') and frame.FrameID == 'USLT':
                    print(f"FOUND ID3 LYRICS: {len(frame.text)} characters")
                    print(f"Preview: {frame.text[:200]}...")
                    lyrics_found = True
        
        # List all fields
        print("\nAll fields in file:")
        if hasattr(audio, 'keys'):
            for key in sorted(audio.keys()):
                value = audio[key]
                if isinstance(value, list) and value:
                    value = value[0]
                print(f"  {key}: {str(value)[:50]}...")
        
        if not lyrics_found:
            print("NO LYRICS FOUND")
        else:
            print("SUCCESS: Lyrics data found!")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_lyrics_in_file(sys.argv[1])
    else:
        # Look for FLAC files in current directory
        for flac_file in Path(".").glob("*.flac"):
            check_lyrics_in_file(str(flac_file))
            print()  # Empty line between files