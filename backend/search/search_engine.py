import sqlite3
import json
import requests
from pathlib import Path
from sentence_transformers import SentenceTransformer, CrossEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class SearchEngine:
    def __init__(self, db_path):
        self.db_path = db_path
        
        # Load models
        self.dense_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        # Load documents and build indices
        self.documents = self._load_documents_from_db()
        self.doc_embeddings = self._build_dense_index()
        self.tfidf_vectorizer, self.tfidf_matrix = self._build_sparse_index()
    
    def _load_documents_from_db(self):
        """Load documents from SQLite database"""
        conn = sqlite3.connect(self.db_path)
        
        # Get all unique PMC IDs
        pmc_ids = conn.execute("SELECT DISTINCT subject FROM triples WHERE subject LIKE 'PMC%'").fetchall()
        
        documents = {}
        for (pmc_id,) in pmc_ids:
            # Get all triples for this PMC
            triples = conn.execute("SELECT predicate, object FROM triples WHERE subject = ?", (pmc_id,)).fetchall()
            
            # Build searchable text from triples
            text_parts = []
            for predicate, obj in triples:
                if obj and obj.strip():  # Skip empty values
                    text_parts.append(obj)
            
            documents[pmc_id] = {
                'text': ' '.join(text_parts),
                'triples': triples
            }
        
        conn.close()
        return documents
    
    def _build_dense_index(self):
        """Build dense embeddings for all documents"""
        texts = [doc['text'] for doc in self.documents.values()]
        embeddings = self.dense_model.encode(texts)
        return embeddings
    
    def _build_sparse_index(self):
        """Build TF-IDF sparse index"""
        texts = [doc['text'] for doc in self.documents.values()]
        vectorizer = TfidfVectorizer(max_features=10000, stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(texts)
        return vectorizer, tfidf_matrix
    
    def sparse_search(self, query, top_k=50):
        """BM25-style sparse search using TF-IDF"""
        query_vec = self.tfidf_vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        doc_ids = list(self.documents.keys())
        results = [(doc_ids[i], similarities[i]) for i in range(len(doc_ids))]
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]
    
    def dense_search(self, query, top_k=50):
        """Dense embedding search"""
        query_embedding = self.dense_model.encode([query])
        similarities = cosine_similarity(query_embedding, self.doc_embeddings).flatten()
        
        doc_ids = list(self.documents.keys())
        results = [(doc_ids[i], similarities[i]) for i in range(len(doc_ids))]
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]
    
    def reciprocal_rank_fusion(self, rankings, k=60):
        """Combine multiple rankings using RRF"""
        scores = {}
        for ranking in rankings:
            for rank, (doc_id, _) in enumerate(ranking):
                if doc_id not in scores:
                    scores[doc_id] = 0
                scores[doc_id] += 1 / (k + rank + 1)
        
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    def cross_encoder_rerank(self, query, candidates, top_k=10):
        """Re-rank candidates using cross-encoder"""
        pairs = []
        doc_ids = []
        
        for doc_id, _ in candidates[:20]:  # Only rerank top 20
            pairs.append((query, self.documents[doc_id]['text']))
            doc_ids.append(doc_id)
        
        if not pairs:
            return []
        
        scores = self.cross_encoder.predict(pairs)
        results = list(zip(doc_ids, scores))
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]
    
    def search(self, query, top_k=10, include_summary=True):
        """Complete search pipeline with optional summary"""
        # 1. Sparse and dense search
        sparse_results = self.sparse_search(query, top_k=50)
        dense_results = self.dense_search(query, top_k=50)
        
        # 2. Reciprocal rank fusion
        fused_results = self.reciprocal_rank_fusion([sparse_results, dense_results])
        
        # 3. Cross-encoder re-ranking
        final_results = self.cross_encoder_rerank(query, fused_results, top_k=top_k)
        
        # 4. Filter by score threshold and format results
        formatted_results = []
        conn = sqlite3.connect(self.db_path)
        for doc_id, score in final_results:
            # Skip results with very low relevance scores
            if score < -2.0:
                continue
            # Extract parent PMC ID if this is a sub-entity
            parent_pmc = doc_id.split('_')[0] if '_' in doc_id else doc_id
            
            # Get metadata from parent PMC
            metadata = conn.execute("SELECT predicate, object FROM triples WHERE subject = ? AND predicate IN ('has_title', 'published_in', 'published_year', 'has_author')", (parent_pmc,)).fetchall()
            metadata_dict = {}
            authors_list = []
            for pred, obj in metadata:
                if pred == 'has_author':
                    authors_list.append(obj)
                else:
                    metadata_dict[pred] = obj
            
            # Format authors
            author_str = ', '.join(authors_list[:3])  # Show first 3 authors
            if len(authors_list) > 3:
                author_str += ' et al.'
            
            formatted_results.append({
                'pmc_id': parent_pmc,
                'title': metadata_dict.get('has_title', 'Unknown Title'),
                'journal': metadata_dict.get('published_in', 'Unknown Journal'),
                'year': metadata_dict.get('published_year', 'Unknown Year'),
                'authors': author_str if author_str else 'Unknown Authors',
                'score': float(score)
            })
        conn.close()
        
        # 5. Generate summary if requested
        response = {'results': formatted_results}
        if include_summary:
            response['summary'] = self.generate_summary(query, formatted_results)
        
        return response
    
    def generate_summary(self, query, results):
        """Generate summary using Gemma based on search results"""
        if not results:
            return "No relevant results found."
        
        # Format results for prompt
        results_text = ""
        for i, result in enumerate(results[:5], 1):  # Top 5 results
            results_text += f"{i}. {result['title']}\n"
            authors = result.get('authors', 'Unknown Authors')
            results_text += f"   Authors: {authors} ({result['year']})\n"
            results_text += f"   Journal: {result['journal']}\n\n"
        
        prompt = f"""Based on these search results for "{query}", write a short, clear, and concise summary of the main findings. When mentioning findings, cite them using author names and years in parentheses like (Smith et al., 2023). Keep it under 3 sentences. Do not use markdown formatting, numbered citations, or bullet points:

{results_text}

Summary:"""
        
        try:
            response = requests.post('http://localhost:11434/api/generate',
                                   json={
                                       'model': 'gemma2:2b',
                                       'prompt': prompt,
                                       'stream': False,
                                       'options': {
                                           'temperature': 0.3,
                                           'max_tokens': 200
                                       }
                                   },
                                   timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
        
        except Exception as e:
            print(f"Error generating summary: {e}")
        
        return "Summary generation failed."

def main():
    # Initialize search engine
    current_dir = Path(__file__).parent.parent
    db_path = current_dir / 'create' / 'biology_kg.db'
    
    search_engine = SearchEngine(db_path)
    
    # Example search
    query = "microgravity effects on Arabidopsis gene expression"
    response = search_engine.search(query, top_k=5)
    
    print(f"Search results for: '{query}'\n")
    
    if 'summary' in response:
        print(f"Summary: {response['summary']}\n")
        print("-" * 50)
    
    for i, result in enumerate(response['results'], 1):
        print(f"{i}. {result['title']}")
        print(f"   Journal: {result['journal']} ({result['year']})")
        print(f"   Score: {result['score']:.3f}")
        print()

if __name__ == "__main__":
    main()