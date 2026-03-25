"""Domain configuration models."""

from typing import List, Optional
from pydantic import BaseModel, Field


class DomainConfig(BaseModel):
    """Configuration for a domain."""
    id: str = Field(..., description="Domain identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Domain description")
    enabled: bool = Field(default=True, description="Whether this domain is active")
    source_dataset: Optional[str] = Field(default=None, description="HuggingFace dataset ID")
    collection_name: str = Field(..., description="MongoDB collection name")
    
    # Filter options available for this domain
    available_filters: List[str] = Field(default_factory=list)
    
    # Sample queries for demo
    sample_queries: List[str] = Field(default_factory=list)


class Domain(BaseModel):
    """Domain abstraction layer."""
    
    @staticmethod
    def get_domains() -> List[DomainConfig]:
        """Get all available domains."""
        return [
            DomainConfig(
                id="adas",
                name="ADAS / Autonomous Driving",
                description="Autonomous driving and advanced driver assistance systems datasets",
                enabled=True,
                source_dataset="jongwonryu/MIST-autonomous-driving-dataset",
                collection_name="events_adas",
                available_filters=["season", "time_of_day", "weather"],
                sample_queries=[
                    "night driving conditions",
                    "overcast dusk on rural roads",
                    "clear summer daytime driving",
                    "autumn dawn driving conditions",
                    "spring night rural road",
                ]
            ),
            DomainConfig(
                id="factory",
                name="Industrial Scenarios",
                description="Industrial safety and inspection scenarios (coming soon)",
                enabled=False,  # Disabled for v1
                source_dataset=None,
                collection_name="events_factory",
                available_filters=["area", "shift", "equipment_type"],
                sample_queries=[
                    "safety hazard near machinery",
                    "missing protective equipment",
                    "assembly line anomaly",
                ]
            ),
        ]
    
    @staticmethod
    def get_domain(domain_id: str) -> Optional[DomainConfig]:
        """Get a specific domain by ID."""
        for domain in Domain.get_domains():
            if domain.id == domain_id:
                return domain
        return None
    
    @staticmethod
    def get_enabled_domains() -> List[DomainConfig]:
        """Get only enabled domains."""
        return [d for d in Domain.get_domains() if d.enabled]
