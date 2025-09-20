from flask import Flask, request, jsonify
import os
import asyncio
from dotenv import load_dotenv
import json

# Import our services
from services.whatsapp_api import WhatsAppAPI
from services.ai_manager import AIManager
from services.drive_storage import DriveStorage
from services.file_processor import FileProcessor
from services.knowledge_base import KnowledgeBase

load_dotenv()

app = Flask(__name__)

# Initialize services
drive_storage = DriveStorage()
ai_manager = AIManager()
file_processor = FileProcessor(os.getenv('WHATSAPP_ACCESS_TOKEN'), drive_storage)
whatsapp_api = WhatsAppAPI(
    os.getenv('WHATSAPP_ACCESS_TOKEN'),
    os.getenv('WHATSAPP_PHONE_NUMBER_ID')
)

# Store active knowledge bases per user
user_knowledge_bases = {}

class WhatsAppBot:
    def __init__(self):
        self.conversations = {}
    
    def get_user_kb(self, user_id):
        """Get or create knowledge base for user"""
        if user_id not in user_knowledge_bases:
            kb = KnowledgeBase(drive_storage)
            kb.load_from_drive(user_id)  # Try to load existing
            user_knowledge_bases[user_id] = kb
        return user_knowledge_bases[user_id]
    
    async def handle_message(self, message_data):
        """Handle incoming WhatsApp message"""
        try:
            sender = message_data.get('from')
            message_id = message_data.get('id')
            message_type = message_data.get('type')
            
            # Mark as read
            whatsapp_api.mark_message_read(message_id)
            
            # Load conversation context
            conversation = drive_storage.load_conversation(sender)
            kb = self.get_user_kb(sender)
            
            if message_type == 'text':
                await self.handle_text_message(sender, message_data, conversation, kb)
            elif message_type == 'image':
                await self.handle_image_message(sender, message_data, conversation, kb)
            elif message_type == 'document':
                await self.handle_document_message(sender, message_data, conversation, kb)
            else:
                whatsapp_api.send_text_message(
                    sender, 
                    "I can help you with text messages, images, and documents (PDF, Word, TXT)."
                )
        
        except Exception as e:
            print(f"Error handling message: {e}")
            whatsapp_api.send_text_message(
                sender,
                "Sorry, I encountered an error processing your message. Please try again."
            )
    
    async def handle_text_message(self, sender, message_data, conversation, kb):
        """Handle text messages"""
        text = message_data['text']['body']
        
        # Get context from knowledge base
        context = kb.get_context_for_query(text)
        
        # Add conversation history to context
        history_context = self.build_conversation_context(conversation)
        full_context = f"{context}\n\n{history_context}".strip()
        
        # Generate response
        response, provider = await ai_manager.generate_response(text, full_context)
        
        # Update conversation
        conversation['history'].append({
            'user': text,
            'bot': response,
            'provider': provider
        })
        
        # Save conversation
        drive_storage.save_conversation(sender, conversation)
        
        # Send response
        whatsapp_api.send_text_message(sender, response)
    
    async def handle_image_message(self, sender, message_data, conversation, kb):
        """Handle image messages"""
        media_id = message_data['image']['id']
        caption = message_data['image'].get('caption', 'Describe this image')
        filename = f"image_{message_data['timestamp']}.jpg"
        
        # Download and process image
        image_data, mime_type = file_processor.download_whatsapp_media(media_id)
        
        if image_data:
            processed_image = file_processor.process_image(image_data, filename)
            
            if processed_image:
                # Process with AI
                description = await ai_manager.process_image(processed_image['base64'], caption)
                
                # Add to knowledge base
                kb.add_document(description, {
                    'type': 'image',
                    'filename': filename,
                    'file_id': processed_image['file_id']
                })
                
                # Update conversation
                conversation['documents'] = conversation.get('documents', [])
                conversation['documents'].append({
                    'type': 'image',
                    'filename': filename,
                    'description': description,
                    'file_id': processed_image['file_id'],
                    'mime_type': mime_type
                })
                
                drive_storage.save_conversation(sender, conversation)
                kb.save_to_drive(sender)
                
                response = f"📷 **Image: {filename}**\n\n**Description:**\n{description}\n\n✅ Image added to your knowledge base. You can now ask questions about it!"
                whatsapp_api.send_text_message(sender, response)
            else:
                whatsapp_api.send_text_message(sender, f"Sorry, I couldn't extract text from {filename}.")
        else:
            whatsapp_api.send_text_message(sender, "Sorry, I couldn't download this document.")
    
    def build_conversation_context(self, conversation, max_exchanges=3):
        """Build conversation context from history"""
        history = conversation.get('history', [])
        if not history:
            return ""
        
        context = "Recent conversation:\n"
        for exchange in history[-max_exchanges:]:
            context += f"User: {exchange['user']}\nBot: {exchange['bot']}\n\n"
        
        return context.strip()

# Initialize bot
bot = WhatsAppBot()

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Webhook verification
        verify_token = request.args.get('hub.verify_token')
        if verify_token == os.getenv('WEBHOOK_VERIFY_TOKEN'):
            return request.args.get('hub.challenge', '')
        return 'Invalid verification token', 403
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Process webhook data
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    messages = value.get('messages', [])
                    
                    for message in messages:
                        # Run async handler
                        asyncio.create_task(bot.handle_message(message))
            
            return jsonify({'status': 'success'})
        except Exception as e:
            print(f"Webhook error: {e}")
            return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'whatsapp-bot'})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)