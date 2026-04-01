"""Images API routes for serving local images."""

import os
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Path as PathParam
from fastapi.responses import FileResponse, RedirectResponse

from models.domain import Domain
from services.mongodb_service import MongoDBEventsService
from services.s3_service import S3Service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["images"])

# Initialize services
mongodb_service = MongoDBEventsService()

# S3 service (only if S3 storage is enabled)
USE_S3 = os.getenv("USE_S3_STORAGE", "false").lower() == "true"
CLOUDFRONT_DOMAIN = os.getenv("CLOUDFRONT_DOMAIN", "")
logger.info(f"USE_S3_STORAGE: {os.getenv('USE_S3_STORAGE')}, USE_S3: {USE_S3}")
logger.info(f"CLOUDFRONT_DOMAIN: {CLOUDFRONT_DOMAIN}")
s3_service = S3Service() if USE_S3 else None
if s3_service:
    logger.info("S3Service initialized for CloudFront URLs")
else:
    logger.info("S3Service not initialized - using direct S3 URLs or local files")

# Base directory for images
IMAGES_BASE_DIR = Path(__file__).parent.parent / "data" / "images"


@router.get("/{event_id}")
async def get_image_by_event_id(
    event_id: str = PathParam(..., description="Event identifier")
):
    """
    Get image for an event by event_id.
    
    This endpoint abstracts the storage backend:
    - Phase 1: Serves from local filesystem
    - Phase 2: Redirects to S3 URL
    
    The event_id matches the image filename, ensuring data integrity
    when migrating from local to S3 storage.
    """
    # Try to find the event in any domain
    event = None
    for domain_config in Domain.get_enabled_domains():
        event = mongodb_service.get_event(event_id, domain_config.id)
        if event:
            break
    
    if not event:
        # Fall back to trying to find the image file directly
        # This allows serving images before MongoDB is populated
        for domain_config in Domain.get_enabled_domains():
            potential_path = IMAGES_BASE_DIR / domain_config.id / f"{event_id}.jpg"
            if potential_path.exists():
                return FileResponse(
                    path=potential_path,
                    media_type="image/jpeg",
                    filename=f"{event_id}.jpg"
                )
        
        logger.error(f"Event not found for image: {event_id}")
        raise HTTPException(status_code=404, detail=f"Image not found for event: {event_id}")
    
    # Phase 2: If image_url is set (S3), redirect to CloudFront URL
    if event.image_url and USE_S3 and s3_service and CLOUDFRONT_DOMAIN:
        logger.debug(f"Generating CloudFront URL for {event_id}: {event.image_url}")
        # Extract S3 key from URL (e.g., "adas/mist_00001.jpg")
        # URL format: https://bucket.s3.region.amazonaws.com/key
        try:
            s3_key = event.image_url.split('.amazonaws.com/')[-1]
            
            # Use CloudFront instead of presigned S3 URLs
            cloudfront_url = f"https://{CLOUDFRONT_DOMAIN}/{s3_key}"
            logger.info(f"Redirecting to CloudFront: {cloudfront_url}")
            return RedirectResponse(url=cloudfront_url)
            
        except Exception as e:
            logger.error(f"Error generating CloudFront URL for {event_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error generating image URL: {str(e)}")
    
    # Phase 1: Serve from local filesystem (if no S3 URL)
    logger.warning(f"No image_url for {event_id}, attempting local filesystem (image_path={event.image_path})")
    image_path = IMAGES_BASE_DIR / event.image_path
    
    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Image file not found: {event.image_path}")
    
    return FileResponse(
        path=image_path,
        media_type="image/jpeg",
        filename=f"{event_id}.jpg"
    )


@router.get("/path/{image_path:path}")
async def get_image_by_path(
    image_path: str = PathParam(..., description="Relative image path (e.g., adas/mist_00001.jpg)")
):
    """
    Get image by relative path.
    
    This is a direct file serving endpoint, useful for debugging
    or when you have the image_path from an event document.
    """
    # Sanitize path to prevent directory traversal
    safe_path = Path(image_path)
    if ".." in safe_path.parts:
        raise HTTPException(status_code=400, detail="Invalid path")
    
    full_path = IMAGES_BASE_DIR / safe_path
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {image_path}")
    
    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    
    return FileResponse(
        path=full_path,
        media_type="image/jpeg"
    )
