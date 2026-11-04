import json

for enc in ['utf-16', 'utf-8', 'utf-16-le', 'cp1252']:
    try:
        with open('yt_details.json', 'r', encoding=enc) as f:
            d = json.load(f)
            print("Encoding:", enc)
            print("Title:", d.get('title'))
            print("Description:\n", d.get('description'))
            print("Tags:", d.get('tags'))
            print("Chapters:", d.get('chapters'))
            break
    except Exception as e:
        pass

