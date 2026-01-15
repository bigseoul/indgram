import bs4
from langchain_community.document_loaders import WebBaseLoader

url = "https://ko.wikipedia.org/wiki/%EC%9C%84%ED%82%A4%EB%B0%B1%EA%B3%BC:%EC%A0%95%EC%B1%85%EA%B3%BC_%EC%A7%80%EC%B9%A8"

# Target only the main content area
loader = WebBaseLoader(
    web_path=url,
    bs_kwargs=dict(parse_only=bs4.SoupStrainer("div", attrs={"id": "mw-content-text"})),
)

docs = loader.load()
content = docs[0].page_content

print(f"Content length: {len(content)}")
if "격하" in content:
    print("Found '격하' in targeted content!")
    index = content.find("격하")
    print(f"Context: {content[index : index + 200]}")
else:
    print("'격하' NOT found even with targeting.")

# Additional check: what if we use the default loader but with a proper User-Agent?
import os

os.environ["USER_AGENT"] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)

loader_default = WebBaseLoader(url)
docs_default = loader_default.load()
print(f"Default loader content length: {len(docs_default[0].page_content)}")
if "격하" in docs_default[0].page_content:
    print("Found '격하' in default loader content with USER_AGENT.")
