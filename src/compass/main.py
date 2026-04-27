"""Entry point for running the Compass RAG API."""

import uvicorn
from compass.app import app

if __name__ == "__main__":
    uvicorn.run(
        "compass.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


# Export app for uvicorn
__all__ = ["app"]
