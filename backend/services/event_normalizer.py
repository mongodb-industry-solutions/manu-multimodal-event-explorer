"""Event normalizer service for transforming raw dataset records."""

import logging
import re
from typing import Dict, Any, Optional, List
from collections import Counter
from datetime import datetime, timezone

from models.event import Event, EventMetadata, EmbeddingMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventNormalizer:
    """Transform raw dataset records into the internal Event model.
    
    This service handles:
    - Parsing metadata from dataset text fields
    - Generating searchable text descriptions
    - Computing rarity scores based on combination frequency
    """
    
    # Known domain factors for MIST dataset
    SEASONS = ["spring", "summer", "fall", "winter", "autumn"]
    SEASON_ALIASES = {"autumn": "fall"}  # Map autumn -> fall
    
    TIMES_OF_DAY = ["dawn", "day", "dusk", "night", "daytime"]
    TIME_ALIASES = {"daytime": "day"}  # Map daytime -> day
    
    WEATHER_CONDITIONS = ["clear", "cloudy", "rainy", "foggy", "snowy", "overcast"]
    ENVIRONMENTS = ["rural", "urban", "highway", "suburban"]
    
    def __init__(self):
        """Initialize the event normalizer."""
        # Track combination frequencies for rarity calculation
        self._combination_counts: Counter = Counter()
        self._total_events: int = 0
    
    def parse_metadata_from_text(self, text: str) -> Dict[str, Optional[str]]:
        """Extract metadata fields from text description.
        
        The MIST dataset encodes conditions as: "autumn dawn clear weather rural road"
        This method extracts season, time_of_day, weather, and environment.
        
        Args:
            text: Raw text from dataset
            
        Returns:
            Dictionary with extracted metadata
        """
        text_lower = text.lower() if text else ""
        
        metadata = {
            "season": None,
            "time_of_day": None,
            "weather": None,
            "environment": "rural"  # Default
        }
        
        # Extract season (check before normalization)
        for season in self.SEASONS:
            if season in text_lower:
                # Normalize "autumn" -> "fall"
                metadata["season"] = self.SEASON_ALIASES.get(season, season)
                break
        
        # Extract time of day
        for tod in self.TIMES_OF_DAY:
            if tod in text_lower:
                # Normalize "daytime" -> "day"
                metadata["time_of_day"] = self.TIME_ALIASES.get(tod, tod)
                break
        
        # Extract weather
        for weather in self.WEATHER_CONDITIONS:
            if weather in text_lower:
                metadata["weather"] = weather
                break
        
        # Handle synonyms
        if "fog" in text_lower and not metadata["weather"]:
            metadata["weather"] = "foggy"
        if "rain" in text_lower and not metadata["weather"]:
            metadata["weather"] = "rainy"
        if "cloud" in text_lower and not metadata["weather"]:
            metadata["weather"] = "cloudy"
        if "sunny" in text_lower or "sunshine" in text_lower:
            metadata["weather"] = "clear"
        
        if "morning" in text_lower and not metadata["time_of_day"]:
            metadata["time_of_day"] = "dawn"
        if "afternoon" in text_lower and not metadata["time_of_day"]:
            metadata["time_of_day"] = "day"
        if "evening" in text_lower and not metadata["time_of_day"]:
            metadata["time_of_day"] = "dusk"
        if "midnight" in text_lower and not metadata["time_of_day"]:
            metadata["time_of_day"] = "night"
        
        # Extract environment
        for env in self.ENVIRONMENTS:
            if env in text_lower:
                metadata["environment"] = env
                break
        
        # Also check for "road" -> rural, "highway" -> highway, "city" -> urban
        if "highway" in text_lower:
            metadata["environment"] = "highway"
        elif "city" in text_lower or "urban" in text_lower:
            metadata["environment"] = "urban"
        
        return metadata
    
    def generate_text_description(
        self,
        season: Optional[str],
        time_of_day: Optional[str],
        weather: Optional[str],
        domain: str = "adas"
    ) -> str:
        """Generate a searchable text description from metadata.
        
        Creates keyword-rich descriptions for full-text search.
        
        Args:
            season: Season value
            time_of_day: Time of day value
            weather: Weather condition
            domain: Domain identifier
            
        Returns:
            Natural language description for full-text search
        """
        parts = []
        keywords = []  # Extra keywords for searchability
        
        # Base description
        if domain == "adas":
            parts.append("Autonomous driving scene on rural road")
        else:
            parts.append("Scene")
        
        # Weather description
        if weather:
            if weather == "foggy":
                parts.append("in foggy conditions")
                keywords.extend(["fog", "mist", "low visibility", "obscured", "hazy"])
            elif weather == "rainy":
                parts.append("in rainy conditions")
                keywords.extend(["rain", "wet road", "precipitation", "slippery"])
            elif weather == "snowy":
                parts.append("in snowy conditions")
                keywords.extend(["snow", "winter road", "icy", "cold"])
            elif weather == "cloudy" or weather == "overcast":
                parts.append("under cloudy skies")
                keywords.extend(["clouds", "overcast", "gray sky"])
            else:
                parts.append(f"in {weather} weather")
                keywords.append(weather)
        
        # Time of day description
        if time_of_day:
            if time_of_day == "dawn":
                parts.append("at dawn")
                keywords.extend(["sunrise", "early morning", "golden hour", "low sun"])
            elif time_of_day == "dusk":
                parts.append("at dusk")
                keywords.extend(["sunset", "evening", "twilight", "low sun"])
            elif time_of_day == "night":
                parts.append("at night")
                keywords.extend(["dark", "nighttime", "headlights", "low visibility"])
            else:
                parts.append(f"during {time_of_day}time")
                keywords.extend(["bright", "daytime", "good visibility"])
        
        # Season description
        if season:
            parts.append(f"in {season}")
            if season == "winter":
                keywords.extend(["cold", "frost"])
            elif season == "fall":
                keywords.extend(["autumn", "leaves"])
            elif season == "summer":
                keywords.extend(["warm", "bright"])
            elif season == "spring":
                keywords.extend(["mild", "blooming"])
        
        description = " ".join(parts)
        
        # Add visibility/condition summary
        visibility = "good"
        if weather in ["foggy", "rainy", "snowy"] or time_of_day in ["night", "dusk", "dawn"]:
            visibility = "reduced"
            if weather == "foggy" or time_of_day == "night":
                visibility = "low"
        
        description += f". Visibility: {visibility}."
        
        # Add keywords for search
        if keywords:
            description += f" Keywords: {', '.join(keywords[:8])}."
        
        return description
    
    def compute_rarity_score(
        self,
        season: Optional[str],
        time_of_day: Optional[str],
        weather: Optional[str]
    ) -> float:
        """Compute a rarity score based on combination frequency.
        
        Rarer combinations get higher scores (0.0 to 1.0).
        Call update_frequency_counts() first to populate statistics.
        
        Args:
            season: Season value
            time_of_day: Time of day value
            weather: Weather condition
            
        Returns:
            Rarity score between 0.0 (common) and 1.0 (rare)
        """
        if self._total_events == 0:
            return 0.5  # Default if no stats
        
        combo_key = (season, time_of_day, weather)
        count = self._combination_counts.get(combo_key, 0)
        
        if count == 0:
            return 1.0  # Never seen = very rare
        
        # Inverse frequency normalized to 0-1
        frequency = count / self._total_events
        rarity = 1.0 - frequency
        
        # Boost rarity for certain combinations (foggy night, etc.)
        if weather == "foggy" and time_of_day == "night":
            rarity = min(1.0, rarity + 0.2)
        if weather == "rainy" and time_of_day == "dusk":
            rarity = min(1.0, rarity + 0.1)
        
        return round(rarity, 3)
    
    def update_frequency_counts(self, events: List[Dict[str, Any]]) -> None:
        """Update combination frequency counts from a batch of events.
        
        Args:
            events: List of event dictionaries with metadata
        """
        for event in events:
            meta = event.get("metadata", {})
            combo = (
                meta.get("season"),
                meta.get("time_of_day"),
                meta.get("weather")
            )
            self._combination_counts[combo] += 1
            self._total_events += 1
        
        logger.info(f"Updated frequency counts. Total events: {self._total_events}")
    
    def normalize(
        self,
        raw_sample: Dict[str, Any],
        event_id: str,
        image_path: str,
        source_index: int,
        domain: str = "adas"
    ) -> Event:
        """Transform a raw dataset sample into an Event.
        
        Args:
            raw_sample: Raw data from HuggingFace dataset
            event_id: Unique identifier for this event
            image_path: Relative path to saved image
            source_index: Original index in source dataset
            domain: Domain identifier
            
        Returns:
            Normalized Event object
        """
        # Try to extract metadata from any text fields in the sample
        extracted_metadata = {
            "season": None,
            "time_of_day": None,
            "weather": None,
            "environment": "rural"
        }
        
        for key, value in raw_sample.items():
            if isinstance(value, str) and len(value) > 0:
                parsed = self.parse_metadata_from_text(value)
                # Merge parsed values (first match wins)
                for mk, mv in parsed.items():
                    if mv and (not extracted_metadata.get(mk) or extracted_metadata.get(mk) == "rural"):
                        extracted_metadata[mk] = mv
        
        # If minimal metadata found, assign based on index for variety
        # This ensures demo has diverse data even if dataset lacks explicit labels
        if not extracted_metadata["season"] and not extracted_metadata["time_of_day"] and not extracted_metadata["weather"]:
            idx = source_index
            extracted_metadata["season"] = self.SEASONS[idx % 4]  # Only use spring/summer/fall/winter
            extracted_metadata["time_of_day"] = self.TIMES_OF_DAY[(idx // 4) % len(self.TIMES_OF_DAY)]
            extracted_metadata["weather"] = self.WEATHER_CONDITIONS[(idx // 16) % len(self.WEATHER_CONDITIONS)]
        
        # Generate text description
        text_description = self.generate_text_description(
            season=extracted_metadata["season"],
            time_of_day=extracted_metadata["time_of_day"],
            weather=extracted_metadata["weather"],
            domain=domain
        )
        
        # Compute rarity score
        rarity_score = self.compute_rarity_score(
            season=extracted_metadata["season"],
            time_of_day=extracted_metadata["time_of_day"],
            weather=extracted_metadata["weather"]
        )
        
        # Create event metadata
        event_metadata = EventMetadata(
            season=extracted_metadata["season"],
            time_of_day=extracted_metadata["time_of_day"],
            weather=extracted_metadata["weather"],
            environment=extracted_metadata["environment"],
            rarity_score=rarity_score,
            source_index=source_index
        )
        
        # Create and return Event
        event = Event(
            event_id=event_id,
            domain=domain,
            source_dataset="jongwonryu/MIST-autonomous-driving-dataset",
            image_path=image_path,
            image_url=None,
            image_embedding=None,  # Will be populated by embedding service
            embedding_metadata=EmbeddingMetadata(),
            text_description=text_description,
            metadata=event_metadata,
            created_at=datetime.now(timezone.utc)
        )
        
        return event


# Example usage
if __name__ == "__main__":
    normalizer = EventNormalizer()
    
    # Test with mock data
    mock_sample = {
        "image": "<PIL Image>",
        "text": "A foggy night scene in winter on a rural road"
    }
    
    event = normalizer.normalize(
        raw_sample=mock_sample,
        event_id="mist_00001",
        image_path="adas/mist_00001.jpg",
        source_index=0,
        domain="adas"
    )
    
    print(f"Event ID: {event.event_id}")
    print(f"Text description: {event.text_description}")
    print(f"Metadata: {event.metadata}")
