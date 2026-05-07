# Run the full pipeline end-to-end on each video. Skips cached stages by default.
import argparse
import json
import os
import time

from extract_audio import extract_audio
from transcript_pipeline import transcribe
from audio_pipeline import analyze_audio
from scenes import detect_scenes
from convert_ground_truth import convert
from evaluate import per_second_accuracy, ad_detection_metrics, boundary_accuracy

DEFAULT_VIDEOS = ['test_001', 'test_002', 'test_003', 'test_004', 'test_005']


def maybe_skip(path, force):
    if not force and os.path.exists(path):
        print(f"  skip   {path}")
        return True
    return False


def run(video_id, force, model_size, classifier):
    print(f"\n--- {video_id} ({classifier}) ---")

    if classifier == 'ollama':
        from transcript_classifier import classify_transcript as classify_fn
        suffix = 'baseline'
    elif classifier == 'groq':
        from transcript_classifier_groq import classify_transcript as classify_fn
        suffix = 'groq'
    elif classifier == 'fusion':
        from transcript_classifier_fusion import classify_transcript as classify_fn
        suffix = 'fusion'
    else:
        raise ValueError(f"unknown classifier: {classifier}")

    mp4    = f'data/videos/{video_id}.mp4'
    wav    = f'data/videos/{video_id}.wav'
    tjson  = f'data/transcripts/{video_id}.json'
    ajson  = f'data/audio_events/{video_id}.json'
    vjson  = f'data/visual_events/{video_id}.json'
    src    = f'source_of_truth/{video_id}.json'
    dst    = f'data/source_of_truth_flat/{video_id}.json'
    pred   = f'data/predictions/{video_id}_{suffix}.json'

    if not os.path.exists(mp4):
        print(f"  no mp4 ({mp4}), skipping video")
        return None
    if not os.path.exists(src):
        print(f"  no source_of_truth ({src}), skipping video")
        return None

    for d in ['data/transcripts', 'data/audio_events', 'data/visual_events',
              'data/source_of_truth_flat', 'data/predictions']:
        os.makedirs(d, exist_ok=True)

    # 1. wav
    if not maybe_skip(wav, force):
        t0 = time.time()
        extract_audio(mp4)
        print(f"  wav    {time.time()-t0:.1f}s")

    # 2. transcript -- slow, ~3-5 min per video on M1
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

    # 4. scene cuts (~30-90s on first run)
    if not maybe_skip(vjson, force):
        t0 = time.time()
        result = detect_scenes(mp4, video_id)
        with open(vjson, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"  scenes {time.time()-t0:.1f}s ({len(result['scenes'])} cuts)")

    # 5. ground truth (course json -> flat format)
    if not maybe_skip(dst, force):
        convert(src, dst)

    # 6. classify
    if not maybe_skip(pred, force):
        t0 = time.time()
        result = classify_fn(tjson)
        with open(pred, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"  {classifier} {time.time()-t0:.1f}s")

    # 7. eval (no caching, always runs)
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
    ap.add_argument('--classifier', choices=['ollama', 'groq', 'fusion'], default='ollama',
                    help='which classifier to use (default: ollama). fusion = transcript + audio + visual')
    args = ap.parse_args()

    results = [run(v, args.force, args.model, args.classifier) for v in args.video_ids]
    summarize(results)
