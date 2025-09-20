import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # WhatsApp Settings
    WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')
    WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    WEBHOOK_VERIFY_TOKEN = os.getenv('WEBHOOK_VERIFY_TOKEN')
    
    # AI API Keys
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    TOGETHER_API_KEY = os.getenv('TOGETHER_API_KEY')
    COHERE_API_KEY = os.getenv('COHERE_API_KEY')
    HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
    
    # Google Drive
    GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    
    # App Settings
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    PORT = int(os.getenv('PORT', 5000))
    
    # Rate Limiting
    MAX_REQUESTS_PER_MINUTE = 50
    MAX_FILE_SIZE_MB = 10
    MAX_CONTEXT_LENGTH = 3000