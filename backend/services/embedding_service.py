"""Voyage AI embedding service for multimodal embeddings."""

import os
import logging
import base64
from pathlib import Path
from typing import List, Optional, Union
from io import BytesIO

import voyageai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate multimodal embeddings using Voyage AI.
    
    This service handles:
    - Text embeddings
    - Image embeddings using voyage-multimodal-3
    - Batch processing with rate limit handling
    """
    
    # Voyage AI multimodal model
    MULTIMODAL_MODEL = "voyage-multimodal-3"
    TEXT_MODEL = "voyage-3"
    EMBEDDING_DIMENSIONS = 1024
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the embedding service.
        
        Args:
            api_key: Voyage AI API key. Falls back to VOYAGE_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("VOYAGE_API_KEY")
        if not self.api_key:
            logger.warning("No Voyage AI API key provided. Embeddings will fail.")
        
        self.client = voyageai.Client(api_key=self.api_key) if self.api_key else None
        
        # Track usage for cost estimation
        self._total_tokens = 0
        self._total_images = 0
    
    def _image_to_base64(self, image_path: Union[str, Path]) -> str:
        """Convert an image file to base64 string.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded image string
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        with open(image_path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")
    
    def _pil_to_base64(self, image: Image.Image, format: str = "JPEG") -> str:
        """Convert a PIL Image to base64 string.
        
        Args:
            image: PIL Image object
            format: Output format (JPEG, PNG)
            
        Returns:
            Base64 encoded image string
        """
        buffer = BytesIO()
        if image.mode != "RGB" and format == "JPEG":
            image = image.convert("RGB")
        image.save(buffer, format=format)
        return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")
    
    def embed_image(
        self,
        image: Union[str, Path, Image.Image],
        images_base_dir: Optional[Path] = None
    ) -> Optional[List[float]]:
        """Generate embedding for a single image.
        
        Args:
            image: Image path (relative or absolute) or PIL Image
            images_base_dir: Base directory for relative paths
            
        Returns:
            Embedding vector as list of floats, or None on error
        """
        if not self.client:
            logger.error("Voyage AI client not initialized")
            return None
        
        try:
            # Load as PIL Image - Voyage AI expects PIL images directly
            if isinstance(image, Image.Image):
                pil_image = image
            else:
                image_path = Path(image)
                if not image_path.is_absolute() and images_base_dir:
                    image_path = images_base_dir / image_path
                pil_image = Image.open(image_path)
            
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Create multimodal input with PIL image
            inputs = [[pil_image]]
            
            # Generate embedding
            result = self.client.multimodal_embed(
                inputs=inputs,
                model=self.MULTIMODAL_MODEL
            )
            
            self._total_images += 1
            return result.embeddings[0]
            
        except Exception as e:
            logger.error(f"Error generating image embedding: {e}")
            return None
    
    def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats, or None on error
        """
        if not self.client:
            logger.error("Voyage AI client not initialized")
            return None
        
        try:
            result = self.client.embed(
                texts=[text],
                model=self.TEXT_MODEL
            )
            
            self._total_tokens += result.total_tokens
            return result.embeddings[0]
            
        except Exception as e:
            logger.error(f"Error generating text embedding: {e}")
            return None
    
    def embed_images_batch(
        self,
        image_paths: List[Union[str, Path]],
        images_base_dir: Optional[Path] = None,
        batch_size: int = 10
    ) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple images.
        
        Args:
            image_paths: List of image paths
            images_base_dir: Base directory for relative paths
            batch_size: Number of images per API call
            
        Returns:
            List of embedding vectors (None for failed images)
        """
        if not self.client:
            logger.error("Voyage AI client not initialized")
            return [None] * len(image_paths)
        
        embeddings = []
        total = len(image_paths)
        
        for i in range(0, total, batch_size):
            batch_paths = image_paths[i:i + batch_size]
            batch_inputs = []
            
            for path in batch_paths:
                try:
                    image_path = Path(path)
                    if not image_path.is_absolute() and images_base_dir:
                        image_path = images_base_dir / image_path
                    
                    # Load as PIL Image - Voyage AI expects PIL images directly
                    pil_image = Image.open(image_path)
                    if pil_image.mode != 'RGB':
                        pil_image = pil_image.convert('RGB')
                    batch_inputs.append([pil_image])
                except Exception as e:
                    logger.error(f"Error loading image {path}: {e}")
                    batch_inputs.append(None)
            
            # Filter out failed loads
            valid_inputs = [inp for inp in batch_inputs if inp is not None]
            valid_indices = [j for j, inp in enumerate(batch_inputs) if inp is not None]
            
            if valid_inputs:
                try:
                    result = self.client.multimodal_embed(
                        inputs=valid_inputs,
                        model=self.MULTIMODAL_MODEL
                    )
                    
                    self._total_images += len(valid_inputs)
                    
                    # Map results back to original positions
                    batch_embeddings = [None] * len(batch_inputs)
                    for j, idx in enumerate(valid_indices):
                        batch_embeddings[idx] = result.embeddings[j]
                    
                    embeddings.extend(batch_embeddings)
                    
                except Exception as e:
                    logger.error(f"Error in batch embedding: {e}")
                    embeddings.extend([None] * len(batch_paths))
            else:
                embeddings.extend([None] * len(batch_paths))
            
            logger.info(f"Embedded {min(i + batch_size, total)}/{total} images")
        
        return embeddings
    
    def get_usage_stats(self) -> dict:
        """Get embedding usage statistics."""
        return {
            "total_images": self._total_images,
            "total_text_tokens": self._total_tokens,
            "model": self.MULTIMODAL_MODEL,
            "dimensions": self.EMBEDDING_DIMENSIONS
        }


# Example usage
if __name__ == "__main__":
    service = EmbeddingService()
    
    # Test text embedding
    text_embedding = service.embed_text("A foggy night on a rural road")
    if text_embedding:
        print(f"Text embedding dimensions: {len(text_embedding)}")
    
    print(f"Usage stats: {service.get_usage_stats()}")
