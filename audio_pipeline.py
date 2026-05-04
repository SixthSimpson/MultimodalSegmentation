import librosa
import numpy as np
import json

def analyze_audio(audio_path: str, video_id: str) -> dict:
    """Extract audio events: silence, speech, music regions."""

    # Loading audio 16khz mono audio
    y, sr = librosa.load(audio_path, sr = 16000, mono = True)
    duration = len(y) / sr

    # frame level analysis (1 frame = ~32ms)
    frame_length = 2048
    hop_length = 512

    # RMS energy (essentially volume)
    rms = librosa.feature.rms(y = y, frame_length = frame_length, hop_length = hop_length)[0]

    # Spectral centroid  
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]

    # Zero crossing rate (speech has higher crossing rate than music)
    zcr = librosa.feature.zero_crossing_rate(y, frame_length=frame_length, hop_length=hop_length)[0]

    # Convert frame indices to timestamps
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

    # Classify each frame 
    labels = []
    silence_threshold = 0.01 

    for i in range(len(rms)):
        if rms[i] < silence_threshold:
            labels.append('silence')
        elif centroid[i] > 2000 and zcr[i] < 0.08:
            labels.append('music')
        else:
            labels.append('speech')
    
    # Merge consecutive same-label frames into events
    events = merge_into_events(times, labels, min_duration=3.0)

    return{
        'video_id': video_id,
        'duration_sec': float(duration),
        'events': events
    }

def merge_into_events(times, labels, min_duration = 1.0):
    """Merge consecutive same-label frames into events, filtering out short ones."""
    
    if not labels:
        return[]
    
    events = []
    current_label = labels[0]
    current_start = times[0]

    for i in range(1, len(labels)):
        if labels[i] != current_label:
            duration = times[i] - current_start
            if duration >= min_duration:
                events.append({
                    'start': float(current_start),
                    'end': float(times[i]),
                    'type': current_label
                })
            current_label = labels[i]
            current_start = times[i]

    # final event
    duration = times[-1] - current_start
    if duration >= min_duration:
        events.append({
            'start': float(current_start),
            'end': float(times[-1]),
            'type': current_label
        })

    # Smooth: merge adjacent same-type events that got split
    smoothed = [events[0]] if events else []
    for e in events[1:]:
        if e['type'] == smoothed[-1]['type']:
            smoothed[-1]['end'] = e['end']
        else:
            smoothed.append(e)
    
    return smoothed


if __name__ == '__main__':
    import argparse
    import os
    parser = argparse.ArgumentParser(description='Analyze audio events from an MP4/WAV file.')
    parser.add_argument('filename', nargs='?', default='test_001.mp4',
                        help='Video filename, e.g. test_001.mp4. Reads the matching '
                             '.wav from data/videos/ (created by extract_audio.py).')
    args = parser.parse_args()

    stem = os.path.splitext(args.filename)[0]
    audio_path = os.path.join('data', 'videos', f'{stem}.wav')
    result = analyze_audio(audio_path, stem)

    # Print summary
    print(f"Duration: {result['duration_sec']:.1f}s")
    print(f"Total events: {len(result['events'])}")

    # Count by type
    from collections import Counter
    counts = Counter(e['type'] for e in result['events'])
    for label, count in counts.items():
        print(f" {label}: {count} events")

    # Show the first 10 events
    print("\nFirst 10 events:")
    for e in result['events'][:10]:
        print(f"  {e['start']:6.1f} - {e['end']:6.1f}  [{e['type']}]")

    # Save to JSON
    output_path = os.path.join('data', 'audio_events', f'{stem}.json')
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to {output_path}")
