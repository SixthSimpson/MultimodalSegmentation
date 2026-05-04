import ollama
import json
from scenedetect import detect, ContentDetector, AdaptiveDetector

def classify_segment(text: str) -> dict:
    """Classify a transcript segment into a content category."""
    
    system_prompt = """You are a content classifier for long-form video transcripts.
Classify the given segment into ONE of these categories:
- intro: Opening of the video, host greeting, episode preview
- main_content: The core topic/discussion of the video
- advertisement: Paid ads, sponsor reads, promotional content
- transition: Brief segues between topics
- outro: Closing remarks, sign-offs, calls to subscribe
- qa: Question and answer segments

Respond ONLY in JSON with this exact structure:
{
  "category": "<one of the categories above>",
  "confidence": <number between 0 and 1>,
  "reasoning": "<brief explanation>"
}"""


    response = ollama.chat(
        model='llama3.1:8b',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f'Classify this segment:\n\n"{text}"'}
        ],
        format='json'
    )
    
    return json.loads(response['message']['content'])


def process_scenes(location):
    scene_list = detect(location, AdaptiveDetector())
    for i, (start_time, end_time) in enumerate(scene_list):
        print(f"Scene {i}:")
        print(f"  Starts at: {start_time.get_timecode()} ({start_time.get_seconds()}s)")
        print(f"  Ends at:   {end_time.get_timecode()} ({end_time.get_seconds()}s)")
        print(f"  Length:    {end_time.get_seconds() - start_time.get_seconds()}s")


# Run the prompt and analyze the test segment
if __name__ == '__main__':
    process_scenes('data/test_001.mp4')


    
