import asyncio
import hashlib
import os
import shutil

import dns.asyncresolver
import httpx

UA = {"User-Agent": "Mozilla/5.0 XeZaDay/0.2"}


async def dns_profile(email: str) -> dict:
    domain = email.split("@")[-1]
    resolver = dns.asyncresolver.Resolver()
    out = {"domain": domain}
    for rec in ("MX", "TXT", "A"):
        try:
            out[rec] = [str(r) for r in await resolver.resolve(domain, rec)]
        except Exception:
            out[rec] = []
    return out


async def gravatar(email: str) -> dict | None:
    digest = hashlib.md5(email.strip().lower().encode()).hexdigest()
    async with httpx.AsyncClient(headers=UA) as c:
        try:
            r = await c.get(f"https://gravatar.com/{digest}.json", timeout=10)
            if r.status_code == 200:
                d = r.json().get("entry", [{}])[0]
                return {
                    "kind": "gravatar",
                    "value": d.get("displayName") or digest,
                    "url": d.get("profileUrl", f"https://gravatar.com/{digest}"),
                    "method": "api",
                    "weight": 3.0,
                    "extra": {"name": d.get("name"), "about": d.get("aboutMe"), "avatar": d.get("thumbnailUrl")},
                }
        except Exception:
            pass
    return None


async def github_search(email: str) -> list[dict]:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return []
    async with httpx.AsyncClient(headers={**UA, "Authorization": f"Bearer {token}"}) as c:
        try:
            r = await c.get("https://api.github.com/search/users", params={"q": f"{email} in:email"}, timeout=15)
            return [
                {"kind": "github", "value": i["login"], "url": i["html_url"], "method": "api", "weight": 2.5}
                for i in r.json().get("items", [])[:5]
            ]
        except Exception:
            return []


async def hibp(email: str) -> list[str]:
    key = os.getenv("HIBP_KEY")
    if not key:
        return []
    async with httpx.AsyncClient(headers={**UA, "hibp-api-key": key}) as c:
        try:
            r = await c.get(
                f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
                params={"truncateResponse": "true"},
                timeout=15,
            )
            return [b["Name"] for b in r.json()] if r.status_code == 200 else []
        except Exception:
            return []


async def holehe(email: str) -> list[dict]:
    if not shutil.which("holehe"):
        return []
    proc = await asyncio.create_subprocess_exec(
        "holehe", email, "--only-used", "--no-gravatar",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    raw, _ = await proc.communicate()
    out = []
    for line in raw.decode(errors="replace").splitlines():
        if line.startswith("[+]"):
            parts = line.split()
            if len(parts) > 1:
                out.append({"kind": "registration", "value": parts[1].strip(":"), "url": None,
                            "method": "diff", "weight": 1.5})
    return out[:40]