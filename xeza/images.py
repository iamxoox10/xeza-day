import io
from datetime import datetime
from urllib.parse import quote

import httpx
import imagehash
from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS


def _ratio(v):
    return v[0] / v[1] if isinstance(v, tuple) and v[1] else float(v)


def exif(data: bytes) -> dict:
    out = {"gps": None, "camera": None, "taken": None}
    try:
        img = Image.open(io.BytesIO(data))
        raw = img._getexif() or {}
    except Exception:
        return out
    for tag, val in raw.items():
        name = TAGS.get(tag, tag)
        if name == "Make":
            out["camera"] = str(val)
        if name == "DateTimeOriginal":
            try:
                out["taken"] = datetime.strptime(str(val), "%Y:%m:%d %H:%M:%S").isoformat()
            except Exception:
                pass
        if name == "GPSInfo":
            g = {GPSTAGS.get(k, k): v for k, v in val.items()}
            try:
                lat = _ratio(g["GPSLatitude"][0]) + _ratio(g["GPSLatitude"][1]) / 60 + _ratio(g["GPSLatitude"][2]) / 3600
                lon = _ratio(g["GPSLongitude"][0]) + _ratio(g["GPSLongitude"][1]) / 60 + _ratio(g["GPSLongitude"][2]) / 3600
                if g.get("GPSLatitudeRef") == "S":
                    lat = -lat
                if g.get("GPSLongitudeRef") == "W":
                    lon = -lon
                out["gps"] = {"lat": round(lat, 6), "lon": round(lon, 6),
                              "maps": f"https://maps.google.com/?q={lat:.6f},{lon:.6f}"}
            except Exception:
                pass
    return out


def phash(data: bytes) -> str | None:
    try:
        return str(imagehash.phash(Image.open(io.BytesIO(data)).convert("RGB")))
    except Exception:
        return None


def reverse_links(url: str) -> list[dict]:
    return [
        {"kind": "reverse", "value": n, "url": u.format(q=quote(url, safe="")), "method": "js", "weight": 0.6}
        for n, u in [
            ("Google Lens", "https://lens.google.com/uploadbyurl?url={q}"),
            ("Yandex", "https://yandex.com/images/search?rpt=imageview&url={q}"),
            ("Bing Visual", "https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{q}"),
            ("TinEye", "https://tineye.com/search?url={q}"),
        ]
    ]


async def fetch(url: str) -> bytes | None:
    async with httpx.AsyncClient(follow_redirects=True, timeout=25) as c:
        try:
            r = await c.get(url)
            return r.content if r.status_code == 200 else None
        except Exception:
            return None


def match(target: str, candidate: str) -> int | None:
    if not target or not candidate:
        return None
    try:
        return imagehash.hex_to_hash(target) - imagehash.hex_to_hash(candidate)
    except Exception:
        return None