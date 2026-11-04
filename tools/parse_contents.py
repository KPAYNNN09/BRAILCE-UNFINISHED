import re

with open('yt_contents_extracted.txt', 'r', encoding='utf-8') as f:
    text = f.read()

texts = re.findall(r'"text":\s*"([^"]+)"', text)
seen = set()
for t in texts:
    if len(t) > 20 and not t.startswith('http') and t not in seen:
        seen.add(t)
        print(t)

