import io
import logging
import os

import google.auth
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class DriveService:
    def __init__(self):
        # ADC will automatically find credentials from 'gcloud auth application-default login'
        self.creds, self.project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        self.service = build("drive", "v3", credentials=self.creds)
        self.folder_id = os.getenv("DRIVE_FOLDER_ID")

    def list_files_in_folder(self):
        if not self.folder_id:
            logger.warning("DRIVE_FOLDER_ID not set.")
            return []

        logger.info(f"Listing files in folder: {self.folder_id}")
        query = f"'{self.folder_id}' in parents and trashed = false"
        results = (
            self.service.files()
            .list(q=query, fields="files(id, name, mimeType, modifiedTime)")
            .execute()
        )
        files = results.get("files", [])
        logger.info(f"Found {len(files)} files.")
        return files

    def download_file(self, file_id, file_name):
        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

        # Save to temporary file or return bytes
        # For Gemini upload, we might need a path, so let's save to a temp folder
        temp_dir = os.path.join(os.path.dirname(__file__), "temp_downloads")
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, file_name)

        with open(file_path, "wb") as f:
            f.write(fh.getbuffer())

        return file_path
