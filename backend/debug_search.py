#!/usr/bin/env python3
"""Debug script to test search scores."""

import os
from dotenv import load_dotenv
load_dotenv()

from db.mdb import get_mongo_client
from services.embedding_service import EmbeddingService

def main():
    client = get_mongo_client()
    db = client[os.getenv('DATABASE_NAME', 'multimodal_explorer')]
    collection = db['events_adas']
    
    # List search indexes
    print('Search Indexes:')
    for idx in collection.list_search_indexes():
        print(f"  Name: {idx.get('name')}, Type: {idx.get('type')}, Status: {idx.get('status')}")
    
    # Test vector search
    print('\nTesting vector search...')
    emb_svc = EmbeddingService()
    query_emb = emb_svc.embed_text('clear summer daytime')
    
    if query_emb:
        print(f"Query embedding length: {len(query_emb)}")
        
        pipeline = [
            {"$vectorSearch": {
                "index": "vector_index",
                "path": "image_embedding",
                "queryVector": query_emb,
                "numCandidates": 100,
                "limit": 3
            }},
            {"$addFields": {"vector_score": {"$meta": "vectorSearchScore"}}},
            {"$project": {"event_id": 1, "vector_score": 1, "text_description": 1}}
        ]
        
        try:
            results = list(collection.aggregate(pipeline))
            print(f'\nVector results ({len(results)}):')
            for r in results:
                print(f"  {r.get('event_id')}: score={r.get('vector_score')}")
        except Exception as e:
            print(f"Vector search error: {e}")
    
    # Test text search
    print('\nTesting text search...')
    text_pipeline = [
        {"$search": {
            "index": "text_search_index",
            "text": {
                "query": "clear summer daytime",
                "path": "text_description",
                "fuzzy": {"maxEdits": 1}
            }
        }},
        {"$addFields": {"text_score": {"$meta": "searchScore"}}},
        {"$project": {"event_id": 1, "text_score": 1, "text_description": 1}},
        {"$limit": 3}
    ]
    
    try:
        results = list(collection.aggregate(text_pipeline))
        print(f'Text results ({len(results)}):')
        for r in results:
            print(f"  {r.get('event_id')}: score={r.get('text_score')}")
            print(f"    desc: {r.get('text_description', '')[:80]}...")
    except Exception as e:
        print(f"Text search error: {e}")

if __name__ == "__main__":
    main()
