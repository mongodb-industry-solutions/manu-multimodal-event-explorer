export const TALK_TRACK = [
  {
    heading: "Instructions and Talk Track",
    content: [
      {
        heading: "Solution Overview",
        body: "The Multimodal Event Explorer demonstrates MongoDB Atlas's multimodal AI capabilities for autonomous driving and industrial scenarios. It combines $rankFusion hybrid search (vector + text with RRF), Voyage AI embeddings and reranking, and a conversational MongoDB AI Agent powered by Claude on AWS Bedrock — all backed by a single MongoDB Atlas collection.",
      },
      {
        heading: "How to Demo",
        body: [
          "1. Start with the search bar — try 'night driving in rain' or 'foggy industrial environment'",
          "2. Point out the query time and the pipeline steps shown below the results",
          "3. Click a result card to see the full MongoDB capabilities breakdown and $rankFusion scores",
          "4. Switch domains (ADAS ↔ Industrial Scenarios) using the top-right buttons to show multi-domain support",
          "5. Use filters (season, weather, time of day) inside the search bar to demonstrate metadata pre-filtering inside $vectorSearch",
          "6. Click 'MongoDB AI Agent' in the header to open the conversational agent",
          "7. Click a suggested question (e.g. 'What are the rarest events?') and watch the agent's execution trace appear in real time as it calls search tools",
          "8. Point out the Quantization panel — 75% vector payload reduction with ~99% recall using scalar quantization",
        ],
      },
      {
        heading: "Sample Queries to Try",
        body: [
          "• 'overcast night driving' — finds low-light ADAS scenarios",
          "• 'rainy dusk on rural roads' — combines weather + time-of-day filtering",
          "• 'clear summer daytime' — optimal conditions baseline",
          "• 'foggy industrial site at night' — cross-domain rare event",
          "AI Agent: 'Compare foggy vs clear weather scenarios' — triggers compare_scenarios tool",
        ],
      },
    ],
  },
  {
    heading: "Behind the Scenes",
    content: [
      {
        heading: "Architecture Overview",
        body: "The stack has three layers: (1) MongoDB Atlas — single database for documents, embeddings, metadata, and images; (2) AI layer — Voyage AI for text embeddings (1024d) and cross-encoder reranking, AWS Bedrock (Claude 3 Haiku) as the reasoning engine for the AI Agent; (3) Application layer — FastAPI backend with a ReAct agentic loop, Next.js + LeafyGreen UI frontend with real-time SSE streaming for agent trace visibility.",
      },
      {
        heading: "Data Flow — Hybrid Search",
        body: [
          "1. User query → Voyage AI generates 1024-dim text embedding",
          "2. $rankFusion aggregation stage runs $vectorSearch + $search in parallel",
          "3. Reciprocal Rank Fusion (RRF) merges both result sets by rank position",
          "4. Optional: Voyage AI rerank-2 cross-encoder re-scores top candidates",
          "5. Frontend displays results with per-document RRF + reranker scores",
        ],
      },
      {
        heading: "Data Flow — MongoDB AI Agent",
        body: [
          "1. User question → FastAPI /api/chat/stream (SSE endpoint)",
          "2. Agent builds Anthropic-format messages and calls Claude 3 Haiku via Bedrock",
          "3. Claude reasons and returns a tool_use block (search_events / get_stats / compare_scenarios)",
          "4. Backend executes the tool against MongoDB Atlas, streams the trace event to the UI immediately via SSE",
          "5. Tool result is fed back to Claude for the next reasoning step",
          "6. Loop repeats (up to 6 iterations) until Claude returns end_turn with a final answer",
          "7. Frontend appends the final answer to the chat with the full collapsed trace attached",
        ],
      },
    ],
  },
  {
    heading: "Why MongoDB?",
    content: [
      {
        heading: "Scalar Quantization",
        body: "MongoDB Atlas compresses 1024-dim vectors from float32 to int8, achieving 75% smaller vector payload in the index while maintaining ~99% recall.",
      },
      {
        heading: "$rankFusion Hybrid Search",
        body: "Uses MongoDB's $rankFusion stage to combine $vectorSearch and $search results with Reciprocal Rank Fusion (RRF). Documents appearing in both pipelines rank higher.",
      },
      {
        heading: "Multimodal Ready",
        body: "Store images, embeddings, metadata, and text descriptions in the same document. Query across modalities with a single database.",
      },
      {
        heading: "Pre-filtering",
        body: "Apply metadata filters (season, weather, time) inside $vectorSearch for efficient retrieval. Filters narrow candidates before ANN search.",
      },
    ],
  },
];
