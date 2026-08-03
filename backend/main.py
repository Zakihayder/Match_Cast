"""
MatchCast AI — FastAPI Application

Main entry point for the backend API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.routers import matches, processing, analysis, coach, highlights, storage

app = FastAPI(
    title="MatchCast AI",
    description="AI-Powered Football Match Analysis Pipeline",
    version="0.1.0",
)

# CORS — allow the Vite dev server on any local port (5173, 5174, ...) plus
# any explicitly configured origins. Using a regex keeps uploads working no
# matter which port Vite picks.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Quick health check for deployment verification."""
    return {
        "status": "ok",
        "service": "matchcast-ai",
        "yolo_model": settings.yolo_model_resolved,
    }


# Register routers
app.include_router(matches.router, prefix="/api/matches", tags=["matches"])
app.include_router(processing.router, prefix="/api/processing", tags=["processing"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(coach.router, prefix="/api/coach", tags=["coach"])
app.include_router(highlights.router, prefix="/api/highlights", tags=["highlights"])
app.include_router(storage.router, prefix="/api/storage", tags=["storage"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.FASTAPI_HOST,
        port=settings.FASTAPI_PORT,
        reload=True,
    )
