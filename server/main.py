from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.chat_service import ChatService
from server.chat_api import router as chat_router, init_chat_api
from server.session_api import router as session_router
from server.search_api import router as search_router, init_search_api


@asynccontextmanager
async def lifespan(app: FastAPI):
    config_path = os.environ.get("MARX_CONFIG", "config.yaml")
    svc = ChatService(config_path)
    await svc.initialize()
    init_chat_api(svc)
    init_search_api(svc)
    yield


app = FastAPI(title="Marx AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(session_router)
app.include_router(search_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--config", default="config.yaml")
    args = p.parse_args()
    os.environ["MARX_CONFIG"] = args.config
    uvicorn.run("server.main:app", host=args.host, port=args.port, reload=True)
