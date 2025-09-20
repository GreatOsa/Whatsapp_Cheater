from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
import json
import os

class DriveStorage:
    def __init__(self):
        try:
            self.credentials = Credentials.from_service_account_file(
                'credentials.json',
                scopes=['https://www.googleapis.com/auth/drive']
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
            self.folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
            if not self.folder_id:
                raise ValueError("GOOGLE_DRIVE_FOLDER_ID environment variable is not set")
        except Exception as e:
            raise Exception(f"Failed to initialize DriveStorage: {str(e)}")
    
    def upload_file(self, file_content, filename, mime_type='application/octet-stream'):
        """Upload file to Google Drive and return file ID"""
        try:
            # Create file metadata
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }
            
            # Create file in memory
            file_stream = io.BytesIO(file_content)
            media = MediaIoBaseUpload(file_stream, mimetype=mime_type)
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            return file.get('id')
        except Exception as e:
            print(f"Error uploading file: {e}")
            return None
    
    def download_file(self, file_id):
        """Download file from Google Drive"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_stream = io.BytesIO()
            downloader = MediaIoBaseDownload(file_stream, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            file_stream.seek(0)
            return file_stream.read()
        except Exception as e:
            print(f"Error downloading file: {e}")
            return None
    
    def save_conversation(self, user_id, conversation_data):
        """Save conversation context to Drive"""
        filename = f"conversation_{user_id}.json"
        content = json.dumps(conversation_data, indent=2).encode('utf-8')
        return self.upload_file(content, filename, 'application/json')
    
    def load_conversation(self, user_id):
        """Load conversation context from Drive"""
        try:
            # Search for conversation file
            query = f"name='conversation_{user_id}.json' and parents='{self.folder_id}'"
            results = self.service.files().list(q=query).execute()
            files = results.get('files', [])
            
            if files:
                file_content = self.download_file(files[0]['id'])
                return json.loads(file_content.decode('utf-8'))
            return {"history": [], "documents": [], "knowledge_base": []}
        except Exception as e:
            print(f"Error loading conversation: {e}")
            return {"history": [], "documents": [], "knowledge_base": []}