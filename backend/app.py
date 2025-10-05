from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
from search.search_engine import SearchEngine

app = Flask(__name__)
CORS(app)

print("Starting Flask app...")
current_dir = Path(__file__).parent
db_path = current_dir / 'create' / 'biology_kg.db'
print(f"Database path: {db_path}")
search_engine = SearchEngine(db_path)
print("Search engine initialized")

@app.route('/api/search', methods=['POST'])
def search():
    print(f"Received search request: {request.method}")
    data = request.get_json()
    query = data.get('query', '')
    top_k = data.get('top_k', 10)
    print(f"Query: {query}, top_k: {top_k}")
    
    if not query:
        print("Error: No query provided")
        return jsonify({'error': 'Query is required'}), 400
    
    try:
        results = search_engine.search(query, top_k=top_k, include_summary=True)
        print(f"Search completed, found {len(results)} results")
        return jsonify(results)
    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting server on port 5001...")
    app.run(debug=True, port=5001, host='0.0.0.0')