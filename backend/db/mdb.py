import os
import logging
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Singleton MongoClient instance - SHARED across all services
_client: MongoClient = None


def get_mongo_client() -> MongoClient:
    """Get the singleton MongoDB client.
    
    This ensures all services share a single connection pool,
    preventing connection leaks on shared clusters.
    """
    global _client
    
    if _client is None:
        uri = os.getenv("MONGODB_URI")
        appname = os.getenv("APP_NAME", "multimodal-event-explorer")
        
        if not uri:
            logger.warning("No MONGODB_URI provided")
            return None
        
        # Configure connection pool for shared cluster usage.
        # Key settings to prevent connection count from growing:
        #   minPoolSize=0  → no persistent idle connections; sockets only open on demand
        #   maxPoolSize=5  → hard ceiling of 5 connections per process
        #   maxIdleTimeMS=10000 → close sockets unused for 10 s (vs Atlas's ~10 min default)
        _client = MongoClient(
            uri,
            appname=appname,
            # Connection pool settings
            maxPoolSize=5,    # Hard ceiling — keeps Atlas connection count low
            minPoolSize=0,    # Don't hold connections when idle (prevents count creep on reload)
            maxIdleTimeMS=10000,  # Release idle sockets after 10 s
            # Timeouts to prevent hanging
            serverSelectionTimeoutMS=5000,  # 5s to find a server
            connectTimeoutMS=10000,  # 10s to establish connection
            socketTimeoutMS=30000,  # 30s for socket operations
            # Retry settings
            retryWrites=True,
            retryReads=True,
        )
        logger.info(f"MongoDB client initialized (appname={appname}, maxPoolSize=5, minPoolSize=0)")
    
    return _client


def close_mongo_client():
    """Close the MongoDB client connection.
    
    Call this on application shutdown to properly release resources.
    """
    global _client
    
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB client closed")


class MongoDBConnector:
    """ A class to provide access to a MongoDB database.
    This class uses the shared singleton MongoClient to prevent connection leaks.

    Attributes:
        database_name (str): The name of the database to connect to.
    """

    def __init__(self, uri=None, database_name=None, appname=None):
        """ Initialize the MongoDBConnector instance. 
        
        Note: uri and appname params are ignored - uses singleton client.
        """
        self.database_name = database_name or os.getenv("DATABASE_NAME")
        self.client = get_mongo_client()
        self.db = self.client[self.database_name] if self.client else None

    def get_collection(self, collection_name):
        """Retrieve a collection."""
        if not collection_name:
            raise ValueError("Collection name must be provided.")
        if self.db is None:
            raise RuntimeError("MongoDB not connected")
        return self.db[collection_name]

    def insert_one(self, collection_name, document):
        """Insert a single document into a collection."""
        collection = self.get_collection(collection_name)
        result = collection.insert_one(document)
        return result.inserted_id

    def insert_many(self, collection_name, documents):
        """Insert multiple documents into a collection."""
        collection = self.get_collection(collection_name)
        result = collection.insert_many(documents)
        return result.inserted_ids

    def find(self, collection_name, query={}, projection=None):
        """Retrieve documents from a collection."""
        collection = self.get_collection(collection_name)
        return list(collection.find(query, projection))

    def update_one(self, collection_name, query, update, upsert=False):
        """Update a single document in a collection."""
        collection = self.get_collection(collection_name)
        result = collection.update_one(query, update, upsert=upsert)
        return result.modified_count

    def update_many(self, collection_name, query, update, upsert=False):
        """Update multiple documents in a collection."""
        collection = self.get_collection(collection_name)
        result = collection.update_many(query, update, upsert=upsert)
        return result.modified_count

    def delete_one(self, collection_name, query):
        """Delete a single document from a collection."""
        collection = self.get_collection(collection_name)
        result = collection.delete_one(query)
        return result.deleted_count

    def delete_many(self, collection_name, query):
        """Delete multiple documents from a collection."""
        collection = self.get_collection(collection_name)
        result = collection.delete_many(query)
        return result.deleted_count