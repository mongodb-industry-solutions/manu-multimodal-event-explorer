import logging
from pymongo.errors import OperationFailure
from pymongo.operations import SearchIndexModel

from db.mdb import get_mongo_client
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VectorSearchIDXCreator:
    """Create vector search indexes with scalar quantization.
    
    Uses the shared singleton MongoClient to prevent connection leaks.
    """
    
    def __init__(self, collection_name: str, database_name: str = None):
        """Initialize with collection name."""
        self.database_name = database_name or os.getenv("DATABASE_NAME", "multimodal_explorer")
        self.collection_name = collection_name
        self.client = get_mongo_client()
        
        if self.client:
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
        else:
            self.db = None
            self.collection = None
        
        logger.info(f"VectorSearchIDXCreator initialized for {self.collection_name}")

    def create_index(
        self,
        index_name: str,
        vector_field: str,
        dimensions: int = 1024,
        similarity_metric: str = "cosine",
        use_quantization: bool = True,
        filter_fields: list = None
    ) -> dict:
        """Create a vector search index with optional scalar quantization.

        Args:
            index_name: Name for the index
            vector_field: Field containing vectors
            dimensions: Vector dimensions (default 1024)
            similarity_metric: cosine, dotProduct, or euclidean
            use_quantization: Enable scalar quantization (default True)
            filter_fields: List of fields to enable pre-filtering on

        Returns:
            dict: Index creation result
        """
        if not self.collection:
            return {"status": "error", "message": "No MongoDB connection"}
        
        logger.info(f"Creating vector search index '{index_name}'...")
        logger.info(f"  Collection: {self.collection_name}")
        logger.info(f"  Vector Field: {vector_field}")
        logger.info(f"  Dimensions: {dimensions}")
        logger.info(f"  Similarity: {similarity_metric}")
        logger.info(f"  Quantization: {'scalar (int8)' if use_quantization else 'none'}")

        # Build vector field definition
        vector_field_def = {
            "type": "vector",
            "path": vector_field,
            "numDimensions": dimensions,
            "similarity": similarity_metric
        }
        
        # Add scalar quantization if enabled
        if use_quantization:
            vector_field_def["quantization"] = "scalar"
        
        # Build fields list
        fields = [vector_field_def]
        
        # Add filter fields
        if filter_fields:
            for field in filter_fields:
                fields.append({
                    "type": "filter",
                    "path": field
                })
                logger.info(f"  Filter field: {field}")

        # Define the vector search index configuration
        search_index_model = SearchIndexModel(
            definition={"fields": fields},
            name=index_name,
            type="vectorSearch"
        )

        try:
            self.collection.create_search_index(model=search_index_model)
            logger.info(f"Vector search index '{index_name}' created successfully.")
            return {"status": "success", "message": f"Vector search index '{index_name}' created successfully."}
        except OperationFailure as e:
            if "already exists" in str(e).lower() or e.code == 68:
                logger.warning(f"Vector search index '{index_name}' already exists.")
                return {"status": "warning", "message": f"Vector search index '{index_name}' already exists."}
            else:
                logger.error(f"Error creating vector search index: {e}")
                return {"status": "error", "message": f"Error creating vector search index: {e}"}
        except Exception as e:
            logger.error(f"Error creating vector search index: {e}")
            return {"status": "error", "message": f"Error creating vector search index: {e}"}


# Example usage
if __name__ == "__main__":
    # Create index for events_adas collection
    vs_idx = VectorSearchIDXCreator(collection_name="events_adas")
    result = vs_idx.create_index(
        index_name="vector_index",
        vector_field="image_embedding",
        dimensions=1024,
        similarity_metric="cosine",
        use_quantization=True,
        filter_fields=[
            "domain",
            "metadata.season",
            "metadata.time_of_day",
            "metadata.weather"
        ]
    )
    print(result)