"""
Run the full pipeline on each video and print metrics.
Skips stages whose output already exists (use --force to redo everything).
"""
import argparse
import json
import os
import time

from extract_audio import extract_audio
from transcript_pipeline import transcribe
from audio_pipeline import analyze_audio
from convert_ground_truth import convert
from transcript_classifier import classify_transcript
from evaluate import per_second_accuracy, ad_detection_metrics, boundary_accuracy

DEFAULT_VIDEOS = ['test_001', 'test_002', 'test_003', 'test_004', 'test_005']


def maybe_skip(path, force):
    if not force and os.path.exists(path):
        print(f"  skip   {path}")
        return True
    return False


def run(video_id, force, model_size):
    print(f"\n--- {video_id} ---")

    mp4    = f'data/videos/{video_id}.mp4'
    wav    = f'data/videos/{video_id}.wav'
    tjson  = f'data/transcripts/{video_id}.json'
    ajson  = f'data/audio_events/{video_id}.json'
    src    = f'source_of_truth/{video_id}.json'
    dst    = f'data/ground_truth/{video_id}.json'
    pred   = f'data/predictions/{video_id}_baseline.json'

    if not os.path.exists(mp4):
        print(f"  no mp4 ({mp4}), skipping video")
        return None
    if not os.path.exists(src):
        print(f"  no source_of_truth ({src}), skipping video")
        return None

    for d in ['data/transcripts', 'data/audio_events', 'data/ground_truth', 'data/predictions']:
        os.makedirs(d, exist_ok=True)

    # 1. wav
    if not maybe_skip(wav, force):
        t0 = time.time()
        extract_audio(mp4)
        print(f"  wav    {time.time()-t0:.1f}s")

    # 2. transcript -- this is the slow one (~3-5 min on M1 with medium)
    if not maybe_skip(tjson, force):
        t0 = time.time()
        result = transcribe(wav, video_id, model_size=model_size)
        with open(tjson, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"  whisper {time.time()-t0:.1f}s")

    # 3. audio events
    if not maybe_skip(ajson, force):
        t0 = time.time()
        result = analyze_audio(wav, video_id)
        with open(ajson, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"  audio  {time.time()-t0:.1f}s")

    # 4. ground truth (course json -> our format)
    if not maybe_skip(dst, force):
        convert(src, dst)

    # 5. classify -- ollama call, ~30s
    if not maybe_skip(pred, force):
        t0 = time.time()
        result = classify_transcript(tjson)
        with open(pred, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"  ollama {time.time()-t0:.1f}s")

    # 6. eval (always runs, doesn't write anything)
    p = json.load(open(pred))
    t = json.load(open(dst))
    acc = per_second_accuracy(p['segments'], t['segments'], t['duration_sec'])
    ads = ad_detection_metrics(p['segments'], t['segments'])
    bnd = boundary_accuracy(p['segments'], t['segments'])

    msg = f"  acc={acc:.1%} detected={ads['detected_ads']}/{ads['true_ads']} prec={ads['precision']:.0%}"
    if bnd:
        msg += f" boundary_err={bnd['avg_boundary_error_sec']:.1f}s"
    print(msg)

    return {
        'video_id': video_id,
        'acc': acc,
        'recall': ads['recall'],
        'precision': ads['precision'],
        'detected': ads['detected_ads'],
        'true_ads': ads['true_ads'],
        'bnd_err': bnd['avg_boundary_error_sec'] if bnd else None,
    }


def summarize(results):
    results = [r for r in results if r is not None]
    if not results:
        print("\nnothing to summarize")
        return

    print(f"\n=== summary ({len(results)} videos) ===")
    for r in results:
        bnd = f"{r['bnd_err']:.1f}s" if r['bnd_err'] is not None else "n/a"
        print(f"  {r['video_id']}  acc={r['acc']:.1%}  "
              f"{r['detected']}/{r['true_ads']} ads  "
              f"prec={r['precision']:.0%}  bnd={bnd}")

    n = len(results)
    avg_acc = sum(r['acc'] for r in results) / n
    avg_recall = sum(r['recall'] for r in results) / n
    avg_prec = sum(r['precision'] for r in results) / n
    errs = [r['bnd_err'] for r in results if r['bnd_err'] is not None]
    avg_bnd = sum(errs) / len(errs) if errs else None
    bnd_str = f"{avg_bnd:.1f}s" if avg_bnd is not None else "n/a"

    print(f"  ----")
    print(f"  avg        acc={avg_acc:.1%}  recall={avg_recall:.0%}  "
          f"prec={avg_prec:.0%}  bnd={bnd_str}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('video_ids', nargs='*', default=DEFAULT_VIDEOS)
    ap.add_argument('--force', action='store_true', help='redo cached stages')
    ap.add_argument('--model', default='medium', help='whisper model size')
    args = ap.parse_args()

    results = [run(v, args.force, args.model) for v in args.video_ids]
    summarize(results)
