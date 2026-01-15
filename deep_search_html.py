import re

import requests

url = "https://ko.wikipedia.org/wiki/%EC%9C%84%ED%82%A4%EB%B0%B1%EA%B3%BC:%EC%A0%95%EC%B1%85%EA%B3%BC_%EC%A7%80%EC%B9%A8"
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(url, headers=headers)
html = response.text

print(f"HTML Length: {len(html)}")

# Search for '격하'
matches = [m.start() for m in re.finditer("격하", html)]
print(f"Found {len(matches)} occurrences of '격하'")

for i, pos in enumerate(matches):
    print(f"\n--- Match {i + 1} at {pos} ---")
    print(html[max(0, pos - 100) : pos + 300])

# Search for the user's specific sentence
target_sentence = "격하 과정은 채택 과정과 비슷합니다"
if target_sentence in html:
    print("\nFound exact target sentence!")
else:
    print("\nExact target sentence NOT found in HTML.")
    # Try searching for parts
    if "격하" in html and "채택 과정" in html:
        print("Both '격하' and '채택 과정' keywords found in HTML.")
