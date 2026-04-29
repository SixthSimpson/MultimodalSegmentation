import ollama
import json

# accepts text segment and returns json dict for classification
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

# Run the prompt and analyze the test segment
if __name__ == '__main__':
    test_segments = [
        "Hey everyone, welcome back to the channel! Today we're going to talk about how neural networks learn.",
        "This episode is brought to you by Squarespace. Use code PODCAST for 10% off your first purchase.",
        "So when you backpropagate, the gradients flow backward through each layer, updating the weights.",
        "Thanks for watching! Don't forget to like and subscribe, and I'll see you in the next one."
    ]
    
    for segment in test_segments:
        print(f"\nSegment: {segment[:60]}...")
        result = classify_segment(segment)
        print(f"Category: {result['category']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Reasoning: {result['reasoning']}")

