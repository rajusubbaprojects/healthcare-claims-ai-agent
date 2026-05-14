"""FastAPI application for the Healthcare Claims AI Agent."""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.agent import run_agent
from app.config import get_settings
from app.rag.ingest import run_ingestion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()
limiter = Limiter(key_func=get_remote_address)

sessions: dict[str, list[dict]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Healthcare Claims AI Agent...")
    try:
        result = run_ingestion()
        logger.info(f"Knowledge base ready: {result}")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
    yield
    logger.info("Shutting down Healthcare Claims AI Agent...")


class LimitRequestSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10_000:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request too large"}
            )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app = FastAPI(
    title="Healthcare Claims AI Agent",
    description="AI-powered assistant for healthcare insurance claims",
    version="1.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://claims-agent-ui-490841876782.s3-website-us-east-1.amazonaws.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

app.add_middleware(LimitRequestSizeMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > 2000:
            raise ValueError("Message too long — max 2000 characters")
        return v


class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment=settings.environment
    )


@app.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(request: Request, body: ChatRequest):
    session_id = body.session_id or str(uuid.uuid4())

    if session_id not in sessions:
        sessions[session_id] = []

    conversation_history = sessions[session_id]

    try:
        response, updated_history = run_agent(
            user_message=body.message,
            conversation_history=conversation_history
        )

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
    if session_id in sessions:
        del sessions[session_id]
        return {"message": f"Session {session_id} cleared"}
    raise HTTPException(
        status_code=404,
        detail=f"Session {session_id} not found"
    )


@app.get("/sessions")
async def list_sessions():
    return {
        "active_sessions": len(sessions),
        "sessions": {
            sid: len(history)
            for sid, history in sessions.items()
        }
    }