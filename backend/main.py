import os
import sys
from contextlib import asynccontextmanager

# Add parent directory to sys.path if not present so imports work from anywhere
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

try:
    from backend.db.database import engine, Base
    from backend.routers.incidents import router as incidents_router
except ImportError:
    from db.database import engine, Base
    from routers.incidents import router as incidents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure SQLite tables exist on app startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="RapidRelay Triage API",
    description="Multilingual disaster & emergency intake + triage backend for India (floods/cyclones).",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for all origins for hackathon speed
# TODO: Restrict allow_origins to specific frontend domain (e.g. http://localhost:5173 or production domain) in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(incidents_router)


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "RapidRelay Triage API",
        "status": "operational",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "healthy",
        "database": "sqlite_connected"
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
