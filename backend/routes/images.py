"""Images API routes for serving local images."""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Path as PathParam
from fastapi.responses import FileResponse, RedirectResponse

from models.domain import Domain
from services.mongodb_service import MongoDBEventsService
from services.s3_service import S3Service

router = APIRouter(prefix="/api/images", tags=["images"])

# Initialize services
mongodb_service = MongoDBEventsService()

# S3 service (only if S3 storage is enabled)
USE_S3 = os.getenv("USE_S3_STORAGE", "false").lower() == "true"
s3_service = S3Service() if USE_S3 else None

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
        
        raise HTTPException(status_code=404, detail=f"Image not found for event: {event_id}")
    
    # Phase 2: If image_url is set (S3), generate presigned URL
    if event.image_url and USE_S3 and s3_service:
        # Extract S3 key from URL (e.g., "adas/mist_00001.jpg")
        # URL format: https://bucket.s3.region.amazonaws.com/key
        try:
            s3_key = event.image_url.split('.amazonaws.com/')[-1]
            presigned_url = s3_service.generate_presigned_url(
                s3_key=s3_key,
                expiration=86400  # 24 hours
            )
            if presigned_url:
                return RedirectResponse(url=presigned_url)
            else:
                raise HTTPException(status_code=500, detail="Failed to generate presigned URL")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating presigned URL: {str(e)}")
    
    # Phase 1: Serve from local filesystem
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
