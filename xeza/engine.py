import asyncio
import httpx
from . import usernames, emails, phones, domains, images, score

async def run_scan_job(kind: str, raw_query: str, depth: int, log_callback, edge_callback):
    # Split multiple targets by comma or newline
    targets = [t.strip() for t in raw_query.replace("\n", ",").split(",") if t.strip()]
    await log_callback(f"[*] INITIALIZING BATCH RECON FOR {len(targets)} TARGET(S) [Vector: {kind.upper()}]")
    
    all_edges = []
    async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
        for target in targets:
            await log_callback(f"[+] Targeting entity: {target}")
            res = []
            if kind == "username":
                res = await usernames.check_usernames(target, client)
            elif kind == "email":
                res = await emails.profile_email(target, client)
            elif kind == "phone":
                res = await phones.profile_phone(target)
            elif kind == "domain":
                res = await domains.profile_domain(target)
            elif kind == "crypto":
                res = await domains.profile_crypto(target)
            elif kind == "image":
                res = await images.profile_image(target, client)
            
            for item in res:
                item["score"] = score.calculate(item.get("kind", ""), item.get("value", ""))
                all_edges.append(item)
                await edge_callback(item)
                await asyncio.sleep(0.05)

    verdict = "HIGH RISK / FOOTPRINT DETECTED" if len(all_edges) > 5 else "MODERATE / LIMITED FOOTPRINT"
    return {"verdict": verdict, "edges": all_edges}