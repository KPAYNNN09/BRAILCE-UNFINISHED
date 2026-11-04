import json
import re

with open('video_page.html', 'r', encoding='utf-8') as f:
    html = f.read()

m = re.search(r'var ytInitialData\s*=\s*({.+?});</script>', html)
if m:
    data = json.loads(m.group(1))
    with open('ytInitialData.json', 'w', encoding='utf-8') as out:
        json.dump(data, out, indent=2)
    print("ytInitialData saved successfully.")
else:
    print("ytInitialData not found.")

m2 = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});(?:var\s|window\[|<)', html)
if m2:
    player_data = json.loads(m2.group(1))
    with open('playerResponse.json', 'w', encoding='utf-8') as out:
        json.dump(player_data, out, indent=2)
    print("playerResponse saved successfully.")

