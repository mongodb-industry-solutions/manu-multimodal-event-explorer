"""Stats API routes for quantization showcase."""

from fastapi import APIRouter, Query

from models.domain import Domain
from services.mongodb_service import MongoDBEventsService
from services.embedding_service import EmbeddingService

router = APIRouter(prefix="/api/stats", tags=["stats"])

# Initialize services
mongodb_service = MongoDBEventsService()
embedding_service = EmbeddingService()


@router.get("")
async def get_stats(
    domain: str = Query(default="adas", description="Domain to get stats for")
):
    """
    Get collection and quantization statistics.
    
    This endpoint provides data for the quantization showcase panel,
    demonstrating storage savings and performance benefits.
    """
    # Get collection stats from MongoDB
    collection_stats = mongodb_service.get_collection_stats(domain)
    
    # Get embedding service stats
    embedding_stats = embedding_service.get_usage_stats()
    
    # Get domain info
    domain_config = Domain.get_domain(domain)
    
    return {
        "domain": domain,
        "domain_name": domain_config.name if domain_config else domain,
        "collection": collection_stats,
        "embedding_model": embedding_stats,
        "quantization": {
            "type": "scalar",
            "encoding": "int8",
            "original_bytes_per_vector": 4096,
            "quantized_bytes_per_vector": 1024,
            "savings_percent": 75.0,
            "recall_estimate": "~99%",
            "description": "MongoDB Atlas vector search with scalar quantization compresses 1024-dim float32 vectors to int8, saving 75% storage with minimal recall loss."
        }
    }


@router.get("/summary")
async def get_summary():
    """
    Get a high-level summary across all domains.
    
    Useful for dashboard displays.
    """
    summaries = []
    
    for domain_config in Domain.get_domains():
        if domain_config.enabled:
            stats = mongodb_service.get_collection_stats(domain_config.id)
            summaries.append({
                "domain_id": domain_config.id,
                "domain_name": domain_config.name,
                "icon": domain_config.icon,
                "document_count": stats.get("document_count", 0),
                "vector_storage": stats.get("vector_storage", {})
            })
    
    total_docs = sum(s["document_count"] for s in summaries)
    
    return {
        "domains": summaries,
        "total_documents": total_docs,
        "quantization_savings_percent": 75.0
    }
