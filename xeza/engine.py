import asyncio
import uuid
from datetime import datetime, timezone

import httpx

from . import dorks, emails, extract, images, phones, score, usernames

JOBS: dict[str, dict] = {}


def new_job(kind: str, query: str) -> str:
    jid = uuid.uuid4().hex[:12]
    JOBS[jid] = {
        "id": jid, "kind": kind, "query": query, "status": "running",
        "started": datetime.now(timezone.utc).isoformat(),
        "edges": [], "log": [], "meta": {}, "seen": set(),
    }
    return jid


async def emit(job: dict, msg: str, edge: dict | None = None):
    job["log"].append(msg)
    if edge:
        key = (edge["kind"], edge["value"])
        if key in job["seen"]:
            return
        job["seen"].add(key)
        edge["score"] = score.edge(edge.get("weight", 1.0), edge.get("method", "diff"))
        job["edges"].append(edge)
    await asyncio.sleep(0)


async def run(job_id: str, depth: int = 2, region: str | None = None):
    job = JOBS[job_id]
    q = job["query"]
    try:
        if job["kind"] == "username":
            await _username(job, q, depth)
        elif job["kind"] == "email":
            await _email(job, q, depth)
        elif job["kind"] == "phone":
            await _phone(job, q, region)
        elif job["kind"] == "image":
            await _image(job, q)
    except Exception as e:
        await emit(job, f"error: {e}")
    job["status"] = "done"
    job["verdict"] = score.verdict(score.identity_score(job["edges"]))


async def _username(job, username: str, depth: int):
    await emit(job, f"enumerating '{username}'")
    hits = await usernames.hunt(username, progress=lambda m: emit(job, m))
    for h in hits:
        await emit(job, f"+ {h['site']}", {**h, "kind": "profile"})

    await emit(job, "dorking")
    for d in await dorks.search(f'"{username}" -site:facebook.com'):
        await emit(job, f"mention: {d['value'][:50]}", d)

    if depth > 0:
        await _follow(job, [h["url"] for h in hits if h["method"] != "js"][:8], depth - 1)


async def _follow(job, urls: list[str], depth: int):
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as c:
        for url in urls:
            try:
                r = await c.get(url)
            except Exception:
                continue
            data = extract.harvest(r.text)
            for e in data["emails"]:
                await emit(job, f"email from {url}", {"kind": "email", "value": e, "url": url,
                                                      "method": "diff", "weight": 2.0})
            for p in data["phones"]:
                await emit(job, f"phone from {url}", {"kind": "phone", "value": p, "url": url,
                                                      "method": "diff", "weight": 2.0})
            for n in data["names"]:
                await emit(job, f"name: {n}", {"kind": "name", "value": n, "url": url,
                                               "method": "diff", "weight": 1.5})
            for h in data["handles"]:
                if depth > 0:
                    await emit(job, f"handle: {h}", {"kind": "handle", "value": h, "url": url,
                                                     "method": "diff", "weight": 1.2})
                    for m in (await usernames.hunt(h))[:6]:
                        await emit(job, f"+ {m['site']} ({h})", {**m, "kind": "profile"})
    job["meta"]["links_followed"] = len(urls)


async def _email(job, email: str, depth: int):
    await emit(job, f"profiling {email}")
    info = await emails.dns_profile(email)
    job["meta"]["dns"] = info
    await emit(job, f"mx: {', '.join(info['MX']) or 'none'}")

    g = await emails.gravatar(email)
    if g:
        await emit(job, "gravatar hit", g)
        if g["extra"].get("name"):
            await emit(job, f"name: {g['extra']['name']}", {"kind": "name", "value": g["extra"]["name"],
                                                            "url": g["url"], "method": "api", "weight": 3.0})
        if g["extra"].get("avatar"):
            job["meta"]["avatar"] = g["extra"]["avatar"]

    for gh in await emails.github_search(email):
        await emit(job, f"github: {gh['value']}", gh)
    for reg in await emails.holehe(email):
        await emit(job, f"registered: {reg['value']}", reg)

    breaches = await emails.hibp(email)
    job["meta"]["breaches"] = breaches
    if breaches:
        await emit(job, f"{len(breaches)} breaches")

    await emit(job, "dorking")
    for d in await dorks.search(f'"{email}"'):
        await emit(job, f"mention: {d['value'][:50]}", d)

    if depth > 0:
        handles = [e["value"] for e in job["edges"] if e["kind"] == "github"]
        await _follow(job, [f"https://github.com/{h}" for h in handles], depth - 1)


async def _phone(job, raw: str, region: str | None):
    p = phones.profile(raw, region)
    job["meta"]["phone"] = p
    if not p.get("valid"):
        await emit(job, "invalid number")
        return
    await emit(job, f"{p['e164']} | {p['region']} | {p['carrier']} | {p['line']}")

    tg = await phones.telegram(p["e164"])
    if tg:
        await emit(job, "telegram account", tg)
        await emit(job, f"name: {tg['value']}", {"kind": "name", "value": tg["value"],
                                                 "url": tg["url"], "method": "api", "weight": 3.0})

    for l in phones.links(p["e164"]):
        await emit(job, l["value"], l)

    await emit(job, "dorking")
    for variant in (p["e164"], p["national"]):
        for d in await dorks.search(f'"{variant}"'):
            await emit(job, f"mention: {d['value'][:50]}", d)


async def _image(job, url: str):
    await emit(job, "fetching image")
    data = await images.fetch(url)
    if not data:
        await emit(job, "fetch failed")
        return
    job["meta"]["exif"] = images.exif(data)
    job["meta"]["phash"] = images.phash(data)
    if job["meta"]["exif"].get("gps"):
        g = job["meta"]["exif"]["gps"]
        await emit(job, f"GPS {g['lat']},{g['lon']}", {"kind": "geo", "value": f"{g['lat']},{g['lon']}",
                                                      "url": g["maps"], "method": "api", "weight": 3.0})
    if job["meta"]["exif"].get("camera"):
        await emit(job, f"camera {job['meta']['exif']['camera']}")
    for l in images.reverse_links(url):
        await emit(job, l["value"], l)


def public(job_id: str) -> dict:
    j = JOBS[job_id]
    return {k: v for k, v in j.items() if k != "seen"}