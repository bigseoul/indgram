import os

import google.generativeai as genai
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# API 키 설정
api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY or GEMINI_API_KEY not found in environment variables.")
else:
    genai.configure(api_key=api_key)
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            print(f"Model Name: {m.name}")
            print(f"Description: {m.description}\n")
