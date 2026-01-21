"""
PromptDa API - FastAPI Application Entry Point.

A minimal, production-quality backend for saving prompts and AI responses.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.session import get_engine
from app.routers import auth, messages, personas

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and graceful shutdown."""
    # Startup: Nothing special needed (lazy DB init)
    yield
    # Shutdown: Close database connections gracefully
    engine = get_engine()
    if engine:
        await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="API for managing saved prompts, AI responses, and personas.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(personas.router, prefix="/api")
app.include_router(messages.router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "up"}
