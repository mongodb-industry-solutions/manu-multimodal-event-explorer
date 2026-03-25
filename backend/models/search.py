"""Search request and response models."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SearchScores(BaseModel):
    """Breakdown of search scores for transparency.
    
    Score Explanations:
    - vector_score: Cosine similarity (0-1) between query embedding and document embedding.
      Higher = more semantically similar. 0.98 means very close in vector space.
    - text_score: Atlas Search relevance score, normalized to 0-1.
      Based on term frequency and document matching.
    - reranker_score: Voyage AI reranker relevance (0-1).
      Uses cross-encoder to deeply compare query-document pairs.
      Often LOWER than initial scores because it's more discriminating.
    - combined_score: Weighted combination of above scores.
    """
    vector_score: float = Field(default=0.0, description="Cosine similarity (0-1)")
    text_score: float = Field(default=0.0, description="Atlas Search relevance (normalized 0-1)")
    reranker_score: float = Field(default=0.0, description="Voyage AI reranker relevance (0-1)")
    combined_score: float = Field(default=0.0, description="Final weighted score")
    
    # Score explanations for UI
    vector_explanation: str = Field(default="", description="What vector score means")
    text_explanation: str = Field(default="", description="What text score means")
    reranker_explanation: str = Field(default="", description="What reranker score means")


class SearchRequest(BaseModel):
    """Search request parameters."""
    query: str = Field(..., description="Natural language search query")
    domain: str = Field(default="adas", description="Domain to search in")
    
    # Filters
    season: Optional[str] = Field(default=None, description="Filter by season")
    time_of_day: Optional[str] = Field(default=None, description="Filter by time of day")
    weather: Optional[str] = Field(default=None, description="Filter by weather")
    
    # Pagination and limits
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    
    # Search configuration
    use_vector_search: bool = Field(default=True)
    use_text_search: bool = Field(default=True)
    use_reranker: bool = Field(default=True)
    vector_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    text_weight: float = Field(default=0.5, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    """Single search result with scores."""
    event_id: str
    domain: str
    image_path: str
    image_url: Optional[str] = None
    text_description: str
    
    # Metadata
    season: Optional[str] = None
    time_of_day: Optional[str] = None
    weather: Optional[str] = None
    rarity_score: float = 0.0
    
    # Scores
    scores: SearchScores = Field(default_factory=SearchScores)
    
    # Embedding metadata for quantization showcase
    embedding_dimensions: int = 1024
    original_bytes: int = 4096
    quantized_bytes: int = 1024


class TimingBreakdown(BaseModel):
    """Breakdown of search timing for transparency."""
    embedding_ms: float = Field(default=0.0, description="Time to generate query embedding")
    vector_search_ms: float = Field(default=0.0, description="Time for vector search")
    text_search_ms: float = Field(default=0.0, description="Time for text search")
    reranker_ms: float = Field(default=0.0, description="Time for reranking")
    total_ms: float = Field(default=0.0, description="Total query time")


class PipelineStep(BaseModel):
    """Single step in the search pipeline for visualization."""
    name: str
    enabled: bool
    status: str = "pending"  # pending, running, completed, skipped
    result_count: int = 0
    time_ms: float = 0.0
    details: str = ""


class SearchResponse(BaseModel):
    """Search response with results and metadata."""
    results: List[SearchResult]
    total_count: int
    query: str
    
    # Performance metrics for quantization showcase
    query_time_ms: float = Field(description="Time to execute search in milliseconds")
    vector_index_type: str = Field(default="quantized_scalar", description="Index type used")
    
    # Timing breakdown for transparency
    timing: Optional[TimingBreakdown] = None
    
    # Pipeline visualization
    pipeline_steps: List[PipelineStep] = Field(default_factory=list)
    
    # Executed queries for transparency
    executed_queries: Dict[str, Any] = Field(
        default_factory=dict,
        description="Actual MongoDB queries executed"
    )
    
    # Aggregated stats
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    search_config: Dict[str, Any] = Field(default_factory=dict)
