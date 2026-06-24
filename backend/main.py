"""RAgent Router — Backend Entry Point."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, SessionLocal
from logger import setup_logging, get_logger, request_logger
from models import seed_demo_data
from routers import messages, dashboard, rules, ccswitch, traffic

# ── Init logging ───────────────────────────────────────────────────
setup_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting RAgent Router v0.1.0")
    init_db()
    db = SessionLocal()
    try:
        seed_demo_data(db)
        log.info("Database initialized with demo data")
    finally:
        db.close()
    yield
    log.info("Shutting down RAgent Router")


app = FastAPI(
    title="RAgent Router",
    description="AI Cost Optimization & Smart Routing Layer for Claude Code",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
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


# ── Request logging middleware ─────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    elapsed_ms = int((time.time() - t0) * 1000)

    req_log = request_logger()
    req_log.debug(
        "%s %s → %s (%dms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )

    # Route decision headers for /v1/messages
    model = response.headers.get("x-ragent-model", "")
    provider = response.headers.get("x-ragent-provider", "")
    reason = response.headers.get("x-ragent-reason", "")
    if model:
        get_logger("ragent.route").info(
            "→ %-16s | %-8s | %s",
            model,
            provider,
            reason,
        )

    return response


# Register routers
app.include_router(messages.router)
app.include_router(dashboard.router)
app.include_router(rules.router)
app.include_router(ccswitch.router)
app.include_router(traffic.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ragent-router", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
