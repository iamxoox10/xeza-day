import os
import re

import httpx
import phonenumbers
from phonenumbers import carrier, geocoder
from phonenumbers import timezone as pntz

UA = {"User-Agent": "Mozilla/5.0 XeZaDay/0.2"}


def profile(raw: str, region: str | None = None) -> dict:
    region = region or os.getenv("DEFAULT_REGION", "US")
    try:
        num = phonenumbers.parse(raw, region)
    except Exception:
        return {"valid": False, "raw": raw}
    if not phonenumbers.is_valid_number(num):
        return {"valid": False, "raw": raw}
    return {
        "valid": True,
        "e164": phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164),
        "national": phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.NATIONAL),
        "region": geocoder.description_for_number(num, "en"),
        "carrier": carrier.name_for_number(num, "en"),
        "line": str(phonenumbers.number_type(num)),
        "tz": pntz.time_zones_for_number(num),
    }


async def telegram(e164: str) -> dict | None:
    async with httpx.AsyncClient(headers=UA, follow_redirects=True) as c:
        try:
            r = await c.get(f"https://t.me/{e164}", timeout=12)
            if "tgme_page_title" in r.text:
                m = re.search(r"tgme_page_title[^>]*>([^<]{1,80})<", r.text)
                return {"kind": "telegram", "value": (m.group(1).strip() if m else e164),
                        "url": f"https://t.me/{e164}", "method": "api", "weight": 2.5}
        except Exception:
            pass
    return None


def links(e164: str) -> list[dict]:
    bare = e164.lstrip("+")
    return [
        {"kind": "link", "value": "WhatsApp", "url": f"https://wa.me/{bare}", "method": "js", "weight": 0.7},
        {"kind": "link", "value": "Viber", "url": f"viber://chat?number={e164}", "method": "js", "weight": 0.4},
        {"kind": "link", "value": "Signal", "url": f"https://signal.me/#p/{e164}", "method": "js", "weight": 0.4},
    ]