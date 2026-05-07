import json
import os

for video_id in ['test_001', 'test_002', 'test_003', 'test_004', 'test_005']:
    transcript_path = f'data/transcripts/{video_id}.json'
    truth_path = f'source_of_truth/{video_id}.json'

    if not (os.path.exists(transcript_path) and os.path.exists(truth_path)):
        continue

    transcript = json.load(open(transcript_path))
    truth = json.load(open(truth_path))

    print(f"\n{'='*70}\n{video_id}\n{'='*70}")

    for ad in truth['inserted_ads']:
        start = ad['final_video_ad_start_seconds']
        end = ad['final_video_ad_end_seconds']
        duration = ad['ad_duration_seconds']
        ad_text = ' '.join(
            c['text'] for c in transcript['chunks']
            if c['start'] >= start - 1 and c['end'] <= end + 1
        )
        print(f"\nAd {start:.0f}-{end:.0f}s ({duration:.0f}s)  [{ad['ad_filename']}]:")
        print(f"  {ad_text[:200]}")
