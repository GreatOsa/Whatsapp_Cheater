import json
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import nltk
from nltk.tokenize import sent_tokenize

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class KnowledgeBase:
    def __init__(self, drive_storage):
        self.drive_storage = drive_storage
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = None
        self.documents = []
        
    def add_document(self, text, metadata):
        """Add document to knowledge base"""
        # Split text into sentences
        sentences = sent_tokenize(text)
        
        for i, sentence in enumerate(sentences):
            if len(sentence.strip()) > 20:  # Skip very short sentences
                doc_data = {
                    'text': sentence,
                    'metadata': metadata,
                    'sentence_id': i
                }
                self.documents.append(doc_data)
        
        # Rebuild index
        self._rebuild_index()
    
    def _rebuild_index(self):
        """Rebuild FAISS index with current documents"""
        if not self.documents:
            return
        
        texts = [doc['text'] for doc in self.documents]
        embeddings = self.model.encode(texts)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings.astype('float32'))
    
    def search(self, query, top_k=3, min_similarity=0.3):
        """Search for relevant documents"""
        if not self.index or not self.documents:
            return []
        
        # Encode query
        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding.astype('float32'), top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score > min_similarity and idx < len(self.documents):
                doc = self.documents[idx].copy()
                doc['similarity_score'] = float(score)
                results.append(doc)
        
        return results
    
    def get_context_for_query(self, query, max_chars=2000):
        """Get relevant context for a query"""
        relevant_docs = self.search(query)
        
        if not relevant_docs:
            return "No relevant information found in the provided documents."
        
        context = "Relevant information from uploaded documents:\n\n"
        current_length = len(context)
        
        for doc in relevant_docs:
            doc_text = f"From {doc['metadata'].get('filename', 'unknown file')}: {doc['text']}\n\n"
            
            if current_length + len(doc_text) > max_chars:
                break
            
            context += doc_text
            current_length += len(doc_text)
        
        return context.strip()
    
    def save_to_drive(self, user_id):
        """Save knowledge base to Google Drive"""
        kb_data = {
            'documents': self.documents
        }
        filename = f"knowledge_base_{user_id}.json"
        content = json.dumps(kb_data, indent=2).encode('utf-8')
        return self.drive_storage.upload_file(content, filename, 'application/json')
    
    def load_from_drive(self, user_id):
        """Load knowledge base from Google Drive"""
        try:
            # Search for knowledge base file
            query = f"name='knowledge_base_{user_id}.json'"
            # Implementation would depend on your Drive search method
            # For now, return empty if not found
            return False
        except:
            return False