import re
from urllib.parse import parse_qs, urlparse

import httpx

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}


async def search(query: str, limit: int = 12) -> list[dict]:
    async with httpx.AsyncClient(headers=UA, follow_redirects=True) as c:
        try:
            r = await c.get("https://html.duckduckgo.com/html/", params={"q": query}, timeout=20)
        except Exception:
            return []
    out = []
    for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.S):
        href, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if "uddg=" in href:
            href = parse_qs(urlparse(href).query).get("uddg", [href])[0]
        out.append({"kind": "mention", "value": title[:90], "url": href, "method": "js", "weight": 0.5})
        if len(out) >= limit:
            break
    return out