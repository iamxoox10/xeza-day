import asyncio
import base64
import json
import os
import secrets
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from . import engine

load_dotenv()
warnings.filterwarnings("ignore")

XEZA_USER = os.getenv("XEZA_USER", "admin")
XEZA_PASS = os.getenv("XEZA_PASS", "")


def res(*parts) -> Path:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base).joinpath(*parts)
    return Path(__file__).parent.parent.joinpath(*parts)


app = FastAPI(title="XeZa Day")
app.mount("/static", StaticFiles(directory=res("static")), name="s")


@app.middleware("http")
async def gate(request: Request, call_next):
    if not XEZA_PASS or request.url.path.startswith("/static"):
        return await call_next(request)
    hdr = request.headers.get("authorization", "")
    if hdr.startswith("Basic "):
        try:
            user, pw = base64.b64decode(hdr[6:]).decode().split(":", 1)
            if user == XEZA_USER and secrets.compare_digest(pw, XEZA_PASS):
                return await call_next(request)
        except Exception:
            pass
    return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="xeza"'})


@app.get("/")
async def index():
    return FileResponse(res("static", "index.html"))


@app.post("/api/trace")
async def trace(kind: str, q: str, depth: int = 2, region: str | None = None):
    if kind not in ("username", "email", "phone", "image"):
        raise HTTPException(400, "bad kind")
    jid = engine.new_job(kind, q)
    asyncio.create_task(engine.run(jid, depth, region))
    return {"job": jid}


@app.get("/api/stream/{jid}")
async def stream(jid: str):
    if jid not in engine.JOBS:
        raise HTTPException(404)

    async def gen():
        sent_log = sent_edges = 0
        job = engine.JOBS[jid]
        while True:
            while sent_log < len(job["log"]):
                yield {"event": "log", "data": job["log"][sent_log]}
                sent_log += 1
            while sent_edges < len(job["edges"]):
                yield {"event": "edge", "data": json.dumps(job["edges"][sent_edges])}
                sent_edges += 1
            if job["status"] == "done" and sent_log >= len(job["log"]) and sent_edges >= len(job["edges"]):
                yield {"event": "done", "data": json.dumps(engine.public(jid))}
                break
            await asyncio.sleep(0.25)

    return EventSourceResponse(gen())


@app.get("/api/job/{jid}")
async def job(jid: str):
    if jid not in engine.JOBS:
        raise HTTPException(404)
    return engine.public(jid)