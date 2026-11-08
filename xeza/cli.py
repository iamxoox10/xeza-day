import asyncio
import json
import warnings

import typer
import uvicorn
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from . import engine

load_dotenv()
warnings.filterwarnings("ignore")

app = typer.Typer()
console = Console()


@app.command()
def trace(kind: str, query: str, depth: int = 2, region: str | None = None):
    """kind: username | email | phone | image"""
    jid = engine.new_job(kind, query)
    asyncio.run(engine.run(jid, depth, region))
    job = engine.JOBS[jid]
    table = Table(title=f"{kind}: {query} — {job.get('verdict', '?')}")
    for c in ("kind", "value", "method", "score"):
        table.add_column(c)
    for e in sorted(job["edges"], key=lambda x: -x["score"]):
        table.add_row(e["kind"], str(e["value"])[:44], e["method"], str(e["score"]))
    console.print(table)


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000):
    uvicorn.run("xeza.server:app", host=host, port=port)


@app.command()
def json_out(kind: str, query: str):
    jid = engine.new_job(kind, query)
    asyncio.run(engine.run(jid))
    print(json.dumps(engine.public(jid), indent=2))


if __name__ == "__main__":
    app()