"""Migration script to upload existing local images to S3 and update MongoDB."""

import sys
import logging
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.s3_service import S3Service
from services.mongodb_service import MongoDBEventsService
from models.event import Event

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class S3MigrationService:
    """Service to migrate images from local storage to S3."""
    
    def __init__(self, domain: str = "adas"):
        """Initialize migration service.
        
        Args:
            domain: Domain to migrate
        """
        self.domain = domain
        self.s3_service = S3Service()
        self.mongodb_service = MongoDBEventsService()
        
        # Base directory for local images
        self.images_base_dir = backend_dir / "data" / "images"
        
        # Statistics
        self.stats = {
            "total_events": 0,
            "already_migrated": 0,
            "uploaded": 0,
            "updated": 0,
            "errors": 0
        }
    
    def migrate_all(self, dry_run: bool = False) -> dict:
        """Migrate all images for a domain to S3.
        
        Args:
            dry_run: If True, don't actually upload or update MongoDB
            
        Returns:
            Statistics dictionary
        """
        logger.info(f"Starting S3 migration for domain: {self.domain}")
        logger.info(f"Dry run: {dry_run}")
        
        # Check S3 bucket access
        if not dry_run and not self.s3_service.check_bucket_exists():
            logger.error("Cannot access S3 bucket. Aborting migration.")
            return self.stats
        
        # Get all events for domain
        events = self.mongodb_service.get_all_events(self.domain)
        self.stats["total_events"] = len(events)
        
        logger.info(f"Found {len(events)} events to migrate")
        
        # Process each event
        for event in events:
            self._migrate_event(event, dry_run)
        
        # Print summary
        print("\n" + "=" * 60)
        print("S3 MIGRATION COMPLETE")
        print("=" * 60)
        print(f"Total events: {self.stats['total_events']}")
        print(f"Already migrated: {self.stats['already_migrated']}")
        print(f"Uploaded to S3: {self.stats['uploaded']}")
        print(f"Updated in MongoDB: {self.stats['updated']}")
        print(f"Errors: {self.stats['errors']}")
        print("=" * 60 + "\n")
        
        return self.stats
    
    def _migrate_event(self, event: Event, dry_run: bool) -> None:
        """Migrate a single event's image to S3.
        
        Args:
            event: Event to migrate
            dry_run: If True, don't actually upload or update
        """
        # Skip if already migrated
        if event.image_url:
            logger.debug(f"Event {event.event_id} already has S3 URL: {event.image_url}")
            self.stats["already_migrated"] += 1
            return
        
        # Check if local image exists
        local_path = self.images_base_dir / event.image_path
        if not local_path.exists():
            logger.error(f"Local image not found for {event.event_id}: {local_path}")
            self.stats["errors"] += 1
            return
        
        if dry_run:
            logger.info(f"[DRY RUN] Would upload: {event.image_path}")
            self.stats["uploaded"] += 1
            self.stats["updated"] += 1
            return
        
        # Upload to S3
        s3_url = self.s3_service.upload_image_from_path(
            image_path=event.image_path,
            images_base_dir=self.images_base_dir,
            domain=self.domain
        )
        
        if not s3_url:
            logger.error(f"Failed to upload image for {event.event_id}")
            self.stats["errors"] += 1
            return
        
        self.stats["uploaded"] += 1
        
        # Update MongoDB with S3 URL
        success = self.mongodb_service.update_event_image_url(
            event_id=event.event_id,
            domain=self.domain,
            image_url=s3_url
        )
        
        if success:
            self.stats["updated"] += 1
            logger.info(f"✓ Migrated {event.event_id}: {s3_url}")
        else:
            logger.error(f"Failed to update MongoDB for {event.event_id}")
            self.stats["errors"] += 1


def main():
    """CLI entry point for S3 migration."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate local images to S3"
    )
    parser.add_argument(
        "--domain", "-d",
        default="adas",
        help="Domain to migrate (default: adas)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually upload or update MongoDB"
    )
    
    args = parser.parse_args()
    
    # Run migration
    migrator = S3MigrationService(domain=args.domain)
    migrator.migrate_all(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
