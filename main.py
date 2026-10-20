import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db
from app.routes.emergency import router as emergency_router
from app.routes.contacts import router as contacts_router
from app.routes.responder import router as responder_router
from app.routes.simulate import router as simulate_router
from app.routes.system import router as system_router

# Initialize database schema
init_db()

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Action-oriented AI-agentic emergency response assistant bridging distress triggers and coordinated rescue."
)

# Enable CORS for cross-origin or mobile web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(emergency_router)
app.include_router(contacts_router)
app.include_router(responder_router)
app.include_router(simulate_router)
app.include_router(system_router)

# Mount static files
STATIC_DIR = Path(__file__).resolve().parent / "app" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": f"Welcome to {settings.app_name}. UI is loading."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
