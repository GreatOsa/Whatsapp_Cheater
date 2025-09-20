import requests
import base64
import io
from PIL import Image
import PyPDF2
import docx
import os

class FileProcessor:
    def __init__(self, whatsapp_token, drive_storage):
        self.whatsapp_token = whatsapp_token
        self.drive_storage = drive_storage
        self.supported_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        self.supported_doc_types = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword',
            'text/plain'
        ]
    
    def download_whatsapp_media(self, media_id):
        """Download media from WhatsApp servers"""
        try:
            # Get media URL
            url = f"https://graph.facebook.com/v18.0/{media_id}"
            headers = {"Authorization": f"Bearer {self.whatsapp_token}"}
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return None, None
            
            media_info = response.json()
            media_url = media_info.get('url')
            mime_type = media_info.get('mime_type')
            
            # Download actual media content
            media_response = requests.get(media_url, headers=headers)
            if media_response.status_code == 200:
                return media_response.content, mime_type
            
            return None, None
        except Exception as e:
            print(f"Error downloading media: {e}")
            return None, None
    
    def process_image(self, image_data, filename="image.jpg"):
        """Process image and store in Drive"""
        try:
            # Convert to base64 for AI processing
            image = Image.open(io.BytesIO(image_data))
            
            # Resize if too large (cost optimization)
            if image.size[0] > 1024 or image.size[1] > 1024:
                image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            # Convert to JPEG and base64
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Store original in Drive
            file_id = self.drive_storage.upload_file(
                image_data, 
                f"images/{filename}",
                "image/jpeg"
            )
            
            return {
                'base64': img_base64,
                'file_id': file_id,
                'filename': filename,
                'type': 'image'
            }
        except Exception as e:
            print(f"Error processing image: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_data):
        """Extract text from PDF"""
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return f"Error reading PDF: {str(e)}"
    
    def extract_text_from_docx(self, docx_data):
        """Extract text from DOCX"""
        try:
            doc = docx.Document(io.BytesIO(docx_data))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error extracting DOCX text: {e}")
            return f"Error reading DOCX: {str(e)}"
    
    def process_document(self, doc_data, mime_type, filename="document"):
        """Process document and store in Drive"""
        try:
            # Extract text based on type
            if mime_type == 'application/pdf':
                text_content = self.extract_text_from_pdf(doc_data)
            elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                text_content = self.extract_text_from_docx(doc_data)
            elif mime_type == 'text/plain':
                text_content = doc_data.decode('utf-8', errors='ignore')
            else:
                text_content = f"Unsupported document type: {mime_type}"
            
            # Store original in Drive
            file_id = self.drive_storage.upload_file(
                doc_data,
                f"documents/{filename}",
                mime_type
            )
            
            return {
                'text': text_content,
                'file_id': file_id,
                'filename': filename,
                'mime_type': mime_type,
                'type': 'document'
            }
        except Exception as e:
            print(f"Error processing document: {e}")
            return None
    
    def is_supported_file(self, mime_type):
        """Check if file type is supported"""
        return (mime_type in self.supported_image_types or 
                mime_type in self.supported_doc_types)