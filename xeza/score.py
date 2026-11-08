CONFIRM = {"api": 3.0, "diff": 2.0, "js": 0.7}

RANK = [(80, "certain"), (55, "probable"), (30, "possible"), (0, "weak")]


def edge(weight: float, method: str) -> float:
    return round(weight * CONFIRM.get(method, 1.0), 2)


def verdict(total: float) -> str:
    for floor, label in RANK:
        if total >= floor:
            return label
    return "weak"


def identity_score(edges: list[dict]) -> float:
    seen = set()
    total = 0.0
    for e in edges:
        key = (e["kind"], e["value"])
        if key in seen:
            continue
        seen.add(key)
        total += e["weight"]
    return round(min(total, 100.0), 2)