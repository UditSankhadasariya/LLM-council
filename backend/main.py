"""FastAPI backend for LLM Council."""

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

from . import storage
from .config import COUNCIL_MODELS
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage1_collect_responses_progressive, stage2_synthesize_final
from .browser import BrowserProviderManager
from .llm_client import set_browser_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage browser provider lifecycle."""
    logger.info("Starting LLM Council backend...")

    # Start browser providers
    browser_manager = BrowserProviderManager()
    await browser_manager.start()
    set_browser_manager(browser_manager)

    logger.info("LLM Council backend ready!")
    yield

    # Shutdown browser providers
    await browser_manager.stop()
    logger.info("LLM Council backend shutdown complete.")


app = FastAPI(title="LLM Council API", lifespan=lifespan)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


@app.get("/api/status")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/health")
async def health_check():
    """Check readiness of all configured providers."""
    from .llm_client import _browser_manager

    providers = {}

    for model in COUNCIL_MODELS:
        model_id = model["id"]
        provider = model["provider"]
        name = model["name"]

        if provider == "browser":
            browser_provider = model.get("browser_provider", "chatgpt")
            ready = False
            if _browser_manager and browser_provider in _browser_manager._providers:
                bm = _browser_manager._providers[browser_provider]["browser"]
                ready = bm.ready and bm.tab is not None
            initializing = (
                _browser_manager is not None
                and not _browser_manager._init_done.is_set()
            )
            providers[model_id] = {
                "name": name,
                "provider": provider,
                "ready": ready,
                "initializing": initializing,
            }

        elif provider == "claude-cli":
            # Check auth status via `claude auth status`
            auth_info = {}
            ready = False
            try:
                proc = await asyncio.create_subprocess_exec(
                    "claude", "auth", "status",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
                if proc.returncode == 0:
                    auth_info = json.loads(stdout.decode())
                    ready = auth_info.get("loggedIn", False)
            except Exception:
                pass
            providers[model_id] = {
                "name": name,
                "provider": provider,
                "ready": ready,
                "authenticated": ready,
                **( {"email": auth_info["email"]} if auth_info.get("email") else {} ),
            }

    all_ready = all(p["ready"] for p in providers.values())
    return {"all_ready": all_ready, "providers": providers}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations(date: Optional[str] = Query(None)):
    """List conversations (metadata only), filtered by date. Defaults to today."""
    return storage.list_conversations(date)


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/dates", response_model=List[str])
async def list_conversation_dates():
    """List all dates that have conversations."""
    return storage.list_conversation_dates()


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Run the 2-stage council process
    stage1_results, stage2_result = await run_full_council(request.content)

    # Add assistant message
    storage.add_assistant_message(conversation_id, stage1_results, stage2_result)

    # Return the complete response
    return {
        "stage1": stage1_results,
        "stage2": stage2_result,
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        stage1_results = []
        stage2_result = None
        title_task = None
        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses progressively
            model_names = [m["name"] for m in COUNCIL_MODELS]
            yield f"data: {json.dumps({'type': 'stage1_start', 'data': {'models': model_names}})}\n\n"

            async for result in stage1_collect_responses_progressive(request.content):
                stage1_results.append(result)
                yield f"data: {json.dumps({'type': 'stage1_model_complete', 'data': result})}\n\n"

            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_result = await stage2_synthesize_final(request.content, stage1_results)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                title_task = None
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_result
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            # Save whatever we collected so far so the conversation isn't lost
            if stage1_results or stage2_result:
                try:
                    storage.add_assistant_message(conversation_id, stage1_results, stage2_result)
                except Exception:
                    pass
            # Cancel pending title task
            if title_task and not title_task.done():
                title_task.cancel()
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# Serve frontend static build
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React SPA for any non-API route."""
        return FileResponse(_frontend_dist / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
