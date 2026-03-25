import json
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.agent_service import AgentService, resolve_approval

logger = logging.getLogger(__name__)
router = APIRouter()
agent = AgentService()


class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


@router.post("/api/chat")
async def chat_endpoint(request: Request, body: ChatRequest):
    """Batch endpoint — returns full response + trace once complete."""
    try:
        response, trace = agent.run([m.dict() for m in body.messages])
        return {"response": response, "trace": trace}
    except Exception as e:
        logger.error(f"Chat agent error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )


@router.post("/api/chat/stream")
async def chat_stream_endpoint(request: Request, body: ChatRequest):
    """SSE streaming endpoint — yields trace + response events as they happen."""
    messages = [m.dict() for m in body.messages]

    def event_generator():
        try:
            for event in agent.run_stream(messages):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"Chat stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/api/tools")
async def list_tools_endpoint():
    """Return all registered agent tools with their name, description, and input schema."""
    return {"tools": agent.list_tools()}


class ApprovalRequest(BaseModel):
    approval_key: str   # "{request_id}:{tool_id}" sent in the approval_required SSE event
    approved: bool


@router.post("/api/chat/approve")
async def approve_tool_endpoint(body: ApprovalRequest):
    """Resolve a pending Human-in-the-Loop tool approval.

    The frontend sends this after the user clicks Approve or Reject on the
    approval card.  The backend unblocks the waiting run_stream() call and
    either executes the tool or skips it.

    Returns 404 if the approval_key is unknown (e.g. already timed out).
    """
    ok = resolve_approval(body.approval_key, body.approved)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail=f"No pending approval for key '{body.approval_key}'. It may have timed out.",
        )
    return {"status": "ok", "approved": body.approved}
