# Same prompt as transcript_classifier, but Llama 70B on Groq instead of local 8B.
import json
import os
import sys

from groq import Groq

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from transcript_classifier import build_prompt


def classify_transcript(transcript_path, model='llama-3.3-70b-versatile'):
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set. Get one at https://console.groq.com")

    client = Groq(api_key=api_key)

    with open(transcript_path) as f:
        transcript = json.load(f)

    print(f"Loaded {len(transcript['chunks'])} chunks from {transcript_path}")
    print(f"Calling Groq ({model})...")

    prompt = build_prompt(transcript['chunks'], transcript['duration_sec'])

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    result = json.loads(response.choices[0].message.content)

    return {
        'video_id': transcript['video_id'],
        'duration_sec': transcript['duration_sec'],
        'method': f'transcript_only_groq ({model})',
        'segments': result['segments'],
    }


if __name__ == '__main__':
    video_id = sys.argv[1] if len(sys.argv) > 1 else 'test_001'
    transcript_path = f'data/transcripts/{video_id}.json'
    output_path = f'data/predictions/{video_id}_groq.json'

    os.makedirs('data/predictions', exist_ok=True)

    result = classify_transcript(transcript_path)

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\nSaved {len(result['segments'])} segments to {output_path}")
    for seg in result['segments']:
        marker = "AD" if seg['label'] == 'advertisement' else "  "
        dur = seg['end'] - seg['start']
        print(f"  {marker} [{seg['start']:7.1f} - {seg['end']:7.1f}] ({dur:6.1f}s) {seg['label']}")
