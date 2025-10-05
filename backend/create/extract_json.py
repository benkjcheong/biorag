import requests
import json
import time
from pathlib import Path

def extract_kg_entities_with_gemma(content, pmc_id):
    """Use Gemma to extract all knowledge graph entities from paper content"""
    
    prompt = f"""Extract key information from this biology paper. Return ONLY valid JSON in this exact format:

{{
  "publication": {{
    "pmc_id": "PMC1234567",
    "title": "paper title",
    "year": "YYYY",
    "journal": "journal name"
  }},
  "authors": ["author1", "author2"],
  "subjects": {{
    "species": ["species1", "species2"],
    "tissues": ["tissue1", "tissue2"]
  }},
  "methods": {{
    "platforms": ["platform1", "platform2"],
    "assays": ["assay_type1", "assay_type2"]
  }},
  "treatments": [
    {{
      "agent": "treatment_agent",
      "dose": "dose_amount dose_unit",
      "duration": "duration_amount duration_unit"
    }}
  ],
  "results": [
    {{
      "target": "measured_target",
      "effect": "observed_effect",
      "magnitude": "effect_size"
    }}
  ]
}}

Text:
{content[:8000]}

JSON:"""

    try:
        response = requests.post('http://localhost:11434/api/generate',
                               json={
                                   'model': 'gemma2:2b',
                                   'prompt': prompt,
                                   'stream': False,
                                   'options': {
                                       'temperature': 0.1,
                                       'top_p': 0.9
                                   }
                               },
                               timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '').strip()
            
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                return json.loads(json_text)
            
    except Exception as e:
        print(f"Error with Gemma for {pmc_id}: {e}")
    
    return None

def process_files_to_json(input_dir, output_dir):
    """Process files using Gemma to extract JSON data"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    txt_files = list(input_path.glob('PMC*.txt'))
    print(f"Processing {len(txt_files)} files with Gemma...")
    
    processed = 0
    skipped_files = []

    for file_path in txt_files:
        try:
            pmc_id = file_path.stem
            
            # Check if JSON file already exists
            json_file = output_path / f'{pmc_id}_kg.json'
            if json_file.exists():
                continue
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract KG entities from Gemma
            kg_data = extract_kg_entities_with_gemma(content, pmc_id)
            
            if kg_data is None:
                skipped_files.append(pmc_id)
                continue
            
            # Add PMC ID to publication if not already there
            if 'publication' in kg_data:
                kg_data['publication']['pmc_id'] = pmc_id
            
            # Write individual JSON file
            json_file = output_path / f'{pmc_id}_kg.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(kg_data, f, indent=2)
            
            processed += 1
            if processed % 5 == 0:
                print(f"Processed {processed}/{len(txt_files)} files...")
                time.sleep(2)  # Pause to avoid overwhelming the API
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"Completed processing {processed} files")
    print(f"JSON files created in {output_path}")
    if skipped_files:
        print(f"\nSkipped {len(skipped_files)} files:")
        for file_id in skipped_files:
            print(f"  - {file_id}")

def main():
    current_dir = Path(__file__).parent
    input_dir = current_dir / 'unsorted'
    output_dir = current_dir / 'json_output'
    
    print("Starting JSON extraction...")
    process_files_to_json(input_dir, output_dir)
    print("JSON extraction complete!")

if __name__ == "__main__":
    main()