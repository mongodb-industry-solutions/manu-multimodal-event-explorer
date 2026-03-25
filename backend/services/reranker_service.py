"""Reranker service using Voyage AI."""

import os
import logging
import time
from typing import List, Optional

import voyageai
from dotenv import load_dotenv

from models.search import SearchResult, SearchResponse

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RerankerService:
    """Rerank search results using Voyage AI reranker.
    
    This service handles:
    - Reranking search results for improved relevance
    - Score normalization and combination
    """
    
    RERANKER_MODEL = "rerank-2"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the reranker service.
        
        Args:
            api_key: Voyage AI API key
        """
        self.api_key = api_key or os.getenv("VOYAGE_API_KEY")
        
        if self.api_key:
            self.client = voyageai.Client(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("No Voyage AI API key provided. Reranking will be skipped.")
    
    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: Optional[int] = None
    ) -> List[SearchResult]:
        """Rerank search results.
        
        Args:
            query: Original search query
            results: List of search results to rerank
            top_k: Number of top results to return (default: all)
            
        Returns:
            Reranked list of search results
        """
        if not self.client or not results:
            return results
        
        top_k = top_k or len(results)
        
        try:
            # Extract text descriptions for reranking
            documents = [r.text_description for r in results]
            
            # Perform reranking
            reranking = self.client.rerank(
                query=query,
                documents=documents,
                model=self.RERANKER_MODEL,
                top_k=min(top_k, len(documents))
            )
            
            # Map reranked results back to SearchResult objects
            reranked_results = []
            for item in reranking.results:
                original_result = results[item.index]
                
                # Only update the reranker score - keep original RRF score in combined_score
                original_result.scores.reranker_score = item.relevance_score
                # Don't overwrite combined_score - it has the RRF score
                
                reranked_results.append(original_result)
            
            logger.info(f"Reranked {len(reranked_results)} results")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Reranking error: {e}")
            return results
    
    def rerank_response(
        self,
        response: SearchResponse,
        top_k: Optional[int] = None
    ) -> SearchResponse:
        """Rerank a complete search response.
        
        Args:
            response: Search response to rerank
            top_k: Number of top results to return
            
        Returns:
            Updated search response with reranked results
        """
        if not response.results:
            return response
        
        rerank_start = time.time()
        
        reranked = self.rerank(
            query=response.query,
            results=response.results,
            top_k=top_k
        )
        
        rerank_time = round((time.time() - rerank_start) * 1000, 1)
        
        response.results = reranked
        response.total_count = len(reranked)
        response.search_config["reranker_applied"] = True
        response.search_config["reranker_model"] = self.RERANKER_MODEL
        
        # Update timing if available
        if response.timing:
            response.timing.reranker_ms = rerank_time
            response.timing.total_ms = round(response.timing.total_ms + rerank_time, 1)
            response.query_time_ms = round(response.timing.total_ms, 1)
        
        # Update pipeline step status
        for step in response.pipeline_steps:
            if step.name == "Reranker":
                step.status = "completed"
                step.time_ms = rerank_time
                step.result_count = len(reranked)
                step.details = f"Voyage AI {self.RERANKER_MODEL} ({rerank_time}ms)"
        
        return response


# Example usage
if __name__ == "__main__":
    from models.search import SearchScores
    
    service = RerankerService()
    
    # Test with mock results
    results = [
        SearchResult(
            event_id="mist_00001",
            domain="adas",
            image_path="adas/mist_00001.jpg",
            text_description="Rural road driving in foggy conditions at night in winter",
            scores=SearchScores(vector_score=0.8, text_score=0.6)
        ),
        SearchResult(
            event_id="mist_00002",
            domain="adas",
            image_path="adas/mist_00002.jpg",
            text_description="Clear daytime driving in summer",
            scores=SearchScores(vector_score=0.5, text_score=0.3)
        )
    ]
    
    reranked = service.rerank("foggy night driving", results)
    for r in reranked:
        print(f"{r.event_id}: reranker={r.scores.reranker_score:.3f}, combined={r.scores.combined_score:.3f}")
