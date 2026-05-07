from faster_whisper import WhisperModel
import json
import os

def transcribe(audio_path: str, video_id: str, model_size: str = "small") -> dict:
    """Transcribe audio file with timestamped segments."""
    
    print(f"Loading Whisper model ({model_size})...")
    model = WhisperModel(model_size, device="auto", compute_type="int8")
    
    print(f"Transcribing {audio_path}...")
    # vad_filter=True silently skipped ads, condition_on_previous_text drifted across ad boundaries
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        vad_filter=False,
        word_timestamps=False,
        condition_on_previous_text=False,
    )
    
    chunks = []
    for seg in segments:
        chunks.append({
            'start': float(seg.start),
            'end': float(seg.end),
            'text': seg.text.strip()
        })
        print(f"  [{seg.start:6.1f} - {seg.end:6.1f}]  {seg.text.strip()[:80]}")
    
    return {
        'video_id': video_id,
        'duration_sec': info.duration,
        'language': info.language,
        'chunks': chunks
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Transcribe a video with faster-whisper.')
    parser.add_argument('filename', nargs='?', default='test_001.mp4',
                        help='MP4 filename inside data/videos/ (default: test_001.mp4)')
    parser.add_argument('--model', default='medium',
                        help='Whisper model size (default: medium)')
    args = parser.parse_args()

    stem = os.path.splitext(args.filename)[0]
    audio_path = os.path.join('data', 'videos', f'{stem}.wav')
    output_path = os.path.join('data', 'transcripts', f'{stem}.json')

    os.makedirs('data/transcripts', exist_ok=True)

    result = transcribe(audio_path, stem, model_size=args.model)

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\nDone. {len(result['chunks'])} chunks saved to {output_path}")