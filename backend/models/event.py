"""Event model for the Multimodal Event Explorer."""

from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field


class EmbeddingMetadata(BaseModel):
    """Metadata about the vector embedding."""
    dimensions: int = 1024
    original_bytes: int = 4096  # 1024 dims × 4 bytes (float32)
    quantized_bytes: int = 1024  # 1024 dims × 1 byte (int8)
    model: str = "voyage-multimodal-3.5"


class EventMetadata(BaseModel):
    """Metadata extracted from the source dataset."""
    season: Optional[str] = None  # spring, summer, fall, winter
    time_of_day: Optional[str] = None  # dawn, day, dusk, night
    weather: Optional[str] = None  # clear, cloudy, rainy, foggy
    environment: str = "rural"
    rarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_index: Optional[int] = None  # Original index in HuggingFace dataset


class Event(BaseModel):
    """Internal event model for the Multimodal Event Explorer.
    
    This model normalizes data from various source datasets (MIST, factory vision, etc.)
    into a consistent format for storage and search.
    """
    event_id: str = Field(..., description="Unique identifier, matches image filename")
    domain: str = Field(default="adas", description="Domain: adas, factory, etc.")
    source_dataset: str = Field(default="jongwonryu/MIST-autonomous-driving-dataset")
    
    # Image data
    image_path: str = Field(..., description="Relative path to local image file")
    image_url: Optional[str] = Field(default=None, description="S3 URL after migration")
    
    # Vector embedding
    image_embedding: Optional[List[float]] = Field(default=None, description="Voyage AI multimodal embedding")
    embedding_metadata: EmbeddingMetadata = Field(default_factory=EmbeddingMetadata)
    
    # Searchable text
    text_description: str = Field(..., description="Generated text description for full-text search")
    
    # Metadata for filtering
    metadata: EventMetadata = Field(default_factory=EventMetadata)
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_mongo_doc(self) -> dict:
        """Convert to MongoDB document format."""
        doc = self.model_dump()
        # Flatten metadata for easier querying
        doc["season"] = self.metadata.season
        doc["time_of_day"] = self.metadata.time_of_day
        doc["weather"] = self.metadata.weather
        doc["rarity_score"] = self.metadata.rarity_score
        return doc

    @classmethod
    def from_mongo_doc(cls, doc: dict) -> "Event":
        """Create Event from MongoDB document."""
        if "_id" in doc:
            del doc["_id"]
        # Remove flattened fields that are also in metadata
        for key in ["season", "time_of_day", "weather", "rarity_score"]:
            if key in doc and "metadata" in doc:
                doc.pop(key, None)
        return cls(**doc)
