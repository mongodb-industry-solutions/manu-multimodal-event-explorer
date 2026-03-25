from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter

from dotenv import load_dotenv

# Import routers
from routes import (
    search_router,
    events_router,
    domains_router,
    images_router,
    stats_router,
)
from db.mdb import close_mongo_client, get_mongo_client
from routes.chat import router as chat_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown.
    
    This ensures MongoDB connections are properly closed on shutdown,
    which is critical for shared clusters.
    """
    # Startup: Initialize MongoDB connection
    client = get_mongo_client()
    if client:
        print("MongoDB connection pool initialized")
    
    yield
    
    # Shutdown: Close MongoDB connection
    close_mongo_client()
    print("MongoDB connection pool closed")


app = FastAPI(
    title="Multimodal Event Explorer API",
    description="MongoDB-powered multimodal search for autonomous driving and computer vision domains",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(search_router)
app.include_router(events_router)
app.include_router(domains_router)
app.include_router(images_router)
app.include_router(stats_router)
app.include_router(chat_router)


@app.get("/")
async def read_root(request: Request):
    return {
        "message": "Multimodal Event Explorer API",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "search": "/api/search",
            "events": "/api/events",
            "domains": "/api/domains",
            "images": "/api/images",
            "stats": "/api/stats"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}