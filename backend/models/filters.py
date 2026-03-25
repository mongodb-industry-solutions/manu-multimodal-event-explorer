"""Filter options models."""

from typing import List, Dict
from pydantic import BaseModel, Field


class FilterOptions(BaseModel):
    """Available filter options for search."""
    
    seasons: List[str] = Field(
        default=["spring", "summer", "fall"],
        description="Available season filters"
    )
    
    times_of_day: List[str] = Field(
        default=["dawn", "day", "dusk", "night"],
        description="Available time of day filters"
    )
    
    weather_conditions: List[str] = Field(
        default=["clear", "overcast"],
        description="Available weather filters"
    )
    
    @classmethod
    def for_domain(cls, domain_id: str) -> "FilterOptions":
        """Get filter options for a specific domain."""
        if domain_id == "adas":
            return cls()
        elif domain_id == "factory":
            # Factory domain has different filters
            return cls(
                seasons=[],
                times_of_day=["morning_shift", "afternoon_shift", "night_shift"],
                weather_conditions=[]
            )
        return cls()
    
    def to_dict(self) -> Dict[str, List[str]]:
        """Convert to dictionary format."""
        return {
            "season": self.seasons,
            "time_of_day": self.times_of_day,
            "weather": self.weather_conditions,
        }
