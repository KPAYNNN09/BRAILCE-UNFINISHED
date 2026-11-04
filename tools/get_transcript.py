from youtube_transcript_api import YouTubeTranscriptApi

video_id = 'm7Q5ZjqN-ao'
try:
    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)
    # Find english transcript if possible
    en_t = None
    for t in transcript_list:
        if t.language_code.startswith('en'):
            en_t = t
            break
    if not en_t:
        en_t = list(transcript_list)[0]
    
    print("Using transcript:", en_t.language, en_t.language_code)
    fetched = en_t.fetch()
    with open('transcript_scotto.txt', 'w', encoding='utf-8') as f:
        for item in fetched:
            # item might be dict or object
            if isinstance(item, dict):
                text = item.get('text', '')
                start = item.get('start', 0)
            else:
                text = getattr(item, 'text', str(item))
                start = getattr(item, 'start', 0)
            f.write(f"{start:.1f}s: {text}\n")
    print("Transcript saved successfully.")
except Exception as e:
    import traceback
    traceback.print_exc()
