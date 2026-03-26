"""AI-Engine — FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.database import init_db
from app.api.media_routes import router as media_router
from app.api.outreach_routes import router as outreach_router
from app.api.system_routes import router as system_router
from app.api.admin_routes import router as admin_router
from app.api.marketing_routes import router as marketing_router
from app.api.video_routes import router as video_router

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="NullRecords AI Engine",
    description=(
        "Local-first AI-powered media sourcing, tagging, and outreach platform "
        "for the NullRecords music collective."
    ),
    version="0.1.0",
)

# Allow local services to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8100", "http://localhost:8300", "http://127.0.0.1:8100"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register routers ---
app.include_router(media_router)
app.include_router(outreach_router)
app.include_router(system_router)
app.include_router(admin_router)
app.include_router(marketing_router)
app.include_router(video_router)

# --- Static files ---
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/admin")
def admin_page():
    """Serve the admin dashboard."""
    return FileResponse(str(STATIC_DIR / "admin.html"))


@app.get("/")
def root():
    return {
        "name": "NullRecords AI Engine",
        "version": "0.1.0",
        "docs": "/docs",
        "admin": "/admin",
    }
