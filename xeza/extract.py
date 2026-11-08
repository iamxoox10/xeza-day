import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}")
PHONE = re.compile(r"(?<![\d.])(\+?\d[\d\s().-]{7,16}\d)(?![\d.])")
HANDLE = re.compile(
    r"(?:twitter\.com|x\.com|instagram\.com|t\.me|github\.com|tiktok\.com/@|bsky\.app/profile)/([A-Za-z0-9_.-]{2,32})"
)
SITE = re.compile(r"https?://(?!\S*(?:twitter|x\.com|instagram|tiktok|facebook|github|t\.me|youtube))[^\s\"'<>)]+")
NAME = re.compile(r'"(?:name|displayName|full_name|fullName)"\s*:\s*"([^"]{2,60})"')


def harvest(html: str) -> dict:
    text = html[:200000]
    return {
        "emails": sorted(set(EMAIL.findall(text)))[:8],
        "phones": sorted(
            {re.sub(r"[^\d+]", "", p) for p in PHONE.findall(text) if len(re.sub(r"\D", "", p)) >= 8}
        )[:6],
        "handles": sorted(set(HANDLE.findall(text)))[:10],
        "sites": sorted(set(SITE.findall(text)))[:10],
        "names": sorted(set(NAME.findall(text)))[:4],
    }