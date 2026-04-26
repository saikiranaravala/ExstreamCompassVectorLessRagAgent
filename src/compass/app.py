"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from compass import __version__

app = FastAPI(
    title="Compass RAG",
    description="Vectorless Retrieval-Augmented Generation agent for OpenText Exstream documentation",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": __version__}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Compass RAG API",
        "version": __version__,
        "docs": "/docs",
    }
