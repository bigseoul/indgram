import os

import streamlit as st
from drive_service import DriveService
from gemini_service import GeminiService

# Page config
st.set_page_config(page_title="Gemini Drive Assistant", layout="wide")

# Styling
st.markdown(
    """
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    .main-title {
        color: #1a73e8;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 2rem;
    }
    .chat-bubble {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Initialize Services
def get_services():
    try:
        return GeminiService(), DriveService()
    except Exception as e:
        st.error(f"Initialization Error: {e}")
        return None, None


gemini, drive = get_services()

st.title("📂 사내 문서 지식 베이스 (Gemini RAG)")

if not gemini or not drive:
    st.warning("환경 변수나 인증 설정을 확인해주세요.")
    st.stop()

# Sidebar: File Management
with st.sidebar:
    st.header("⚙️ 관리 도구")
    if st.button("🔄 드라이브 파일 동기화"):
        with st.spinner("구글 드라이브에서 파일을 가져와 제미나이에 최신화 중..."):
            try:
                # 1. Get or create store
                print(">>> Getting or creating file search store...")
                store = gemini.get_or_create_file_search_store()
                store_id = store.name  # Resource name like 'fileSearchStores/...'
                print(f">>> Store ID: {store_id}")

                # 2. List existing files in store to avoid duplicates
                existing_files = gemini.list_store_files(store_id)
                existing_map = {f.display_name: f.name for f in existing_files}

                # 3. List drive files
                print(">>> Listing files in Google Drive...")
                drive_files = drive.list_files_in_folder()
                print(f">>> Found {len(drive_files)} files in Drive.")

                # 4. Sync
                for df in drive_files:
                    # If file exists, delete it first to update
                    if df["name"] in existing_map:
                        print(f">>> Deleting existing version of {df['name']}...")
                        gemini.delete_file(existing_map[df["name"]])

                    st.write(f"업로드 중: {df['name']}...")
                    local_path = drive.download_file(df["id"], df["name"])
                    gemini.upload_file_to_store(
                        store_id, local_path, mime_type=df.get("mimeType")
                    )
                    os.remove(local_path)  # cleanup

                st.success("동기화 완료!")
            except Exception as e:
                import traceback

                error_details = traceback.format_exc()
                print(f">>> Error during sync: {error_details}")
                st.error(f"동기화 오류: {e}")

    if st.button("🗑️ 저장소 비우기", help="제미나이에 업로드된 모든 문서를 삭제합니다."):
        with st.spinner("저장소 비우는 중..."):
            try:
                store = gemini.get_or_create_file_search_store()
                print(f">>> Deleting store: {store.name}")
                gemini.delete_store(store.name)
                st.success(
                    "저장소를 비웠습니다. (다시 시작하면 새 저장소가 생성됩니다)"
                )
                st.rerun()
            except Exception as e:
                import traceback

                error_details = traceback.format_exc()
                st.error(f"비우기 오류: {e}")
                with st.expander("상세 오류"):
                    st.code(error_details)

    # Display indexed files
    st.subheader("📋 인덱싱된 파일 목록")
    try:
        store = gemini.get_or_create_file_search_store()
        files = gemini.list_store_files(store.name)
        if files:
            for f in files:
                st.text(f"• {f.display_name} ({f.state})")
        else:
            st.info("인덱싱된 파일이 없습니다.")
    except Exception as e:
        st.info("파일 정보를 불러올 수 없습니다.")
        print(f">>> Error loading file list: {e}")
        with st.expander("파일 목록 로드 오류 상세"):
            st.write(f"오류: {e}")

# Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("문서에 대해 궁금한 점을 물어보세요."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            try:
                store = gemini.get_or_create_file_search_store()
                response = gemini.ask_question(store.name, prompt)
                st.markdown(response)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )
            except Exception as e:
                import traceback

                error_details = traceback.format_exc()
                print(f">>> Error during chat: {error_details}")
                st.error(f"오류 발생: {e}")
                with st.expander("상세 에러 로그 보기"):
                    st.code(error_details)
