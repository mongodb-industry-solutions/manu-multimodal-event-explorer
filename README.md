# Multimodal Event Explorer

A MongoDB-powered demo that lets you explore a dataset of autonomous driving events through natural language search and a conversational AI agent. Users can search by scene description, filter by weather, season, or time of day, and interact with a ReAct-based AI agent backed by AWS Bedrock (Claude 3) that reasons over the database in real time.

## Where MongoDB Shines?

- **Atlas Vector Search with Scalar Quantization** — image embeddings (1024-dim, Voyage AI) are stored as `float32` in documents and compressed to `int8` at the index layer, reducing memory footprint by ~75% with ~99% recall preserved.
- **Hybrid Search via `$rankFusion`** — combines vector search and full-text Atlas Search with Reciprocal Rank Fusion in a single aggregation pipeline, no application-side merging needed.
- **`$facet` aggregations** — the AI agent uses a single `$facet` pipeline to compute weather, season, and time-of-day distributions across the entire collection in one round-trip.
- **Flexible document model** — each event stores raw image bytes, a text description, metadata fields, and a vector embedding in one document, eliminating joins.

## High Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Browser                             │
│  Next.js 15 (App Router)  ·  LeafyGreen UI                  │
│  SearchBar · ResultsGrid · ChatPanel (SSE streaming)        │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP / SSE
┌───────────────────────▼─────────────────────────────────────┐
│                    FastAPI Backend                           │
│  /api/search  (hybrid search · reranker)                    │
│  /api/chat/stream  (ReAct agent · SSE)                      │
│  /api/chat/approve (Human-in-the-Loop)                      │
│  /api/tools   (tool discovery registry)                     │
└──────┬────────────────┬──────────────────┬──────────────────┘
       │                │                  │
┌──────▼──────┐  ┌──────▼──────┐  ┌───────▼───────┐
│  MongoDB    │  │  AWS Bedrock│  │   Voyage AI   │
│  Atlas      │  │  Claude 3   │  │  Embeddings + │
│  (Vector +  │  │  (LLM +     │  │  Reranker     │
│  Text Search│  │   Agent)    │  │               │
└─────────────┘  └─────────────┘  └───────────────┘
```

## Tech Stack

- [Next.js 15](https://nextjs.org/docs/app) (App Router) for the frontend
- [MongoDB Atlas](https://www.mongodb.com/atlas/database) — Vector Search, Atlas Search, aggregations
- [FastAPI](https://fastapi.tiangolo.com/) for the Python backend
- [AWS Bedrock](https://aws.amazon.com/bedrock/) — Claude 3 Haiku for the AI agent
- [Voyage AI](https://www.voyageai.com/) — `voyage-multimodal-3` for embeddings, `rerank-2` for reranking
- [uv](https://docs.astral.sh/uv/) for Python dependency management
- [LeafyGreen UI](https://www.mongodb.design/) for MongoDB-branded React components

## Prerequisites

Before you begin, ensure you have met the following requirements:

- Python 3.13 (but less than 3.14)
- Node.js 22 or higher
- uv (install via [uv's official documentation](https://docs.astral.sh/uv/getting-started/installation/))
- A [MongoDB Atlas](https://www.mongodb.com/atlas) cluster with the ADAS collection loaded and Vector Search + Atlas Search indexes created
- A [Voyage AI](https://www.voyageai.com/) API key
- AWS credentials configured locally with access to Bedrock (Claude 3 Haiku)

## Run it Locally

### Backend

1. Copy the example environment file and fill in your credentials:
   ```bash
   cp backend/.env.example backend/.env
   ```
   Edit `backend/.env` with your values:
   ```env
   MONGODB_URI=<your-atlas-connection-string>
   DATABASE_NAME=multimodal_explorer
   VOYAGE_API_KEY=<your-voyage-ai-key>
   AWS_REGION=us-east-1
   AWS_PROFILE=<your-aws-sso-profile>   # omit if using instance role / IRSA
   ```

2. Open the project in your preferred IDE (Visual Studio Code recommended).
3. Open the terminal and ensure you are in the root project directory where the `makefile` is located.
4. Install Python dependencies:
   - uv initialization
     ```bash
     make uv_init
     ```
   - uv sync
     ```bash
     make uv_sync
     ```
5. Verify that the `.venv` folder has been generated within the `/backend` directory.

### Running Backend Locally

After setting up the backend dependencies, you can run the development server:

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Start the FastAPI development server:
   ```bash
   uv run uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. The backend API will be accessible at http://localhost:8000. You can verify it is running at http://localhost:8000/docs (Swagger UI).

**Note**: If port 8000 is already in use (e.g., by Docker containers), either stop the containers with `make clean` or use a different port like `--port 8001`.

### Frontend

1. Copy the example environment file:
   ```bash
   cp frontend/EXAMPLE.env frontend/.env.local
   ```
   The default value points to the local backend — no changes needed for local development:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

2. Navigate to the `frontend` folder and install dependencies:
   ```bash
   cd frontend
   npm install
   ```

3. Start the frontend development server:
   ```bash
   npm run dev
   ```

4. The frontend will be accessible at http://localhost:3000.

## Run with Docker

Make sure to run this from the root directory. The Docker Compose setup mounts your local AWS credentials so the backend can reach Bedrock without static keys.

1. Build and start both containers:
   ```bash
   make build
   ```
2. To stop and remove the containers and images:
   ```bash
   make clean
   ```

## Common errors

### Backend

- **Missing `.env` file** — copy `backend/.env.example` to `backend/.env` and fill in all required values (`MONGODB_URI`, `VOYAGE_API_KEY`, AWS config).
- **AWS auth errors** — ensure your AWS SSO session is active (`aws sso login --profile <profile>`) or that the machine has an IAM role with Bedrock access.
- **MongoDB connection refused** — confirm your Atlas cluster IP allowlist includes your current IP address (or `0.0.0.0/0` for development).
- **Vector search index not found** — the Atlas Vector Search and Atlas Search indexes must be created before running the app. Refer to the index definitions in `backend/services/mongodb_service.py`.

### Frontend

- **`NEXT_PUBLIC_API_URL` not set** — copy `frontend/EXAMPLE.env` to `frontend/.env.local`. Without this the frontend cannot reach the backend.
- **CORS errors in browser** — ensure the `ORIGINS` variable in `backend/.env` includes `http://localhost:3000`.