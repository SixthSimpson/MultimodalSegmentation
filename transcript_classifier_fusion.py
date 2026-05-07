# Multimodal fusion: transcript + audio events + scene cuts in one prompt.
# Set FUSION_BACKEND=groq for the fast cloud version (needs GROQ_API_KEY).
import json
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BACKEND = os.environ.get('FUSION_BACKEND', 'ollama')


def build_fusion_prompt(transcript, audio_events, scenes, duration):
    chunks = transcript['chunks']
    transcript_text = "\n".join(
        f"[{c['start']:.1f}-{c['end']:.1f}] {c['text']}"
        for c in chunks
    )

    # speech events are most of the video, only silence/music carry signal
    non_speech = [e for e in audio_events['events'] if e['type'] != 'speech']
    audio_text = "\n".join(
        f"[{e['start']:.1f}-{e['end']:.1f}] {e['type']}"
        for e in non_speech
    ) or "(none)"

    # only keep cuts bordering a stable scene -- drops camera-angle micro-cuts
    MIN_STABLE = 10.0
    scene_list = scenes['scenes']
    cuts = []
    for i, s in enumerate(scene_list):
        if s['scene_index'] == 0:
            continue
        prev = scene_list[i - 1]
        if s['duration'] >= MIN_STABLE or prev['duration'] >= MIN_STABLE:
            cuts.append(s['start'])
    cuts_text = ", ".join(f"{c:.1f}" for c in cuts) or "(none)"

    # whisper drops out on music-heavy ads, so transcript gaps are a strong signal
    MIN_GAP = 20.0
    gaps = []
    pos = 0.0
    for c in chunks:
        if c['start'] - pos >= MIN_GAP:
            gaps.append((pos, c['start']))
        pos = max(pos, c['end'])
    if duration - pos >= MIN_GAP:
        gaps.append((pos, duration))
    gaps_text = "\n".join(
        f"[{g[0]:.1f}-{g[1]:.1f}] silent gap ({g[1]-g[0]:.1f}s)"
        for g in gaps
    ) or "(none)"

    return f"""You are analyzing a long-form video to find INSERTED ADVERTISEMENTS.

The video could be any genre (podcast, lecture, talk, interview, etc.). What matters is that 1-3 ads have been inserted at unknown timestamps. Find every ad and set its boundaries precisely.

You have FOUR signals:

1. TRANSCRIPT (what was said):
{transcript_text}

2. AUDIO EVENTS (silences and music regions only -- regular speech omitted):
{audio_text}

3. VISUAL CUTS (timestamps where the video cuts to a new shot):
{cuts_text}

4. TRANSCRIPT GAPS (regions where Whisper produced no text):
{gaps_text}

HOW TO COMBINE THEM:
- Transcript tells you WHAT was said -- jingles, brand names, sponsor reads, promo codes, calls to action are ad signals.
- Silences and music regions often mark ad boundaries.
- Visual cuts almost always happen at ad boundaries (the source video and inserted ad don't share frames).
- TRANSCRIPT GAPS ARE A MAJOR AD SIGNAL: Whisper transcribes speech but struggles with music-heavy content. A 20+ second gap in the transcript usually means the audio is music or singing -- which is highly characteristic of inserted ads (jingles, song-based commercials). If a long transcript gap aligns with visual cuts at both ends, you should be VERY confident that span is an ad.
- When transcript looks ad-like AND a visual cut + audio gap fall near the same timestamp, snap your boundary to that exact timestamp instead of the loose Whisper chunk boundary.
- A single visual cut alone is not enough -- shot changes happen all the time in normal content.
- Ignore content that simply mentions a brand or product casually -- ads have promotional intent (selling, urging action, jingles).

Inserted ads are typically 20-120 seconds long. There are typically 1-3 of them.

The video is {duration:.0f} seconds long.

Output a JSON object with a "segments" array covering 0 to {duration:.0f}, in order, no overlaps. Each segment:
- "start": number (seconds)
- "end": number (seconds)
- "label": "advertisement" OR "video_content"
"""


