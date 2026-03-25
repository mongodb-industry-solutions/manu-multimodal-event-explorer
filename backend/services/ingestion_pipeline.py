"""Ingestion pipeline for loading, normalizing, embedding, and storing events."""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone

from dotenv import load_dotenv

# Add backend to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.dataset_loader import DatasetLoader
from services.event_normalizer import EventNormalizer
from services.embedding_service import EmbeddingService
from services.mongodb_service import MongoDBEventsService
from models.event import Event

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrate the ingestion of events from HuggingFace to MongoDB.
    
    Pipeline steps:
    1. Load samples from HuggingFace dataset
    2. Normalize into Event model
    3. Generate embeddings for images
    4. Store in MongoDB with indexes
    """
    
    def __init__(
        self,
        sample_size: int = 500,
        batch_size: int = 10,
        skip_existing: bool = True,
        skip_embeddings: bool = False
    ):
        """Initialize the ingestion pipeline.
        
        Args:
            sample_size: Number of samples to ingest
            batch_size: Batch size for embedding and insertion
            skip_existing: Skip events that already exist in MongoDB
            skip_embeddings: Skip embedding generation (for testing)
        """
        # CLI arg takes precedence over env var
        self.sample_size = sample_size
        self.batch_size = batch_size
        self.skip_existing = skip_existing
        self.skip_embeddings = skip_embeddings
        
        # Initialize services
        self.loader = DatasetLoader(sample_size=self.sample_size)
        self.normalizer = EventNormalizer()
        self.embedding_service = EmbeddingService()
        self.mongodb_service = MongoDBEventsService()
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "skipped_existing": 0,
            "embedded": 0,
            "inserted": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    def inspect_dataset(self) -> dict:
        """Inspect the dataset schema before ingestion.
        
        Returns:
            Schema information
        """
        logger.info("Inspecting dataset schema...")
        schema = self.loader.inspect_schema()
        
        print("\n" + "=" * 60)
        print("DATASET SCHEMA INSPECTION")
        print("=" * 60)
        print(f"\nDataset: {self.loader.dataset_id}")
        print(f"\nColumns:")
        for col, dtype in schema["columns"].items():
            print(f"  - {col}: {dtype}")
        print(f"\nSample values:")
        for col, val in schema["sample"].items():
            val_str = str(val)[:100] + "..." if len(str(val)) > 100 else str(val)
            print(f"  - {col}: {val_str}")
        print("=" * 60 + "\n")
        
        return schema
    
    def setup_indexes(self, domain: str = "adas") -> bool:
        """Create MongoDB indexes.
        
        Args:
            domain: Domain to create indexes for
            
        Returns:
            True if successful
        """
        logger.info(f"Creating indexes for domain: {domain}")
        
        # Create standard MongoDB indexes
        success = self.mongodb_service.create_indexes(domain)
        if success:
            logger.info("Standard indexes created successfully")
        else:
            logger.error("Failed to create standard indexes")
            return False
        
        # Create Atlas Search indexes (Vector + Text)
        logger.info("Creating Atlas Search indexes...")
        search_results = self.mongodb_service.create_all_search_indexes(domain)
        logger.info(f"Atlas Search index creation results: {search_results}")
        
        return True
    
    def run(self, domain: str = "adas") -> dict:
        """Run the full ingestion pipeline.
        
        Args:
            domain: Domain to ingest for
            
        Returns:
            Statistics dictionary
        """
        self.stats["start_time"] = datetime.now(timezone.utc)
        logger.info(f"Starting ingestion pipeline for domain: {domain}")
        logger.info(f"Sample size: {self.sample_size}, Batch size: {self.batch_size}")
        
        # Setup indexes
        self.setup_indexes(domain)
        
        # Get images base directory
        images_base_dir = self.loader.images_dir
        
        # Process in batches
        batch: List[Event] = []
        batch_image_paths: List[str] = []
        
        for sample_data in self.loader.load_samples(domain=domain):
            event_id = sample_data["event_id"]
            
            # Check if already exists
            if self.skip_existing and self.mongodb_service.event_exists(event_id, domain):
                logger.debug(f"Skipping existing event: {event_id}")
                self.stats["skipped_existing"] += 1
                continue
            
            # Normalize to Event
            try:
                event = self.normalizer.normalize(
                    raw_sample=sample_data["raw_sample"],
                    event_id=event_id,
                    image_path=sample_data["image_path"],
                    source_index=sample_data["source_index"],
                    domain=domain
                )
                
                batch.append(event)
                batch_image_paths.append(sample_data["image_path"])
                self.stats["total_processed"] += 1
                
            except Exception as e:
                logger.error(f"Error normalizing event {event_id}: {e}")
                self.stats["errors"] += 1
                continue
            
            # Process batch when full
            if len(batch) >= self.batch_size:
                self._process_batch(batch, batch_image_paths, images_base_dir)
                batch = []
                batch_image_paths = []
        
        # Process remaining batch
        if batch:
            self._process_batch(batch, batch_image_paths, images_base_dir)
        
        self.stats["end_time"] = datetime.now(timezone.utc)
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        # Print summary
        print("\n" + "=" * 60)
        print("INGESTION COMPLETE")
        print("=" * 60)
        print(f"Total processed: {self.stats['total_processed']}")
        print(f"Skipped (existing): {self.stats['skipped_existing']}")
        print(f"Embedded: {self.stats['embedded']}")
        print(f"Inserted: {self.stats['inserted']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Duration: {duration:.1f} seconds")
        print("=" * 60 + "\n")
        
        return self.stats
    
    def _process_batch(
        self,
        batch: List[Event],
        image_paths: List[str],
        images_base_dir: Path
    ) -> None:
        """Process a batch of events.
        
        Args:
            batch: List of events to process
            image_paths: Corresponding image paths
            images_base_dir: Base directory for images
        """
        # Generate embeddings
        if not self.skip_embeddings:
            logger.info(f"Generating embeddings for batch of {len(batch)} events...")
            embeddings = self.embedding_service.embed_images_batch(
                image_paths=image_paths,
                images_base_dir=images_base_dir,
                batch_size=self.batch_size
            )
            
            for event, embedding in zip(batch, embeddings):
                if embedding:
                    event.image_embedding = embedding
                    self.stats["embedded"] += 1
                else:
                    logger.warning(f"No embedding generated for {event.event_id}")
        
        # Insert into MongoDB
        inserted = self.mongodb_service.insert_events_batch(batch)
        self.stats["inserted"] += inserted
        
        logger.info(f"Batch complete: {inserted} events inserted")


def main():
    """CLI entry point for the ingestion pipeline."""
    parser = argparse.ArgumentParser(
        description="Ingest events from HuggingFace dataset into MongoDB"
    )
    parser.add_argument(
        "--sample-size", "-n",
        type=int,
        default=500,
        help="Number of samples to ingest (default: 500)"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=10,
        help="Batch size for processing (default: 10)"
    )
    parser.add_argument(
        "--domain", "-d",
        type=str,
        default="adas",
        help="Domain to ingest for (default: adas)"
    )
    parser.add_argument(
        "--inspect-only",
        action="store_true",
        help="Only inspect dataset schema, don't ingest"
    )
    parser.add_argument(
        "--create-indexes-only",
        action="store_true",
        help="Only create Atlas Search indexes, don't ingest data"
    )
    parser.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip embedding generation (for testing)"
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-process existing events"
    )
    
    args = parser.parse_args()
    
    pipeline = IngestionPipeline(
        sample_size=args.sample_size,
        batch_size=args.batch_size,
        skip_existing=not args.no_skip_existing,
        skip_embeddings=args.skip_embeddings
    )
    
    if args.inspect_only:
        pipeline.inspect_dataset()
    elif args.create_indexes_only:
        print("Creating Atlas Search indexes...")
        pipeline.setup_indexes(domain=args.domain)
        print("Done!")
    else:
        pipeline.run(domain=args.domain)


if __name__ == "__main__":
    main()
