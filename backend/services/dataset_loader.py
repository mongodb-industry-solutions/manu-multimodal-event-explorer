"""Dataset loader service for HuggingFace datasets."""

import os
import logging
from pathlib import Path
from typing import Generator, Dict, Any, Optional, List
from PIL import Image
import io

from datasets import load_dataset, Dataset
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatasetLoader:
    """Load and sample datasets from HuggingFace.
    
    This service handles:
    - Loading datasets with streaming for memory efficiency
    - Sampling a subset for demo purposes
    - Saving images locally to backend/data/images/
    - Auto-detecting dataset schema
    """
    
    def __init__(
        self,
        dataset_id: str = "jongwonryu/MIST-autonomous-driving-dataset",
        images_dir: Optional[str] = None,
        sample_size: int = 500
    ):
        """Initialize the dataset loader.
        
        Args:
            dataset_id: HuggingFace dataset identifier
            images_dir: Directory to save images (default: backend/data/images)
            sample_size: Number of samples to load
        """
        self.dataset_id = dataset_id
        # Use passed sample_size directly (CLI arg takes precedence)
        self.sample_size = sample_size
        
        # Set up images directory
        if images_dir:
            self.images_dir = Path(images_dir)
        else:
            # Default to backend/data/images relative to this file
            backend_dir = Path(__file__).parent.parent
            self.images_dir = backend_dir / "data" / "images"
        
        self.images_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Images will be saved to: {self.images_dir}")
        
        self._dataset = None
        self._schema = None
    
    def inspect_schema(self) -> Dict[str, Any]:
        """Inspect the dataset schema without downloading all data.
        
        Returns:
            Dictionary with column names, types, and sample values
        """
        logger.info(f"Inspecting schema for dataset: {self.dataset_id}")
        
        # Load with streaming to avoid downloading everything
        dataset = load_dataset(self.dataset_id, split="train", streaming=True)
        
        # Get first sample to inspect structure
        first_sample = next(iter(dataset))
        
        schema = {
            "columns": {},
            "sample": {}
        }
        
        for key, value in first_sample.items():
            value_type = type(value).__name__
            if hasattr(value, 'mode'):  # PIL Image
                value_type = f"PIL.Image ({value.mode}, {value.size})"
                schema["sample"][key] = f"<Image {value.size}>"
            elif isinstance(value, bytes):
                value_type = f"bytes ({len(value)} bytes)"
                schema["sample"][key] = f"<bytes {len(value)}>"
            else:
                schema["sample"][key] = value
            
            schema["columns"][key] = value_type
        
        self._schema = schema
        logger.info(f"Schema inspected. Columns: {list(schema['columns'].keys())}")
        return schema
    
    def load_samples(
        self, 
        domain: str = "adas",
        split: str = "test",
        diverse: bool = True
    ) -> Generator[Dict[str, Any], None, None]:
        """Load and yield samples from the dataset.
        
        Args:
            domain: Domain identifier for organizing images
            split: Dataset split to use
            diverse: If True, sample from different parts of dataset for variety
            
        Yields:
            Dictionary with raw sample data and saved image path
        """
        logger.info(f"Loading {self.sample_size} samples from {self.dataset_id}")
        
        # Create domain subdirectory
        domain_dir = self.images_dir / domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        
        # Load dataset with streaming
        dataset = load_dataset(self.dataset_id, split=split, streaming=True)
        
        if diverse:
            # Sample evenly across the dataset for variety
            # MIST dataset has ~10k images, organized by conditions
            # We'll use skip sampling to get diverse conditions
            yield from self._load_diverse_samples(dataset, domain, domain_dir)
        else:
            yield from self._load_sequential_samples(dataset, domain, domain_dir)
    
    def _load_diverse_samples(
        self, 
        dataset, 
        domain: str, 
        domain_dir: Path
    ) -> Generator[Dict[str, Any], None, None]:
        """Sample from different parts of the dataset for variety.
        
        The MIST dataset is organized with similar images grouped together.
        This method skips through to get diverse weather/time conditions.
        """
        # Collect samples with different text labels
        seen_texts = set()
        samples_per_condition = max(5, self.sample_size // 20)  # At least 5 per condition
        condition_counts = {}
        
        count = 0
        skipped = 0
        
        for idx, sample in enumerate(dataset):
            if count >= self.sample_size:
                break
            
            # Get the text label for this sample
            text_label = sample.get('text', '')
            
            # Limit samples per condition for variety
            if text_label in condition_counts:
                if condition_counts[text_label] >= samples_per_condition:
                    skipped += 1
                    continue
                condition_counts[text_label] += 1
            else:
                condition_counts[text_label] = 1
                if text_label:
                    logger.info(f"Found new condition: {text_label}")
            
            # Generate event_id from index
            event_id = f"mist_{idx:05d}"
            image_filename = f"{event_id}.jpg"
            image_path = domain_dir / image_filename
            relative_path = f"{domain}/{image_filename}"
            
            # Save image if it's a PIL Image
            image_saved = False
            for key, value in sample.items():
                if hasattr(value, 'save'):  # PIL Image
                    if value.mode != 'RGB':
                        value = value.convert('RGB')
                    value.save(image_path, "JPEG", quality=85)
                    image_saved = True
                    break
            
            if not image_saved:
                continue
            
            yield {
                "raw_sample": sample,
                "event_id": event_id,
                "image_path": relative_path,
                "source_index": idx,
                "domain": domain
            }
            
            count += 1
            if count % 50 == 0:
                logger.info(f"Processed {count}/{self.sample_size} samples (skipped {skipped} for variety)")
        
        logger.info(f"Finished loading {count} diverse samples from {len(condition_counts)} conditions")
        logger.info(f"Conditions found: {list(condition_counts.keys())}")
    
    def _load_sequential_samples(
        self, 
        dataset, 
        domain: str, 
        domain_dir: Path
    ) -> Generator[Dict[str, Any], None, None]:
        """Load samples sequentially (original behavior)."""
        count = 0
        for idx, sample in enumerate(dataset):
            if count >= self.sample_size:
                break
            
            event_id = f"mist_{idx:05d}"
            image_filename = f"{event_id}.jpg"
            image_path = domain_dir / image_filename
            relative_path = f"{domain}/{image_filename}"
            
            # Save image
            image_saved = False
            for key, value in sample.items():
                if hasattr(value, 'save'):
                    if value.mode != 'RGB':
                        value = value.convert('RGB')
                    value.save(image_path, "JPEG", quality=85)
                    image_saved = True
                    break
            
            if not image_saved:
                continue
            
            yield {
                "raw_sample": sample,
                "event_id": event_id,
                "image_path": relative_path,
                "source_index": idx,
                "domain": domain
            }
            
            count += 1
            if count % 100 == 0:
                logger.info(f"Processed {count}/{self.sample_size} samples")
        
        logger.info(f"Finished loading {count} samples")
    
    def get_image_columns(self) -> List[str]:
        """Get column names that contain images."""
        if not self._schema:
            self.inspect_schema()
        
        image_cols = []
        for col, dtype in self._schema["columns"].items():
            if "PIL.Image" in dtype or "image" in col.lower():
                image_cols.append(col)
        return image_cols
    
    def get_text_columns(self) -> List[str]:
        """Get column names that contain text."""
        if not self._schema:
            self.inspect_schema()
        
        text_cols = []
        for col, dtype in self._schema["columns"].items():
            if dtype == "str":
                text_cols.append(col)
        return text_cols


# Example usage
if __name__ == "__main__":
    loader = DatasetLoader(sample_size=5)
    
    print("=== Schema Inspection ===")
    schema = loader.inspect_schema()
    print(f"Columns: {schema['columns']}")
    print(f"Sample: {schema['sample']}")
    
    print("\n=== Loading Samples ===")
    for sample in loader.load_samples():
        print(f"Event ID: {sample['event_id']}")
        print(f"Image path: {sample['image_path']}")
        print(f"Raw keys: {sample['raw_sample'].keys()}")
        print("---")
