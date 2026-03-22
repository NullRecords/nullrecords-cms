# AI Engine — NullRecords Media Sourcing & Outreach Platform

Local-first FastAPI backend for sourcing public-domain media, AI tagging, playlist/influencer discovery, and outreach automation.

## Quick Start

```bash
cd ai-engine

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY and PEXELS_API_KEY

# Run the server
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for interactive API docs (Swagger UI).

## Architecture

```
ai-engine/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── api/                  # Route handlers
│   │   ├── media_routes.py   # /media/* endpoints
│   │   ├── outreach_routes.py# /outreach/* endpoints
│   │   └── system_routes.py  # /system/* endpoints
│   ├── core/
│   │   ├── config.py         # Settings from .env
│   │   └── database.py       # SQLAlchemy engine + session
│   ├── models/               # ORM models (SQLite)
│   ├── schemas/              # Pydantic request/response schemas
│   ├── services/
│   │   ├── media/            # Source plugins + downloader + AI tagger
│   │   └── outreach/         # Discovery, scoring, messaging, follow-ups
│   └── jobs/                 # Background task scheduler (phase 2)
├── media-library/            # Downloaded assets
├── exports/                  # Generated videos & social content
├── requirements.txt
├── .env.example
└── .gitignore
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/media/search` | Search Pexels or Internet Archive |
| POST | `/media/download/{id}` | Download an asset locally |
| POST | `/media/tag/{id}` | AI-tag an asset |
| GET  | `/media/` | List all assets |
| POST | `/outreach/discover` | Discover playlists & influencers |
| POST | `/outreach/generate/{type}/{id}` | Generate outreach message |
| POST | `/outreach/send` | Log outreach + schedule follow-up |
| GET  | `/outreach/followups` | Get due follow-ups |
| POST | `/system/credential` | Store an API key |
| GET  | `/system/health` | Health check |

## Roadmap

- **Phase 1 (current):** Media sourcing, tagging, outreach pipeline
- **Phase 2:** AI video generation (MoviePy + generative visuals)
