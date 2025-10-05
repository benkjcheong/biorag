import json
import sqlite3
from pathlib import Path

class KGStorage:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''CREATE TABLE IF NOT EXISTS triples 
                       (subject TEXT, predicate TEXT, object TEXT)''')
        conn.commit()
        conn.close()
    
    def add_triple(self, subject, predicate, obj):
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO triples VALUES (?, ?, ?)",
                    (subject, predicate, obj))
        conn.commit()
        conn.close()

def populate_kg_from_json(kg_storage, json_data, pmc_id):
    """Populate knowledge graph from extracted JSON data"""
    try:
        # Add publication info
        if 'publication' in json_data:
            pub = json_data['publication']
            kg_storage.add_triple(pmc_id, "has_title", pub.get('title', ''))
            kg_storage.add_triple(pmc_id, "published_in", pub.get('journal', ''))
            kg_storage.add_triple(pmc_id, "published_year", pub.get('year', ''))
        
        # Add authors
        if 'authors' in json_data:
            for author in json_data['authors']:
                kg_storage.add_triple(pmc_id, "has_author", author)
        
        # Add subjects
        if 'subjects' in json_data:
            subjects = json_data['subjects']
            for species in subjects.get('species', []):
                kg_storage.add_triple(pmc_id, "studies_species", species)
            for tissue in subjects.get('tissues', []):
                kg_storage.add_triple(pmc_id, "studies_tissue", tissue)
        
        # Add methods
        if 'methods' in json_data:
            methods = json_data['methods']
            for platform in methods.get('platforms', []):
                kg_storage.add_triple(pmc_id, "uses_platform", platform)
            for assay in methods.get('assays', []):
                kg_storage.add_triple(pmc_id, "uses_assay", assay)
        
        # Add treatments
        if 'treatments' in json_data:
            for i, treatment in enumerate(json_data['treatments']):
                treatment_id = f"{pmc_id}_treatment_{i}"
                kg_storage.add_triple(pmc_id, "has_treatment", treatment_id)
                kg_storage.add_triple(treatment_id, "agent", treatment.get('agent', ''))
                kg_storage.add_triple(treatment_id, "dose", treatment.get('dose', ''))
        
        # Add results
        if 'results' in json_data:
            for i, result in enumerate(json_data['results']):
                result_id = f"{pmc_id}_result_{i}"
                kg_storage.add_triple(pmc_id, "has_result", result_id)
                kg_storage.add_triple(result_id, "target", result.get('target', ''))
                kg_storage.add_triple(result_id, "effect", result.get('effect', ''))
    
    except Exception as e:
        print(f"Error populating KG for {pmc_id}: {e}")

def process_json_to_database(json_dir, db_path):
    """Process JSON files and populate database"""
    json_path = Path(json_dir)
    kg_storage = KGStorage(db_path)
    
    json_files = list(json_path.glob('PMC*_kg.json'))
    print(f"Processing {len(json_files)} JSON files...")
    
    processed = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            pmc_id = json_file.stem.replace('_kg', '')
            populate_kg_from_json(kg_storage, json_data, pmc_id)
            
            processed += 1
            if processed % 10 == 0:
                print(f"Processed {processed}/{len(json_files)} files...")
                
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    print(f"Completed processing {processed} JSON files")
    print(f"SQLite database created at {db_path}")

def main():
    current_dir = Path(__file__).parent
    json_dir = current_dir / 'json_output'
    db_path = current_dir / 'biology_kg.db'
    
    print("Starting database population...")
    process_json_to_database(json_dir, db_path)
    print("Database population complete!")

if __name__ == "__main__":
    main()