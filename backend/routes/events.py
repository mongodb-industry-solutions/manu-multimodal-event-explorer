"""Events API routes."""

from fastapi import APIRouter, HTTPException, Path, Query
from typing import Optional

from models.event import Event
from models.filters import FilterOptions
from services.mongodb_service import MongoDBEventsService

router = APIRouter(prefix="/api/events", tags=["events"])

# Initialize service
mongodb_service = MongoDBEventsService()


@router.get("/{event_id}", response_model=Event)
async def get_event(
    event_id: str = Path(..., description="Event identifier"),
    domain: str = Query(default="adas", description="Domain to search in")
):
    """
    Get a single event by ID.
    
    Returns full event details including metadata and embedding info.
    """
    event = mongodb_service.get_event(event_id, domain)
    
    if not event:
        raise HTTPException(status_code=404, detail=f"Event not found: {event_id}")
    
    return event


@router.get("", response_model=dict)
async def list_events(
    domain: str = Query(default="adas", description="Domain to list from"),
    season: Optional[str] = Query(default=None),
    time_of_day: Optional[str] = Query(default=None),
    weather: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    List events with optional filtering.
    
    This is a simple listing endpoint for browsing without search.
    """
    collection = mongodb_service._get_collection(domain)
    if not collection:
        raise HTTPException(status_code=400, detail=f"Invalid domain: {domain}")
    
    # Build filter
    filter_doc = {"domain": domain}
    if season:
        filter_doc["metadata.season"] = season
    if time_of_day:
        filter_doc["metadata.time_of_day"] = time_of_day
    if weather:
        filter_doc["metadata.weather"] = weather
    
    # Query
    cursor = collection.find(
        filter_doc,
        {"_id": 0, "image_embedding": 0}  # Exclude large fields
    ).skip(offset).limit(limit)
    
    events = list(cursor)
    total = collection.count_documents(filter_doc)
    
    return {
        "events": events,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/filters/options", response_model=dict)
async def get_filter_options(
    domain: str = Query(default="adas", description="Domain to get filters for")
):
    """
    Get available filter options for a domain.
    
    Returns distinct values for season, time_of_day, and weather filters.
    """
    # Get static options
    static_options = FilterOptions.for_domain(domain).to_dict()
    
    # Get actual values from database
    db_values = mongodb_service.get_filter_values(domain)
    
    # Combine (prefer DB values if available)
    return {
        "season": db_values.get("season") or static_options.get("season", []),
        "time_of_day": db_values.get("time_of_day") or static_options.get("time_of_day", []),
        "weather": db_values.get("weather") or static_options.get("weather", []),
    }
