import time
import random
from groq import Groq
import cohere
import requests
from together import Together

class AIManager:
    def __init__(self):
        self.providers = {
            'groq': {
                'client': Groq(api_key=os.getenv('GROQ_API_KEY')),
                'rate_limit': {'requests': 0, 'window_start': time.time(), 'max_per_minute': 60},
                'model': 'mixtral-8x7b-32768'
            },
            'together': {
                'client': Together(api_key=os.getenv('TOGETHER_API_KEY')),
                'rate_limit': {'requests': 0, 'window_start': time.time(), 'max_per_minute': 50},
                'model': 'mistralai/Mixtral-8x7B-Instruct-v0.1'
            },
            'cohere': {
                'client': cohere.Client(os.getenv('COHERE_API_KEY')),
                'rate_limit': {'requests': 0, 'window_start': time.time(), 'max_per_minute': 20},
                'model': 'command-r'
            }
        }
        self.current_provider = 'groq'
    
    def _check_rate_limit(self, provider_name):
        """Check if provider is within rate limits"""
        provider = self.providers[provider_name]
        current_time = time.time()
        
        # Reset counter if window expired (1 minute)
        if current_time - provider['rate_limit']['window_start'] > 60:
            provider['rate_limit']['requests'] = 0
            provider['rate_limit']['window_start'] = current_time
        
        return provider['rate_limit']['requests'] < provider['rate_limit']['max_per_minute']
    
    def _get_available_provider(self):
        """Get next available provider within rate limits"""
        # Try current provider first
        if self._check_rate_limit(self.current_provider):
            return self.current_provider
        
        # Try other providers
        for provider_name in self.providers.keys():
            if provider_name != self.current_provider and self._check_rate_limit(provider_name):
                self.current_provider = provider_name
                return provider_name
        
        # If all providers are rate limited, wait and retry with least used
        time.sleep(2)
        return min(self.providers.keys(), 
                  key=lambda x: self.providers[x]['rate_limit']['requests'])
    
    def _increment_usage(self, provider_name):
        """Increment usage counter for provider"""
        self.providers[provider_name]['rate_limit']['requests'] += 1
    
    async def generate_response(self, message, context="", max_retries=3):
        """Generate response using available AI provider"""
        for attempt in range(max_retries):
            try:
                provider_name = self._get_available_provider()
                provider = self.providers[provider_name]
                
                # Build prompt
                full_prompt = f"""Context: {context}

User message: {message}

Please provide a helpful response. If the information is not available in the provided context, clearly state "This information is not available in the provided documents" and then provide a general response based on your knowledge."""

                # Generate response based on provider
                if provider_name == 'groq':
                    response = provider['client'].chat.completions.create(
                        messages=[{"role": "user", "content": full_prompt}],
                        model=provider['model'],
                        max_tokens=1000,
                        temperature=0.7
                    )
                    result = response.choices[0].message.content
                
                elif provider_name == 'together':
                    response = provider['client'].chat.completions.create(
                        model=provider['model'],
                        messages=[{"role": "user", "content": full_prompt}],
                        max_tokens=1000,
                        temperature=0.7
                    )
                    result = response.choices[0].message.content
                
                elif provider_name == 'cohere':
                    response = provider['client'].chat(
                        message=full_prompt,
                        model=provider['model'],
                        max_tokens=1000
                    )
                    result = response.text
                
                self._increment_usage(provider_name)
                return result, provider_name
                
            except Exception as e:
                print(f"Error with {provider_name}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    return "I'm experiencing technical difficulties. Please try again later.", "error"
    
    async def process_image(self, image_base64, prompt="Describe this image"):
        """Process image using Groq vision model"""
        try:
            if self._check_rate_limit('groq'):
                client = self.providers['groq']['client']
                response = client.chat.completions.create(
                    model="llava-v1.5-7b-4096-preview",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                        ]
                    }],
                    max_tokens=1000
                )
                self._increment_usage('groq')
                return response.choices[0].message.content
            else:
                return "Image processing temporarily unavailable due to rate limits. Please try again later."
        except Exception as e:
            return f"Error processing image: {str(e)}"