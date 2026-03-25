"""Hybrid search service using MongoDB $rankFusion."""

import os
import logging
import time
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv

from models.search import (
    SearchRequest, SearchResponse, SearchResult, SearchScores,
    TimingBreakdown, PipelineStep
)
from models.domain import Domain
from services.embedding_service import EmbeddingService
from db.mdb import get_mongo_client

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SearchService:
    """Hybrid search service using MongoDB $rankFusion.
    
    - Uses $rankFusion to combine $vectorSearch and $search with RRF
    - Falls back to vector-only search if $rankFusion unavailable
    - Single RRF score displayed (no individual vector/text scores)
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,
        database_name: Optional[str] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """Initialize the search service."""
        self.database_name = database_name or os.getenv("DATABASE_NAME", "multimodal_explorer")
        self.client = get_mongo_client()
        self.db = self.client[self.database_name] if self.client else None
        self.embedding_service = embedding_service or EmbeddingService()
        self._last_query_time_ms = 0
    
    def _get_collection(self, domain: str):
        """Get collection for a domain."""
        if self.db is None:
            return None
        domain_config = Domain.get_domain(domain)
        if not domain_config:
            return None
        return self.db[domain_config.collection_name]
    
    def _build_filter(self, request: SearchRequest) -> Dict[str, Any]:
        """Build MongoDB filter from search request."""
        filter_doc = {"domain": request.domain}
        if request.season:
            filter_doc["metadata.season"] = request.season
        if request.time_of_day:
            filter_doc["metadata.time_of_day"] = request.time_of_day
        if request.weather:
            filter_doc["metadata.weather"] = request.weather
        return filter_doc
    
    def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        domain: str = "adas",
        filter_doc: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        vector_weight: float = 0.5,
        text_weight: float = 0.5
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any], float]:
        """Perform hybrid search using $rankFusion.
        
        Returns:
            Tuple of (results, executed_pipeline, time_ms)
        """
        collection = self._get_collection(domain)
        if collection is None:
            return [], {}, 0
        
        # Build vector search pipeline
        vector_pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "image_embedding",
                    "queryVector": query_embedding,
                    "numCandidates": limit * 10,
                    "limit": limit * 2,
                    **({"filter": filter_doc} if filter_doc else {})
                }
            }
        ]
        
        # Build text search pipeline
        text_pipeline = [
            {
                "$search": {
                    "index": "text_search_index",
                    "text": {
                        "query": query,
                        "path": "text_description",
                        "fuzzy": {"maxEdits": 1}
                    }
                }
            },
            {"$limit": limit * 2}
        ]
        
        # $rankFusion pipeline
        pipeline = [
            {
                "$rankFusion": {
                    "input": {
                        "pipelines": {
                            "vector": vector_pipeline,
                            "fulltext": text_pipeline
                        }
                    },
                    "combination": {
                        "weights": {
                            "vector": vector_weight,
                            "fulltext": text_weight
                        }
                    }
                }
            },
            {
                "$addFields": {
                    "rrf_score": {"$meta": "score"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "event_id": 1,
                    "domain": 1,
                    "image_path": 1,
                    "image_url": 1,
                    "text_description": 1,
                    "metadata": 1,
                    "embedding_metadata": 1,
                    "rrf_score": 1
                }
            },
            {"$limit": limit}
        ]
        
        # Display pipeline (without actual embedding)
        display_pipeline = {
            "$rankFusion": {
                "pipelines": ["$vectorSearch (vector_index)", "$search (text_search_index)"],
                "weights": {"vector": vector_weight, "fulltext": text_weight}
            }
        }
        
        start = time.time()
        try:
            results = list(collection.aggregate(pipeline))
            elapsed_ms = round((time.time() - start) * 1000, 1)
            logger.info(f"$rankFusion returned {len(results)} results in {elapsed_ms}ms")
            return results, display_pipeline, elapsed_ms
        except Exception as e:
            logger.warning(f"$rankFusion failed: {e}, falling back to vector search")
            return self.vector_search(query_embedding, domain, filter_doc, limit)
    
    def vector_search(
        self,
        query_embedding: List[float],
        domain: str = "adas",
        filter_doc: Optional[Dict[str, Any]] = None,
        limit: int = 20
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any], float]:
        """Perform vector-only search (fallback)."""
        collection = self._get_collection(domain)
        if collection is None:
            return [], {}, 0
        
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "image_embedding",
                    "queryVector": query_embedding,
                    "numCandidates": limit * 10,
                    "limit": limit,
                    **({"filter": filter_doc} if filter_doc else {})
                }
            },
            {
                "$addFields": {
                    "rrf_score": {"$meta": "vectorSearchScore"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "event_id": 1,
                    "domain": 1,
                    "image_path": 1,
                    "image_url": 1,
                    "text_description": 1,
                    "metadata": 1,
                    "embedding_metadata": 1,
                    "rrf_score": 1
                }
            }
        ]
        
        display_pipeline = {"$vectorSearch": "vector_index (cosine similarity)"}
        
        start = time.time()
        try:
            results = list(collection.aggregate(pipeline))
            elapsed_ms = round((time.time() - start) * 1000, 1)
            logger.info(f"Vector search returned {len(results)} results in {elapsed_ms}ms")
            return results, display_pipeline, elapsed_ms
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return [], {}, 0
    
    def text_search(
        self,
        query: str,
        domain: str = "adas",
        filter_doc: Optional[Dict[str, Any]] = None,
        limit: int = 20
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any], float]:
        """Perform text-only search."""
        collection = self._get_collection(domain)
        if collection is None:
            return [], {}, 0
        
        pipeline = [
            {
                "$search": {
                    "index": "text_search_index",
                    "text": {
                        "query": query,
                        "path": "text_description",
                        "fuzzy": {"maxEdits": 1}
                    }
                }
            },
            {
                "$addFields": {
                    "rrf_score": {"$meta": "searchScore"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "event_id": 1,
                    "domain": 1,
                    "image_path": 1,
                    "image_url": 1,
                    "text_description": 1,
                    "metadata": 1,
                    "embedding_metadata": 1,
                    "rrf_score": 1
                }
            },
            {"$limit": limit}
        ]
        
        if filter_doc and len(filter_doc) > 1:
            pipeline.insert(1, {"$match": filter_doc})
        
        display_pipeline = {"$search": "text_search_index (fuzzy text)"}
        
        start = time.time()
        try:
            results = list(collection.aggregate(pipeline))
            elapsed_ms = round((time.time() - start) * 1000, 1)
            logger.info(f"Text search returned {len(results)} results in {elapsed_ms}ms")
            return results, display_pipeline, elapsed_ms
        except Exception as e:
            logger.error(f"Text search error: {e}")
            return [], {}, 0
    
    def search(self, request: SearchRequest) -> SearchResponse:
        """Perform search based on request parameters."""
        start_time = time.time()
        timing = TimingBreakdown()
        pipeline_steps = []
        executed_queries = {}
        
        # Build filter
        filter_doc = self._build_filter(request)
        has_filters = any([request.season, request.time_of_day, request.weather])
        
        # Pre-filter step
        pipeline_steps.append(PipelineStep(
            name="Pre-filter",
            enabled=has_filters,
            status="completed" if has_filters else "skipped",
            details=f"Filters: {filter_doc}" if has_filters else "No filters applied"
        ))
        
        results = []
        search_method = "none"
        
        # Determine search mode
        use_hybrid = request.use_vector_search and request.use_text_search
        use_vector_only = request.use_vector_search and not request.use_text_search
        use_text_only = request.use_text_search and not request.use_vector_search
        
        # Generate embedding if needed
        query_embedding = None
        if request.use_vector_search:
            embed_start = time.time()
            query_embedding = self.embedding_service.embed_text(request.query)
            timing.embedding_ms = round((time.time() - embed_start) * 1000, 1)
            
            executed_queries["embedding"] = {
                "service": "Voyage AI",
                "model": "voyage-3",
                "dimensions": 1024,
                "time_ms": timing.embedding_ms
            }
        
        if use_hybrid and query_embedding:
            # Hybrid search with $rankFusion
            results, exec_pipeline, search_time = self.hybrid_search(
                query=request.query,
                query_embedding=query_embedding,
                domain=request.domain,
                filter_doc=filter_doc if has_filters else None,
                limit=request.limit,
                vector_weight=request.vector_weight,
                text_weight=request.text_weight
            )
            timing.vector_search_ms = search_time
            search_method = "$rankFusion"
            executed_queries["search"] = exec_pipeline
            
            pipeline_steps.append(PipelineStep(
                name="$rankFusion Hybrid Search",
                enabled=True,
                status="completed",
                result_count=len(results),
                time_ms=search_time,
                details=f"RRF with weights: vector={request.vector_weight}, text={request.text_weight}"
            ))
            
        elif use_vector_only and query_embedding:
            # Vector-only search
            results, exec_pipeline, search_time = self.vector_search(
                query_embedding=query_embedding,
                domain=request.domain,
                filter_doc=filter_doc if has_filters else None,
                limit=request.limit
            )
            timing.vector_search_ms = search_time
            search_method = "$vectorSearch"
            executed_queries["search"] = exec_pipeline
            
            pipeline_steps.append(PipelineStep(
                name="Vector Search",
                enabled=True,
                status="completed",
                result_count=len(results),
                time_ms=search_time,
                details="Cosine similarity search"
            ))
            
        elif use_text_only:
            # Text-only search
            results, exec_pipeline, search_time = self.text_search(
                query=request.query,
                domain=request.domain,
                filter_doc=filter_doc if has_filters else None,
                limit=request.limit
            )
            timing.text_search_ms = search_time
            search_method = "$search"
            executed_queries["search"] = exec_pipeline
            
            pipeline_steps.append(PipelineStep(
                name="Text Search",
                enabled=True,
                status="completed",
                result_count=len(results),
                time_ms=search_time,
                details="Atlas Search with fuzzy matching"
            ))
        
        # Reranker placeholder
        pipeline_steps.append(PipelineStep(
            name="Reranker",
            enabled=request.use_reranker,
            status="pending" if request.use_reranker else "skipped",
            details="Voyage AI rerank-2" if request.use_reranker else "Disabled"
        ))
        
        # Calculate total time
        timing.total_ms = round((time.time() - start_time) * 1000, 1)
        self._last_query_time_ms = timing.total_ms
        
        # Convert to SearchResult objects
        search_results = []
        for r in results:
            metadata = r.get("metadata", {})
            emb_metadata = r.get("embedding_metadata", {})
            rrf_score = r.get("rrf_score", 0)
            
            search_results.append(SearchResult(
                event_id=r["event_id"],
                domain=r.get("domain", request.domain),
                image_path=r.get("image_path", ""),
                image_url=r.get("image_url"),
                text_description=r.get("text_description", ""),
                season=metadata.get("season"),
                time_of_day=metadata.get("time_of_day"),
                weather=metadata.get("weather"),
                rarity_score=metadata.get("rarity_score", 0),
                scores=SearchScores(
                    vector_score=0,  # Not shown separately
                    text_score=0,    # Not shown separately
                    reranker_score=0,
                    combined_score=rrf_score,
                    vector_explanation="",
                    text_explanation="",
                    reranker_explanation="Voyage AI rerank-2 cross-encoder"
                ),
                embedding_dimensions=emb_metadata.get("dimensions", 1024),
                original_bytes=emb_metadata.get("original_bytes", 4096),
                quantized_bytes=emb_metadata.get("quantized_bytes", 1024)
            ))
        
        # Build filters applied
        filters_applied = {}
        if request.season:
            filters_applied["season"] = request.season
        if request.time_of_day:
            filters_applied["time_of_day"] = request.time_of_day
        if request.weather:
            filters_applied["weather"] = request.weather
        
        return SearchResponse(
            results=search_results,
            total_count=len(search_results),
            query=request.query,
            query_time_ms=timing.total_ms,
            timing=timing,
            pipeline_steps=pipeline_steps,
            executed_queries=executed_queries,
            vector_index_type="quantized_scalar",
            filters_applied=filters_applied,
            search_config={
                "use_vector_search": request.use_vector_search,
                "use_text_search": request.use_text_search,
                "use_reranker": request.use_reranker,
                "vector_weight": request.vector_weight,
                "text_weight": request.text_weight,
                "search_method": search_method
            }
        )


    def get_dataset_distributions(self, domain: str = "adas") -> Dict[str, Any]:
        """Return real distributions across ALL documents using a $facet aggregation.

        Unlike search(), this scans every document in the collection so counts
        are always accurate regardless of collection size.
        """
        collection = self._get_collection(domain)
        if collection is None:
            return {"error": "Collection unavailable"}

        pipeline = [
            {"$match": {"domain": domain}},
            {"$facet": {
                "total": [{"$count": "n"}],
                "by_weather": [
                    {"$group": {"_id": "$metadata.weather", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                ],
                "by_season": [
                    {"$group": {"_id": "$metadata.season", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                ],
                "by_time_of_day": [
                    {"$group": {"_id": "$metadata.time_of_day", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                ],
                "rarity_stats": [
                    {"$group": {
                        "_id": None,
                        "avg": {"$avg": "$rarity_score"},
                        "min": {"$min": "$rarity_score"},
                        "max": {"$max": "$rarity_score"},
                    }},
                ],
            }},
        ]

        try:
            result = list(collection.aggregate(pipeline))[0]
        except Exception as e:
            logger.error(f"get_dataset_distributions error: {e}")
            return {"error": str(e)}

        total = result["total"][0]["n"] if result["total"] else 0
        rarity_raw = result["rarity_stats"][0] if result["rarity_stats"] else {}

        return {
            "total_documents": total,
            "weather_distribution": {
                r["_id"]: r["count"] for r in result["by_weather"] if r["_id"]
            },
            "season_distribution": {
                r["_id"]: r["count"] for r in result["by_season"] if r["_id"]
            },
            "time_of_day_distribution": {
                r["_id"]: r["count"] for r in result["by_time_of_day"] if r["_id"]
            },
            "rarity_score_stats": {
                "avg": round(rarity_raw.get("avg") or 0, 3),
                "min": round(rarity_raw.get("min") or 0, 3),
                "max": round(rarity_raw.get("max") or 0, 3),
            },
        }


if __name__ == "__main__":
    service = SearchService()
    request = SearchRequest(query="foggy night driving", domain="adas", limit=10)
    response = service.search(request)
    print(f"Found {response.total_count} results in {response.query_time_ms}ms")
    for r in response.results[:3]:
        print(f"  {r.event_id}: score={r.scores.combined_score:.4f}")
