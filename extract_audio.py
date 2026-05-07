import subprocess
import os

def extract_audio(video_path: str, output_path: str = None) -> str:
    """Extract audio from video file as 16kHz mono WAV (ideal for analysis)."""
    if output_path is None:
        base = os.path.splitext(video_path)[0]
        output_path = f"{base}.wav"

    subprocess.run([ 
        'ffmpeg', '-y',
        '-i', video_path,
        '-ac', '1',
        '-ar', '16000',
        '-vn',
        output_path
    ], check=True) 

    return output_path


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Extract audio from an MP4 file.')
    parser.add_argument('filename', nargs='?', default='test_001.mp4',
                        help='MP4 filename inside data/videos/ (default: test_001.mp4)')
    args = parser.parse_args()

    video_path = os.path.join('data', 'videos', args.filename)
    audio_path = extract_audio(video_path)
    print(f"Audio extracted to: {audio_path}")