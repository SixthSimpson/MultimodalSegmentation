import ollama
import json
import os
import sys


def build_prompt(chunks: list, video_duration: float) -> str:
    transcript_text = "\n".join(
        f"[{c['start']:.1f}-{c['end']:.1f}] {c['text']}"
        for c in chunks
    )
    
    return f"""You are analyzing a video transcript to identify INSERTED ADVERTISEMENTS.

This video is a TED Talk or similar long-form content where 1-3 advertisements have been inserted at unknown timestamps. Your job is to find every ad.

Advertisements typically:
- Mention specific brand or product names (chips, snacks, software, services, etc.)
- Contain jingles, slogans, or repetitive promotional language
- Have a sudden topic shift unrelated to the surrounding content
- Use short, fragmented sentences typical of commercials
- May include lyrics or musical content (sometimes transcribed as "[song]" or random lyric-like text)
- Often contain calls to action ("try", "taste", "available now", etc.)

Examples of advertisement content:
- "Out for some Lay's, you face a test. Which tasty chip will be the best? Sour cream and onion smoky barbecue."
- "Who has the Doritos? Who has the Doritos? You want one?"
- "It's a good song. I think it's a good song. It's a good song." (repetitive ad jingle)

Examples of NON-advertisement content (TED Talk style):
- "What is it about a big brain that nature was so eager for every one of us to have one?"
- "Human beings have this marvelous adaptation that they can actually have experiences in their heads."

Be DECISIVE. If you see brand names, jingles, or sudden topic breaks, those are ads. Do not be conservative — finding ads is the goal.

The video is {video_duration:.0f} seconds long.

TRANSCRIPT:
{transcript_text}

Output a JSON object with a "segments" array. Cover the entire video from 0 to {video_duration:.0f}. Each segment must have:
- "start": number (seconds)
- "end": number (seconds)  
- "label": "advertisement" OR "video_content"

Aim to identify 1-5 advertisement segments. Be aggressive about flagging suspicious content as ads."""


def classify_transcript(transcript_path: str, model: str = 'llama3.1:8b') -> dict:
    """Classify a transcript into segments using Ollama."""
    
    with open(transcript_path) as f:
        transcript = json.load(f)
    
    print(f"Loaded {len(transcript['chunks'])} chunks from {transcript_path}")
    print(f"Calling Ollama ({model})... this takes ~30s")
    
    prompt = build_prompt(transcript['chunks'], transcript['duration_sec'])
    
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
                            'label': {
                                'type': 'string',
                                'enum': ['advertisement', 'video_content']
                            }
                        },
                        'required': ['start', 'end', 'label']
                    }
                }
            },
            'required': ['segments']
        },
        # low temp + 16k context (default 2k truncates the prompt silently)
        options={'temperature': 0.1, 'num_ctx': 16384, 'num_predict': 4096},
    )
    
    result = json.loads(response['message']['content'])
    
    return {
        'video_id': transcript['video_id'],
        'duration_sec': transcript['duration_sec'],
        'method': 'transcript_only_baseline',
        'segments': result['segments']
    }


if __name__ == '__main__':
    video_id = sys.argv[1] if len(sys.argv) > 1 else 'test_001'
    
    transcript_path = f'data/transcripts/{video_id}.json'
    output_path = f'data/predictions/{video_id}_baseline.json'
    
    os.makedirs('data/predictions', exist_ok=True)
    
    result = classify_transcript(transcript_path)
    
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\nSaved {len(result['segments'])} segments to {output_path}")
    for seg in result['segments']:
        marker = "AD" if seg['label'] == 'advertisement' else "  "
        duration = seg['end'] - seg['start']
        print(f"  {marker} [{seg['start']:7.1f} - {seg['end']:7.1f}] ({duration:6.1f}s) {seg['label']}")