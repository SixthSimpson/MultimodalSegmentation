import json
import sys
import os


def convert(course_json_path: str, output_path: str):
    with open(course_json_path) as f:
        data = json.load(f)
    
    segments = []
    for seg in data['timeline_segments']:
        if seg['type'] == 'ad':
            label = 'advertisement'
        else:
            label = 'video_content'
        
        segments.append({
            'start': seg['final_video_start_seconds'],
            'end': seg['final_video_end_seconds'],
            'label': label
        })
    
    output = {
        'video_id': os.path.splitext(os.path.basename(course_json_path))[0],
        'duration_sec': data['output_duration_seconds'],
        'segments': segments
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✓ Wrote {len(segments)} segments to {output_path}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Convert course source_of_truth JSON into the evaluator format.')
    parser.add_argument('video_id', nargs='?', default='test_001',
                        help='Video ID, e.g. test_001 (default: test_001). '
                             'Pass "all" to convert every file in source_of_truth/.')
    args = parser.parse_args()

    if args.video_id == 'all':
        for fname in sorted(os.listdir('source_of_truth')):
            if not fname.endswith('.json'):
                continue
            video_id = os.path.splitext(fname)[0]
            convert(
                os.path.join('source_of_truth', fname),
                os.path.join('data', 'ground_truth', f'{video_id}.json'),
            )
    else:
        convert(
            os.path.join('source_of_truth', f'{args.video_id}.json'),
            os.path.join('data', 'ground_truth', f'{args.video_id}.json'),
        )