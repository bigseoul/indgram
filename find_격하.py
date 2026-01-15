import os

from langchain_community.document_loaders import WebBaseLoader

os.environ["USER_AGENT"] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)

url = "https://ko.wikipedia.org/wiki/%EC%9C%84%ED%82%A4%EB%B0%B1%EA%B3%BC:%EC%A0%95%EC%B1%85%EA%B3%BC_%EC%A7%80%EC%B9%A8"
loader = WebBaseLoader(url)
docs = loader.load()
text = docs[0].page_content

import re

matches = [m.start() for m in re.finditer("격하", text)]
print(f"Found {len(matches)} occurrences")

for i, pos in enumerate(matches):
    print(f"\n--- Occurrence {i + 1} at index {pos} ---")
    print(text[max(0, pos - 20) : pos + 100])
