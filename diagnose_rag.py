from dotenv import load_dotenv
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# 위키피디아 정책과 지침
url = "https://ko.wikipedia.org/wiki/%EC%9C%84%ED%82%A4%EB%B0%B1%EA%B3%BC:%EC%A0%95%EC%B1%85%EA%B3%BC_%EC%A7%80%EC%B9%A8"
loader = WebBaseLoader(url)
docs = loader.load()

print(f"Total document length: {len(docs[0].page_content)}")

# Check if '격하' exists in the raw document
index = docs[0].page_content.find("격하")
if index != -1:
    print(f"Found '격하' at index {index}")
    print(f"Context: {docs[0].page_content[index - 50 : index + 200]}")
else:
    print("'격하' not found in the raw document loaded by WebBaseLoader.")

# Split documents
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
splits = text_splitter.split_documents(docs)

print(f"Number of splits: {len(splits)}")

# Find which split contains '격하'
found_splits = []
for i, split in enumerate(splits):
    if "격하" in split.page_content:
        found_splits.append(i)

if found_splits:
    print(f"'격하' found in splits: {found_splits}")
    for i in found_splits:
        print(f"\n--- Split {i} ---\n{split.page_content[:200]}...")
else:
    print("'격하' not found in any split.")
