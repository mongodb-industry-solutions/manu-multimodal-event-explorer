#!/usr/bin/env python3
"""
Standalone script to create Atlas Search indexes on an existing collection.
Run this AFTER importing data via Compass.

Usage:
    uv run python create_search_indexes.py
"""

import os
import sys
import logging
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.operations import SearchIndexModel

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_client():
    """Get MongoDB client."""
    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("ERROR: MONGODB_URI not set in .env")
        sys.exit(1)
    
    return MongoClient(
        uri,
        appname="create-indexes",
        serverSelectionTimeoutMS=5000
    )


def create_standard_indexes(collection):
    """Create standard MongoDB indexes."""
    print("\n📋 Creating standard indexes...")
    
    try:
        # Compound index for metadata filtering
        collection.create_index([
            ("domain", ASCENDING),
            ("metadata.season", ASCENDING),
            ("metadata.time_of_day", ASCENDING),
            ("metadata.weather", ASCENDING)
        ], name="metadata_compound_idx")
        print("  ✅ metadata_compound_idx created")
        
        # Unique index on event_id
        collection.create_index(
            [("event_id", ASCENDING)],
            unique=True,
            name="event_id_unique_idx"
        )
        print("  ✅ event_id_unique_idx created")
        
        return True
    except Exception as e:
        print(f"  ⚠️ Index may already exist: {e}")
        return True


def create_vector_search_index(collection, index_name="vector_index"):
    """Create vector search index with scalar quantization."""
    print(f"\n🔍 Creating vector search index '{index_name}'...")
    
    search_index_model = SearchIndexModel(
        definition={
            "fields": [
                {
                    "type": "vector",
                    "path": "image_embedding",
                    "numDimensions": 1024,
                    "similarity": "cosine",
                    "quantization": "scalar"  # int8 quantization!
                },
                {"type": "filter", "path": "domain"},
                {"type": "filter", "path": "metadata.season"},
                {"type": "filter", "path": "metadata.time_of_day"},
                {"type": "filter", "path": "metadata.weather"}
            ]
        },
        name=index_name,
        type="vectorSearch"
    )
    
    try:
        collection.create_search_index(model=search_index_model)
        print(f"  ✅ {index_name} created (with scalar quantization)")
        return True
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"  ⚠️ {index_name} already exists")
            return True
        print(f"  ❌ Error: {e}")
        return False


def create_text_search_index(collection, index_name="text_search_index"):
    """Create Atlas Search index for full-text search."""
    print(f"\n📝 Creating text search index '{index_name}'...")
    
    search_index_model = SearchIndexModel(
        definition={
            "mappings": {
                "dynamic": False,
                "fields": {
                    "text_description": {
                        "type": "string",
                        "analyzer": "lucene.standard"
                    },
                    "domain": {
                        "type": "string"
                    }
                }
            }
        },
        name=index_name,
        type="search"
    )
    
    try:
        collection.create_search_index(model=search_index_model)
        print(f"  ✅ {index_name} created")
        return True
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"  ⚠️ {index_name} already exists")
            return True
        print(f"  ❌ Error: {e}")
        return False


def verify_collection(collection):
    """Check collection has data."""
    count = collection.count_documents({})
    print(f"\n📊 Collection '{collection.name}' has {count} documents")
    
    if count == 0:
        print("  ⚠️ WARNING: Collection is empty! Import data first.")
        return False
    
    # Check a sample document
    sample = collection.find_one({}, {"event_id": 1, "image_embedding": 1})
    if sample:
        has_embedding = "image_embedding" in sample and sample["image_embedding"]
        embedding_len = len(sample.get("image_embedding", [])) if has_embedding else 0
        print(f"  Sample event_id: {sample.get('event_id')}")
        print(f"  Has embedding: {has_embedding} ({embedding_len} dimensions)")
    
    return True


def list_existing_indexes(collection):
    """List all search indexes."""
    print("\n📑 Existing search indexes:")
    try:
        indexes = list(collection.list_search_indexes())
        if not indexes:
            print("  (none)")
        for idx in indexes:
            name = idx.get("name", "unknown")
            idx_type = idx.get("type", "unknown")
            status = idx.get("status", "unknown")
            print(f"  - {name} ({idx_type}) - {status}")
        return indexes
    except Exception as e:
        print(f"  Could not list indexes: {e}")
        return []


def main():
    print("=" * 60)
    print("Atlas Search Index Creator")
    print("=" * 60)
    
    database_name = os.getenv("DATABASE_NAME", "manu-multimodal-explorer")
    collection_name = "events_adas"
    
    print(f"\nConnecting to database: {database_name}")
    print(f"Collection: {collection_name}")
    
    client = get_client()
    db = client[database_name]
    collection = db[collection_name]
    
    # Verify connection
    try:
        client.admin.command('ping')
        print("✅ Connected to MongoDB Atlas")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)
    
    # Verify collection has data
    if not verify_collection(collection):
        print("\n⚠️ Import data via Compass first, then run this script again.")
        client.close()
        sys.exit(1)
    
    # List existing indexes
    list_existing_indexes(collection)
    
    # Create indexes
    create_standard_indexes(collection)
    create_vector_search_index(collection)
    create_text_search_index(collection)
    
    # Final check
    print("\n" + "=" * 60)
    print("Final Index Status:")
    list_existing_indexes(collection)
    
    print("\n✅ Done! Search indexes may take 1-2 minutes to build.")
    print("   Check Atlas UI → Search Indexes to monitor progress.")
    
    client.close()


if __name__ == "__main__":
    main()
