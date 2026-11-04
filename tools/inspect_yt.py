import json

with open('playerResponse.json', 'r', encoding='utf-8') as f:
    player = json.load(f)

with open('yt_info_extracted.txt', 'w', encoding='utf-8') as out:
    out.write("VIDEO DETAILS:\n")
    out.write(json.dumps(player.get('videoDetails', {}), indent=2))
    out.write("\n\nMICROFORMAT:\n")
    out.write(json.dumps(player.get('microformat', {}), indent=2))

with open('ytInitialData.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

contents = data.get('contents', {})
with open('yt_contents_extracted.txt', 'w', encoding='utf-8') as out:
    out.write(json.dumps(contents, indent=2))

print("Extracted info saved.")
