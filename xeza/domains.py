import httpx

async def profile_domain(domain: str):
    domain = domain.strip().replace("https://", "").replace("http://", "").split("/")[0]
    results = [
        {"kind": "Domain Target", "value": f"Target Host: {domain}", "score": 1, "method": "Parser"},
        {"kind": "Whois Record", "value": f"Query domain registration details", "score": 4, "method": "Whois Lookup", "url": f"https://whois.domaintools.com/{domain}"},
        {"kind": "DNS & IP Map", "value": f"Resolve subdomains and IP telemetry", "score": 5, "method": "DNS Recon", "url": f"https://securitytrails.com/domain/{domain}/dns"},
        {"kind": "Threat Intel", "value": f"Check VirusTotal reputation for {domain}", "score": 7, "method": "VirusTotal", "url": f"https://www.virustotal.com/gui/domain/{domain}"}
    ]
    return results

async def profile_crypto(wallet: str):
    wallet = wallet.strip()
    results = [{"kind": "Wallet Vector", "value": f"Address: {wallet}", "score": 2, "method": "Parser"}]
    if wallet.startswith("0x"):
        results.append({"kind": "Etherscan Tracker", "value": "Inspect Ethereum / EVM Transactions", "score": 6, "method": "Blockchain API", "url": f"https://etherscan.io/address/{wallet}"})
    elif wallet.startswith("bc1") or wallet.startswith("1") or wallet.startswith("3"):
        results.append({"kind": "Bitcoin Explorer", "value": "Inspect BTC Ledger & Transactions", "score": 6, "method": "Blockchain API", "url": f"https://www.blockchain.com/explorer/addresses/btc/{wallet}"})
    else:
        results.append({"kind": "Solana Tracker", "value": "Inspect Solana Ledger", "score": 6, "method": "Blockchain API", "url": f"https://solscan.io/account/{wallet}"})
    return results