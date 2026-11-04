import urllib.request
import re

req = urllib.request.Request(
    'https://matthews.ma',
    headers={'User-Agent': 'Mozilla/5.0'}
)
try:
    html = urllib.request.urlopen(req).read().decode('utf-8')
    with open('matthews_home.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Downloaded matthews.ma homepage.")
    
    links = re.findall(r'href=[\'"]([^\'"]+)[\'"]', html)
    for l in links:
        if 'keyboard' in l.lower() or 'project' in l.lower() or 'blog' in l.lower():
            print("Link:", l)
except Exception as e:
    print("Error:", e)

