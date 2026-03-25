"""Search API routes."""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from models.search import SearchRequest, SearchResponse
from services.search_service import SearchService
from services.reranker_service import RerankerService

router = APIRouter(prefix="/api/search", tags=["search"])

# Initialize services
search_service = SearchService()
reranker_service = RerankerService()


@router.get("", response_model=SearchResponse)
async def search(
    query: str = Query(..., description="Natural language search query"),
    domain: str = Query(default="adas", description="Domain to search"),
    season: Optional[str] = Query(default=None, description="Filter by season"),
    time_of_day: Optional[str] = Query(default=None, description="Filter by time of day"),
    weather: Optional[str] = Query(default=None, description="Filter by weather"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    use_vector_search: bool = Query(default=True, description="Enable vector search"),
    use_text_search: bool = Query(default=True, description="Enable text search"),
    use_reranker: bool = Query(default=True, description="Enable Voyage AI reranker"),
    vector_weight: float = Query(default=0.5, ge=0.0, le=1.0, description="Vector score weight"),
    text_weight: float = Query(default=0.5, ge=0.0, le=1.0, description="Text score weight"),
):
    """
    Perform hybrid multimodal search.
    
    This endpoint combines:
    - MongoDB Atlas vector search (with scalar quantization)
    - Full-text search on text descriptions
    - Metadata pre-filtering (season, time_of_day, weather)
    - Voyage AI reranking for improved relevance
    """
    request = SearchRequest(
        query=query,
        domain=domain,
        season=season,
        time_of_day=time_of_day,
        weather=weather,
        limit=limit,
        use_vector_search=use_vector_search,
        use_text_search=use_text_search,
        use_reranker=use_reranker,
        vector_weight=vector_weight,
        text_weight=text_weight,
    )
    
    # Perform search
    response = search_service.search(request)
    
    # Apply reranker if enabled
    if use_reranker and response.results:
        response = reranker_service.rerank_response(response, top_k=limit)
        # Add reranker to executed queries
        response.executed_queries["reranker"] = {
            "service": "Voyage AI",
            "model": "rerank-2",
            "api_call": {
                "method": "voyageai.Client.rerank()",
                "query": query,
                "documents": f"[{len(response.results)} text descriptions]",
                "top_k": limit
            },
            "note": "Cross-encoder that reads query + document together for deep relevance scoring"
        }
    
    return response


@router.post("", response_model=SearchResponse)
async def search_post(request: SearchRequest):
    """
    Perform hybrid multimodal search (POST variant).
    
    Same as GET but accepts full SearchRequest body.
    """
    response = search_service.search(request)
    
    if request.use_reranker and response.results:
        response = reranker_service.rerank_response(response, top_k=request.limit)
        # Add reranker to executed queries
        response.executed_queries["reranker"] = {
            "service": "Voyage AI",
            "model": "rerank-2",
            "api_call": {
                "method": "voyageai.Client.rerank()",
                "query": request.query,
                "documents": f"[{len(response.results)} text descriptions]",
                "top_k": request.limit
            },
            "note": "Cross-encoder that reads query + document together for deep relevance scoring"
        }
    
    return response
