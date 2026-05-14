"""Make 13_QUIZ-V5-FINAL.html fully offline: inline Google Fonts (woff2 as base64) + teacher-photo.jpg as data URI."""
import base64
import re
import urllib.request

SRC = "13_QUIZ-V5-FINAL.html"
DST = "13_QUIZ-V5-OFFLINE.html"
PHOTO = "teacher-photo.jpg"

FONTS_CSS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500;1,700"
    "&family=Nunito:wght@400;500;600;700;800;900"
    "&display=swap"
)

# Pretend to be a modern browser so Google serves woff2 + cyrillic
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req) as r:
        return r.read()

print("Fetching Google Fonts CSS...")
css = fetch(FONTS_CSS_URL).decode("utf-8")

# Find every url(...) in the CSS and replace with data: URI
url_pattern = re.compile(r"url\((https://fonts\.gstatic\.com/[^)]+)\)")
urls = list(set(url_pattern.findall(css)))
print(f"Found {len(urls)} font files to download")

cache = {}
for i, u in enumerate(urls, 1):
    print(f"  [{i}/{len(urls)}] {u[-60:]}")
    data = fetch(u)
    b64 = base64.b64encode(data).decode("ascii")
    cache[u] = f"data:font/woff2;base64,{b64}"

css_inline = url_pattern.sub(lambda m: f"url({cache[m.group(1)]})", css)

print(f"Encoding photo {PHOTO}...")
with open(PHOTO, "rb") as f:
    photo_b64 = base64.b64encode(f.read()).decode("ascii")
photo_uri = f"data:image/jpeg;base64,{photo_b64}"

print(f"Reading {SRC}...")
with open(SRC, "r", encoding="utf-8") as f:
    html = f.read()

# Replace the three Google Fonts <link> tags with a single inline <style>
preconnect1 = '<link rel="preconnect" href="https://fonts.googleapis.com">'
preconnect2 = '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
fonts_link_re = re.compile(
    r'<link href="https://fonts\.googleapis\.com/css2\?[^"]+" rel="stylesheet">'
)

html = html.replace(preconnect1, "")
html = html.replace(preconnect2, "")
html = fonts_link_re.sub(f"<style>\n{css_inline}\n</style>", html)

# Replace teacher photo src with data URI
html = html.replace('src="teacher-photo.jpg"', f'src="{photo_uri}"')

with open(DST, "w", encoding="utf-8") as f:
    f.write(html)

import os
size_mb = os.path.getsize(DST) / 1024 / 1024
print(f"\nDone: {DST} ({size_mb:.2f} MB)")
