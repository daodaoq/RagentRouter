"""RAgent Router — Backend Entry Point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, SessionLocal
from models import seed_demo_data
from routers import messages, dashboard, rules


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    db = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()
    yield
    # Shutdown


app = FastAPI(
    title="RAgent Router",
    description="AI Cost Optimization & Smart Routing Layer for Claude Code",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow Electron and dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "x-ragent-model",
        "x-ragent-provider",
        "x-ragent-rule",
        "x-ragent-reason",
    ],
)

# Register routers
app.include_router(messages.router)
app.include_router(dashboard.router)
app.include_router(rules.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ragent-router", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
