"""FastAPI application for the Healthcare Claims AI Agent."""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent import run_agent
from app.config import get_settings
from app.rag.ingest import run_ingestion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()

# In-memory session storage
# In production this would be Redis or a database
sessions: dict[str, list[dict]] = {}


# ─────────────────────────────────────────────
# LIFESPAN — runs on startup and shutdown
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run ingestion pipeline on startup."""
    logger.info("Starting Healthcare Claims AI Agent...")
    try:
        result = run_ingestion()
        logger.info(f"Knowledge base ready: {result}")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
    yield
    logger.info("Shutting down Healthcare Claims AI Agent...")


# ─────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────

app = FastAPI(
    title="Healthcare Claims AI Agent",
    description="AI-powered assistant for healthcare insurance claims",
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


# ─────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request model for chat endpoint.

    Attributes:
        message: The provider's question or request.
        session_id: Optional session ID for conversation continuity.
    """
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint.

    Attributes:
        response: The agent's response.
        session_id: Session ID for continuing the conversation.
        timestamp: When the response was generated.
    """
    response: str
    session_id: str
    timestamp: str


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str
    version: str
    environment: str


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint.

    Returns:
        Application health status.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment=settings.environment
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint for the claims agent.

    Accepts a provider message and returns the agent response.
    Maintains conversation history per session.

    Args:
        request: ChatRequest with message and optional session_id.

    Returns:
        ChatResponse with agent response and session ID.

    Raises:
        HTTPException: If agent fails to process the message.
    """
    # Create new session if none provided
    session_id = request.session_id or str(uuid.uuid4())

    # Get or create conversation history for this session
    if session_id not in sessions:
        sessions[session_id] = []

    conversation_history = sessions[session_id]

    try:
        response, updated_history = run_agent(
            user_message=request.message,
            conversation_history=conversation_history
        )

        # Update session history
        sessions[session_id] = updated_history

        return ChatResponse(
            response=response,
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent failed to process request: {str(e)}"
        )


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear conversation history for a session.

    Args:
        session_id: The session ID to clear.

    Returns:
        Confirmation message.
    """
    if session_id in sessions:
        del sessions[session_id]
        return {"message": f"Session {session_id} cleared"}
    raise HTTPException(
        status_code=404,
        detail=f"Session {session_id} not found"
    )


@app.get("/sessions")
async def list_sessions():
    """List all active sessions.

    Returns:
        Dictionary of active session IDs and message counts.
    """
    return {
        "active_sessions": len(sessions),
        "sessions": {
            sid: len(history)
            for sid, history in sessions.items()
        }
    }