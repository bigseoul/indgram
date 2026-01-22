import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        self.client = genai.Client(
            api_key=self.api_key, http_options={"api_version": "v1beta"}
        )
        self.model_name = "gemini-3-pro-preview"

    def get_or_create_file_search_store(self, display_name="Company Knowledge Base"):
        logger.info(f"Checking for store with display_name: {display_name}")
        stores = list(self.client.file_search_stores.list())
        for store in stores:
            if store.display_name == display_name:
                logger.info(f"Found existing store: {store.name}")
                return store

        logger.info("Creating new file search store...")
        return self.client.file_search_stores.create(
            config=types.CreateFileSearchStoreConfig(display_name=display_name)
        )

    def upload_file_to_store(
        self, store_id, file_path, display_name=None, mime_type=None
    ):
        with open(file_path, "rb") as f:
            return self.client.file_search_stores.upload_to_file_search_store(
                file_search_store_name=store_id,
                file=f,
                config=types.UploadToFileSearchStoreConfig(
                    display_name=display_name or os.path.basename(file_path),
                    mime_type=mime_type,
                ),
            )

    def list_store_files(self, store_id):
        # The list method returns a pager; convert to list
        return list(self.client.file_search_stores.documents.list(parent=store_id))

    def delete_file(self, document_name):
        """Deletes a document from the store using its resource name."""
        try:
            logger.info(f"Deleting document: {document_name}")
            return self.client.file_search_stores.documents.delete(name=document_name)
        except Exception as e:
            logger.error(f"Failed to delete document {document_name}: {e}")
            raise

    def delete_store(self, store_name):
        """Deletes the entire file search store (using force to clean non-empty stores)."""
        logger.info(f"Deleting entire store: {store_name}")
        return self.client.file_search_stores.delete(
            name=store_name, config=types.DeleteFileSearchStoreConfig(force=True)
        )

    def ask_question(self, store_id, prompt):
        # Using File Search as a tool
        # In the new SDK, tools are passed to generate_content
        file_search_tool = types.Tool(
            file_search=types.FileSearch(file_search_store_names=[store_id])
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(tools=[file_search_tool]),
        )
        return response.text
