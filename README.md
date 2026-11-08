# XeZa Day

OSINT pivot engine. One identifier in — the public trail out.

Give it a username, email, phone number, or image URL. It enumerates public
sources, extracts new identifiers from what it finds, and scores how strongly
each hit ties back to the original.

## Run (Codespaces)

    pip install -e .
    pip install holehe
    cp .env.example .env     # add a GitHub token
    xeza serve --port 8000

Open the forwarded port.

## Inputs

| kind | example |
|---|---|
| username | `torvalds` |
| email | `someone@example.com` |
| phone | `+14155550123` |
| image | `https://example.com/photo.jpg` |

## How detection works

Every site is requested twice: once with your target, once with a junk
username. Status codes and body similarity are compared, so sites that return
200 for everything get filtered out.

## Scoring

api 3.0 · body diff 2.0 · js-gated 0.7

Verdict: weak / possible / probable / certain.

## Limits

- JS-heavy sites (Instagram, X, TikTok) are link-only
- Phone to real name needs paid APIs; free path is dorking + Telegram presence
- Image matching is perceptual hash, not facial recognition
- Public surface only

MIT licensed.