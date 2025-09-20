import requests
import json

class WhatsAppAPI:
    def __init__(self, access_token, phone_number_id):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.base_url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def send_text_message(self, to, message):
        """Send text message"""
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "text": {"body": message}
        }
        return self._send_request(data)
    
    def send_document_message(self, to, message, document_id):
        """Send document with caption"""
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "document",
            "document": {
                "id": document_id,
                "caption": message
            }
        }
        return self._send_request(data)
    
    def _send_request(self, data):
        """Send request to WhatsApp API"""
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=data
            )
            return response.json()
        except Exception as e:
            print(f"Error sending message: {e}")
            return {"error": str(e)}
    
    def mark_message_read(self, message_id):
        """Mark message as read"""
        data = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        return self._send_request(data)