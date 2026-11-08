import asyncio
import difflib
from pathlib import Path

import httpx
import yaml

SITES = yaml.safe_load((Path(__file__).parent / "data" / "sites.yaml").read_text(encoding="utf-8"))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"


async def _probe(client, site, username, controls, sem):
    url = site["url"].format(u=username)
    async with sem:
        try:
            r = await client.get(url, timeout=12, follow_redirects=True)
        except Exception:
            return None

        if r.status_code in (404, 410):
            return None

        if site.get("api"):
            body = r.text.strip()
            if r.status_code == 200 and body not in ("", "{}", "[]", "null"):
                if "not found" not in body.lower()[:400]:
                    return {"site": site["name"], "url": url, "method": "api", "weight": site["weight"]}
            return None

        ctrl = controls.get(site["name"])
        if ctrl is None:
            try:
                ctrl = await client.get(site["control"], timeout=12, follow_redirects=True)
                controls[site["name"]] = ctrl
            except Exception:
                ctrl = None

        if ctrl is not None:
            if ctrl.status_code in (404, 410) and r.status_code == 200:
                return {"site": site["name"], "url": url, "method": "diff", "weight": site["weight"]}
            if ctrl.status_code == 200 and r.status_code == 200:
                ratio = difflib.SequenceMatcher(None, r.text[:9000], ctrl.text[:9000]).quick_ratio()
                if ratio > 0.93:
                    return None
                return {"site": site["name"], "url": url, "method": "diff", "weight": site["weight"]}

        if site.get("js") and r.status_code == 200:
            return {"site": site["name"], "url": url, "method": "js", "weight": site["weight"]}
        return None


async def hunt(username: str, concurrency: int = 24, progress=None) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)
    controls: dict = {}
    hits: list[dict] = []
    headers = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}

    async with httpx.AsyncClient(headers=headers, verify=False) as client:
        tasks = [_probe(client, s, username, controls, sem) for s in SITES]
        for coro in asyncio.as_completed(tasks):
            res = await coro
            if res:
                hits.append(res)
                if progress:
                    await progress(f"hit {res['site']} [{res['method']}]")
    hits.sort(key=lambda h: -h["weight"])
    return hits