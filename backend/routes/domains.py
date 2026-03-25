"""Domains API routes."""

from fastapi import APIRouter, HTTPException, Path
from typing import List

from models.domain import Domain, DomainConfig

router = APIRouter(prefix="/api/domains", tags=["domains"])


@router.get("", response_model=List[DomainConfig])
async def list_domains():
    """
    List all available domains.
    
    Returns all domains including disabled ones, so the UI can show
    them as "coming soon".
    """
    return Domain.get_domains()


@router.get("/enabled", response_model=List[DomainConfig])
async def list_enabled_domains():
    """
    List only enabled domains.
    """
    return Domain.get_enabled_domains()


@router.get("/{domain_id}", response_model=DomainConfig)
async def get_domain(domain_id: str = Path(..., description="Domain identifier")):
    """
    Get a specific domain by ID.
    """
    domain = Domain.get_domain(domain_id)
    
    if not domain:
        raise HTTPException(status_code=404, detail=f"Domain not found: {domain_id}")
    
    return domain


@router.get("/{domain_id}/sample-queries", response_model=List[str])
async def get_sample_queries(domain_id: str = Path(..., description="Domain identifier")):
    """
    Get sample queries for a domain.
    
    These are pre-defined queries that showcase the search capabilities
    and help demo users get started.
    """
    domain = Domain.get_domain(domain_id)
    
    if not domain:
        raise HTTPException(status_code=404, detail=f"Domain not found: {domain_id}")
    
    return domain.sample_queries
