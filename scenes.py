import json
import os
from scenedetect import detect, AdaptiveDetector


def detect_scenes(video_path, video_id):
    """Run PySceneDetect, return scene boundaries."""
    # adaptive handles fades/dissolves better than content
    scene_list = detect(video_path, AdaptiveDetector())

    scenes = []
    for i, (start, end) in enumerate(scene_list):
        s = start.get_seconds()
        e = end.get_seconds()
        scenes.append({
            'scene_index': i,
            'start': float(s),
            'end': float(e),
            'duration': float(e - s),
        })

    return {
        'video_id': video_id,
        'duration_sec': scenes[-1]['end'] if scenes else 0.0,
        'scenes': scenes,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Detect shot boundaries.')
    parser.add_argument('filename', nargs='?', default='test_001.mp4',
                        help='Video filename inside data/videos/ (default: test_001.mp4)')
    args = parser.parse_args()

    stem = os.path.splitext(args.filename)[0]
    video_path = os.path.join('data', 'videos', args.filename)
    output_path = os.path.join('data', 'visual_events', f'{stem}.json')

    os.makedirs('data/visual_events', exist_ok=True)

    result = detect_scenes(video_path, stem)

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"{len(result['scenes'])} scenes, total {result['duration_sec']:.1f}s")
    print("First 5:")
    for s in result['scenes'][:5]:
        print(f"  [{s['start']:7.1f} - {s['end']:7.1f}] ({s['duration']:.1f}s)")
    print(f"Saved to {output_path}")