def snap_to_cuts(segments, scenes, duration, tolerance=20.0):
    """Snap each predicted ad to the nearest visual cut within tolerance."""
    cuts = sorted({s['start'] for s in scenes['scenes']})

    snapped_ads = []
    for seg in segments:
        if seg['label'] != 'advertisement':
            continue

        start = seg['start']
        nearest = min(cuts, key=lambda c: abs(c - start))
        if abs(nearest - start) <= tolerance:
            start = nearest

        end = seg['end']
        nearest = min(cuts, key=lambda c: abs(c - end))
        if abs(nearest - end) <= tolerance:
            end = nearest

        if end > start:
            snapped_ads.append({'start': start, 'end': end, 'label': 'advertisement'})

    # merge overlaps that snapping might have created
    snapped_ads.sort(key=lambda s: s['start'])
    merged = []
    for ad in snapped_ads:
        if merged and ad['start'] <= merged[-1]['end']:
            merged[-1]['end'] = max(merged[-1]['end'], ad['end'])
        else:
            merged.append(dict(ad))

    # fill the rest with video_content
    out = []
    pos = 0.0
    for ad in merged:
        if ad['start'] > pos:
            out.append({'start': pos, 'end': ad['start'], 'label': 'video_content'})
        out.append(ad)
        pos = ad['end']
    if pos < duration:
        out.append({'start': pos, 'end': duration, 'label': 'video_content'})
    return out


def _call_ollama(prompt, model='llama3.1:8b'):
    import ollama
    response = ollama.chat(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        format={
            'type': 'object',
            'properties': {
                'segments': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'start': {'type': 'number'},
                            'end': {'type': 'number'},
                            'label': {'type': 'string', 'enum': ['advertisement', 'video_content']},
                        },
                        'required': ['start', 'end', 'label'],
                    },
                },
            },
            'required': ['segments'],
        },
        options={'temperature': 0.1, 'num_ctx': 16384, 'num_predict': 4096},
    )
    return json.loads(response['message']['content']), model


def _call_groq(prompt, model='llama-3.3-70b-versatile'):
    from groq import Groq
    client = Groq(api_key=os.environ['GROQ_API_KEY'])
    response = client.chat.completions.create(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        response_format={'type': 'json_object'},
        temperature=0.1,
    )
    return json.loads(response.choices[0].message.content), model


def classify_transcript(transcript_path, model=None):
    video_id = os.path.splitext(os.path.basename(transcript_path))[0]
    audio_path = f'data/audio_events/{video_id}.json'
    scenes_path = f'data/visual_events/{video_id}.json'

    for p in [audio_path, scenes_path]:
        if not os.path.exists(p):
            raise RuntimeError(f"missing {p} -- run audio_pipeline.py and scenes.py first")

    transcript = json.load(open(transcript_path))
    audio_events = json.load(open(audio_path))
    scenes = json.load(open(scenes_path))

    print(f"Loaded {len(transcript['chunks'])} chunks, "
          f"{len(audio_events['events'])} audio events, "
          f"{len(scenes['scenes'])} scenes")
    print(f"Calling fusion backend: {BACKEND}...")

    prompt = build_fusion_prompt(transcript, audio_events, scenes, transcript['duration_sec'])

    if BACKEND == 'groq':
        result, used_model = _call_groq(prompt, model or 'llama-3.3-70b-versatile')
    else:
        result, used_model = _call_ollama(prompt, model or 'llama3.1:8b')

    snapped = snap_to_cuts(result['segments'], scenes, transcript['duration_sec'])

    return {
        'video_id': transcript['video_id'],
        'duration_sec': transcript['duration_sec'],
        'method': f'multimodal_fusion ({BACKEND}: {used_model}) + snap_to_cuts',
        'segments': snapped,
    }


if __name__ == '__main__':
    video_id = sys.argv[1] if len(sys.argv) > 1 else 'test_001'
    transcript_path = f'data/transcripts/{video_id}.json'
    output_path = f'data/predictions/{video_id}_fusion.json'

    os.makedirs('data/predictions', exist_ok=True)
    result = classify_transcript(transcript_path)

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\nSaved {len(result['segments'])} segments to {output_path}")
    for seg in result['segments']:
        marker = "AD" if seg['label'] == 'advertisement' else "  "
        dur = seg['end'] - seg['start']
        print(f"  {marker} [{seg['start']:7.1f} - {seg['end']:7.1f}] ({dur:6.1f}s) {seg['label']}")
