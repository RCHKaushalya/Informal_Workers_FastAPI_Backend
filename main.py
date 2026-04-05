from __future__ import annotations

import logging
import os
import threading
import time
import urllib.request

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routes import auth, users, jobs, integration, legacy

app = FastAPI(title="Informal Workers API | Premium Optimized")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Modular Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(jobs.router)
app.include_router(integration.router)
app.include_router(legacy.router)

_logger = logging.getLogger("keepalive")
_self_ping_started = False


def _start_self_ping_worker() -> None:
    global _self_ping_started
    if _self_ping_started:
        return
    url = os.getenv("SELF_PING_URL") or "https://informal-worker.onrender.com"
    interval_seconds = int(os.getenv("SELF_PING_INTERVAL_SECONDS", "600"))
    _self_ping_started = True

    def _worker():
        _logger.info(f"Self-ping worker started targeting {url}")
        while True:
            try:
                urllib.request.urlopen(url, timeout=10).read()
                _logger.info("Self-ping success")
            except Exception as exc:
                _logger.warning("self ping failed: %s", exc)
            time.sleep(interval_seconds)

    thread = threading.Thread(target=_worker, daemon=True, name="self-ping-worker")
    thread.start()


@app.on_event("startup")
def startup() -> None:
    init_db()
    _start_self_ping_worker()


@app.get("/")
def home():
    return {
        "status": "online",
        "api": "Informal Workers API v2.1",
        "modules": ["auth", "users", "jobs", "integrations"],
        "message": "Platform optimized for premium web portal."
    }


@app.get("/health")
def health():
    return {"ok": True}