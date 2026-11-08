import os
import uuid
import asyncio
from pathlib import Path
from fastapi import FastAPI, Depends, Request, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from .auth import verify_credentials
from .engine import run_scan_job

app = FastAPI(title="ORAKX-CORE OSINT SUITE", version="4.0.0")

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

jobs_store = {}

@app.get("/", response_class=HTMLResponse)
def index(username: str = Depends(verify_credentials)):
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h3>Error: static/index.html missing.</h3>"

@app.post("/api/trace")
async def start_trace(kind: str = Form(...), q: str = Form(...), depth: int = Form(2), username: str = Depends(verify_credentials)):
    job_id = str(uuid.uuid4())[:8]
    jobs_store[job_id] = {"kind": kind, "query": q, "depth": depth, "status": "running", "logs": [], "edges": []}
    return {"job": job_id}

# Also support JSON / Query params for trace if needed
@app.post("/api/trace/json")
async def start_trace_json(payload: dict, username: str = Depends(verify_credentials)):
    job_id = str(uuid.uuid4())[:8]
    kind = payload.get("kind", "username")
    q = payload.get("q", "")
    depth = int(payload.get("depth", 2))
    jobs_store[job_id] = {"kind": kind, "query": q, "depth": depth, "status": "running", "logs": [], "edges": []}
    return {"job": job_id}

@app.get("/api/stream/{job_id}")
async def stream_job(job_id: str, request: Request, username: str = Depends(verify_credentials)):
    job = jobs_store.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    async def event_generator():
        q_queue = asyncio.Queue()

        async def log_cb(msg):
            await q_queue.put(("log", msg))

        async def edge_cb(edge):
            await q_queue.put(("edge", edge))

        async def background_runner():
            res = await run_scan_job(job["kind"], job["query"], job["depth"], log_cb, edge_cb)
            await q_queue.put(("done", res))

        task = asyncio.create_task(background_runner())

        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev_type, data = await asyncio.wait_for(q_queue.get(), timeout=0.5)
                    if ev_type == "log":
                        yield {"event": "log", "data": data}
                    elif ev_type == "edge":
                        import json
                        yield {"event": "edge", "data": json.dumps(data)}
                    elif ev_type == "done":
                        import json
                        yield {"event": "done", "data": json.dumps(data)}
                        break
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "alive"}
        except Exception:
            pass
        finally:
            task.cancel()

    return EventSourceResponse(event_generator())