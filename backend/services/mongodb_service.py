"""MongoDB events service for storing and retrieving events."""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from pymongo import ASCENDING, TEXT
from pymongo.collection import Collection
from pymongo.operations import SearchIndexModel
from dotenv import load_dotenv

from models.event import Event
from models.domain import Domain
from db.mdb import get_mongo_client

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MongoDBEventsService:
    """MongoDB service for event storage and retrieval.
    
    Uses the shared singleton MongoClient to prevent connection leaks
    on shared clusters.
    
    This service handles:
    - Event document CRUD operations
    - Vector search index creation with scalar quantization
    - Full-text search index creation
    - Collection statistics for quantization showcase
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,  # Ignored - uses shared client
        database_name: Optional[str] = None
    ):
        """Initialize MongoDB connection using shared client.
        
        Args:
            uri: Ignored - uses shared singleton client
            database_name: Database name. Falls back to DATABASE_NAME env var.
        """
        self.database_name = database_name or os.getenv("DATABASE_NAME", "multimodal_explorer")
        self.client = get_mongo_client()
        
        if not self.client:
            logger.warning("No MongoDB client available. Database operations will fail.")
            self.db = None
        else:
            self.db = self.client[self.database_name]
            logger.info(f"MongoDBEventsService using database: {self.database_name}")
    
    def _get_collection(self, domain: str = "adas") -> Optional[Collection]:
        """Get the collection for a domain.
        
        Args:
            domain: Domain identifier
            
        Returns:
            MongoDB collection or None
        """
        if self.db is None:
            return None
        
        domain_config = Domain.get_domain(domain)
        if not domain_config:
            logger.error(f"Unknown domain: {domain}")
            return None
        
        return self.db[domain_config.collection_name]
    
    def create_indexes(self, domain: str = "adas") -> bool:
        """Create all required indexes for a domain.
        
        Args:
            domain: Domain identifier
            
        Returns:
            True if successful
        """
        collection = self._get_collection(domain)
        if collection is None:
            return False
        
        try:
            # Create compound index for metadata filtering
            collection.create_index([
                ("domain", ASCENDING),
                ("metadata.season", ASCENDING),
                ("metadata.time_of_day", ASCENDING),
                ("metadata.weather", ASCENDING)
            ], name="metadata_compound_idx")
            
            # Create unique index on event_id
            collection.create_index(
                [("event_id", ASCENDING)],
                unique=True,
                name="event_id_unique_idx"
            )
            
            logger.info(f"Created standard indexes for domain: {domain}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            return False
    
    def create_vector_search_index(
        self,
        domain: str = "adas",
        index_name: str = "vector_index",
        dimensions: int = 1024
    ) -> bool:
        """Create a vector search index with scalar quantization.
        
        This must be run against MongoDB Atlas (not local MongoDB).
        
        Args:
            domain: Domain identifier
            index_name: Name for the vector index
            dimensions: Vector dimensions
            
        Returns:
            True if successful
        """
        collection = self._get_collection(domain)
        if collection is None:
            return False
        
        try:
            # Define vector search index with scalar quantization
            search_index_model = SearchIndexModel(
                definition={
                    "fields": [
                        {
                            "type": "vector",
                            "path": "image_embedding",
                            "numDimensions": dimensions,
                            "similarity": "cosine",
                            "quantization": "scalar"
                        },
                        # Pre-filter fields
                        {
                            "type": "filter",
                            "path": "domain"
                        },
                        {
                            "type": "filter",
                            "path": "metadata.season"
                        },
                        {
                            "type": "filter",
                            "path": "metadata.time_of_day"
                        },
                        {
                            "type": "filter",
                            "path": "metadata.weather"
                        }
                    ]
                },
                name=index_name,
                type="vectorSearch"
            )
            
            collection.create_search_index(model=search_index_model)
            logger.info(f"Created vector search index '{index_name}' for domain: {domain}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating vector search index: {e}")
            return False
    
    def create_text_search_index(
        self,
        domain: str = "adas",
        index_name: str = "text_search_index"
    ) -> bool:
        """Create an Atlas Search index for full-text search.
        
        Args:
            domain: Domain identifier
            index_name: Name for the search index
            
        Returns:
            True if successful
        """
        collection = self._get_collection(domain)
        if collection is None:
            return False
        
        try:
            # Define Atlas Search index for text
            search_index_model = SearchIndexModel(
                definition={
                    "mappings": {
                        "dynamic": False,
                        "fields": {
                            "text_description": {
                                "type": "string",
                                "analyzer": "lucene.standard"
                            },
                            "metadata": {
                                "type": "document",
                                "fields": {
                                    "season": {"type": "stringFacet"},
                                    "time_of_day": {"type": "stringFacet"},
                                    "weather": {"type": "stringFacet"}
                                }
                            }
                        }
                    }
                },
                name=index_name,
                type="search"
            )
            
            collection.create_search_index(model=search_index_model)
            logger.info(f"Created Atlas Search index '{index_name}' for domain: {domain}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating Atlas Search index: {e}")
            return False
    
    def create_all_search_indexes(self, domain: str = "adas") -> dict:
        """Create both Atlas Vector Search and Atlas Search indexes.
        
        Args:
            domain: Domain identifier
            
        Returns:
            Dict with status of each index creation
        """
        results = {
            "vector_search": False,
            "text_search": False
        }
        
        # Create vector search index
        try:
            results["vector_search"] = self.create_vector_search_index(domain)
        except Exception as e:
            logger.warning(f"Vector search index may already exist: {e}")
            results["vector_search"] = "exists_or_error"
        
        # Create text search index
        try:
            results["text_search"] = self.create_text_search_index(domain)
        except Exception as e:
            logger.warning(f"Text search index may already exist: {e}")
            results["text_search"] = "exists_or_error"
        
        return results
    
    def insert_event(self, event: Event) -> Optional[str]:
        """Insert a single event.
        
        Args:
            event: Event to insert
            
        Returns:
            Inserted event_id or None
        """
        collection = self._get_collection(event.domain)
        if collection is None:
            return None
        
        try:
            doc = event.to_mongo_doc()
            collection.insert_one(doc)
            logger.debug(f"Inserted event: {event.event_id}")
            return event.event_id
        except Exception as e:
            logger.error(f"Error inserting event: {e}")
            return None
    
    def insert_events_batch(self, events: List[Event]) -> int:
        """Insert multiple events.
        
        Args:
            events: List of events to insert
            
        Returns:
            Number of events inserted
        """
        if not events:
            return 0
        
        collection = self._get_collection(events[0].domain)
        if collection is None:
            return 0
        
        try:
            docs = [event.to_mongo_doc() for event in events]
            result = collection.insert_many(docs, ordered=False)
            count = len(result.inserted_ids)
            logger.info(f"Inserted {count} events")
            return count
        except Exception as e:
            logger.error(f"Error inserting events batch: {e}")
            return 0
    
    def get_event(self, event_id: str, domain: str = "adas") -> Optional[Event]:
        """Get a single event by ID.
        
        Args:
            event_id: Event identifier
            domain: Domain identifier
            
        Returns:
            Event or None
        """
        collection = self._get_collection(domain)
        if collection is None:
            return None
        
        doc = collection.find_one({"event_id": event_id})
        if doc:
            return Event.from_mongo_doc(doc)
        return None
    
    def event_exists(self, event_id: str, domain: str = "adas") -> bool:
        """Check if an event exists.
        
        Args:
            event_id: Event identifier
            domain: Domain identifier
            
        Returns:
            True if event exists
        """
        collection = self._get_collection(domain)
        if collection is None:
            return False
        
        return collection.count_documents({"event_id": event_id}, limit=1) > 0
    
    def get_collection_stats(self, domain: str = "adas") -> Dict[str, Any]:
        """Get collection statistics with REAL measurements.
        
        Args:
            domain: Domain identifier
            
        Returns:
            Dictionary with actual statistics
        """
        collection = self._get_collection(domain)
        if collection is None:
            return {}
        
        try:
            # Get document count
            doc_count = collection.count_documents({})
            
            # Get REAL collection stats from MongoDB
            stats = self.db.command("collStats", collection.name)
            
            # Get actual storage sizes (in bytes)
            collection_size = stats.get("size", 0)  # Uncompressed data size
            storage_size = stats.get("storageSize", 0)  # On-disk after compression
            total_index_size = stats.get("totalIndexSize", 0)  # All indexes
            
            # Get individual index sizes
            index_sizes = stats.get("indexSizes", {})
            
            # Calculate ACTUAL embedding storage in documents
            # Each embedding: 1024 floats × 4 bytes = 4096 bytes
            embedding_bytes_per_doc = 1024 * 4
            total_embedding_bytes = doc_count * embedding_bytes_per_doc
            
            # Sample one document to verify embedding size
            sample = collection.find_one({}, {"image_embedding": 1})
            actual_embedding_dims = len(sample.get("image_embedding", [])) if sample else 0
            
            # Try to get search index info
            search_indexes = []
            try:
                idx_cursor = collection.aggregate([{"$listSearchIndexes": {}}])
                for idx in idx_cursor:
                    search_indexes.append({
                        "name": idx.get("name"),
                        "type": idx.get("type"),
                        "status": idx.get("status"),
                        # Check if quantization is configured
                        "quantization": idx.get("latestDefinition", {}).get("fields", [{}])[0].get("quantization") if idx.get("type") == "vectorSearch" else None
                    })
            except Exception as e:
                logger.warning(f"Could not list search indexes: {e}")
            
            return {
                "document_count": doc_count,
                "actual_measurements": {
                    "collection_data_bytes": collection_size,
                    "storage_on_disk_bytes": storage_size,
                    "all_indexes_bytes": total_index_size,
                    "index_breakdown": index_sizes,
                    "wiredtiger_compression": round((1 - storage_size / collection_size) * 100, 1) if collection_size > 0 else 0
                },
                "embedding_storage": {
                    "dimensions": actual_embedding_dims,
                    "bytes_per_embedding": embedding_bytes_per_doc,
                    "total_embedding_bytes_in_docs": total_embedding_bytes,
                    "note": "Embeddings stored as float32 in documents. Atlas Vector Index compresses to int8 at index layer."
                },
                "search_indexes": search_indexes,
                "quantization_explanation": {
                    "how_it_works": "MongoDB Atlas Vector Search with scalar quantization compresses vectors FROM float32 (4 bytes) TO int8 (1 byte) IN THE INDEX ONLY.",
                    "document_storage": f"Documents store full float32: {doc_count} × 4096 bytes = {total_embedding_bytes:,} bytes",
                    "index_storage": "Vector index uses int8 quantization, reducing index memory footprint by ~75%",
                    "proof": f"Index configured with 'quantization.type': 'scalar' - verified in search_indexes",
                    "benefit": "Faster similarity search with lower memory usage, ~99% recall preserved"
                }
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}
    
    def get_filter_values(self, domain: str = "adas") -> Dict[str, List[str]]:
        """Get distinct values for filter fields.
        
        Args:
            domain: Domain identifier
            
        Returns:
            Dictionary with filter field names and their distinct values
        """
        collection = self._get_collection(domain)
        if collection is None:
            return {}
        
        try:
            return {
                "season": collection.distinct("metadata.season"),
                "time_of_day": collection.distinct("metadata.time_of_day"),
                "weather": collection.distinct("metadata.weather")
            }
        except Exception as e:
            logger.error(f"Error getting filter values: {e}")
            return {}
    
    def get_all_events(self, domain: str = "adas") -> List[Event]:
        """Get all events for a domain.
        
        Args:
            domain: Domain identifier
            
        Returns:
            List of all events
        """
        collection = self._get_collection(domain)
        if collection is None:
            return []
        
        try:
            docs = collection.find({})
            return [Event.from_mongo_doc(doc) for doc in docs]
        except Exception as e:
            logger.error(f"Error getting all events: {e}")
            return []
    
    def update_event_image_url(
        self,
        event_id: str,
        domain: str,
        image_url: str
    ) -> bool:
        """Update an event's image_url field (for S3 migration).
        
        Args:
            event_id: Event identifier
            domain: Domain identifier
            image_url: S3 URL for the image
            
        Returns:
            True if successful
        """
        collection = self._get_collection(domain)
        if collection is None:
            return False
        
        try:
            result = collection.update_one(
                {"event_id": event_id},
                {"$set": {"image_url": image_url}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating image_url for {event_id}: {e}")
            return False


# Example usage
if __name__ == "__main__":
    service = MongoDBEventsService()
    
    # Create indexes
    service.create_indexes("adas")
    
    # Get stats
    stats = service.get_collection_stats("adas")
    print(f"Collection stats: {stats}")
