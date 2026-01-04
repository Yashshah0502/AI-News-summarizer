# app/services/ranker.py
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

TECH_KW = {
    "openai": 2.0, "anthropic": 2.0, "google": 1.0, "microsoft": 1.0, "apple": 1.0,
    "nvidia": 1.5, "tesla": 0.8, "ai": 0.8, "llm": 1.0, "chip": 0.8, "gpu": 0.8,
    "cyber": 1.0, "security": 1.0, "breach": 1.2, "startup": 0.7, "funding": 0.9,
}

FINANCE_KW = {
    "stocks": 1.2, "equities": 1.2, "bond": 1.0, "bonds": 1.0, "yield": 1.0, "yields": 1.0,
    "forex": 1.0, "currency": 0.8, "rupee": 0.8, "dollar": 0.8, "oil": 0.8, "gold": 0.8,
    "inflation": 1.2, "cpi": 1.2, "gdp": 1.1, "interest rate": 1.2, "rates": 0.8,
    "fed": 1.2, "central bank": 1.2, "earnings": 1.0, "revenue": 0.6, "ipo": 0.8,
    "crypto": 0.8, "bitcoin": 0.8,
}

WORLD_KW = {
    "election": 0.8, "war": 1.0, "ceasefire": 1.0, "sanction": 1.0, "trade": 0.8,
    "tariff": 0.8, "diplomat": 0.6, "border": 0.6,
}

TOPIC_TARGETS_DEFAULT = {  # edit these
    "tech": 4,
    "finance": 3,
    "world": 2,
    "other": 1,
}

def _norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[^a-z0-9 ]+", "", s)
    return s

def classify_topic(title: str, category: Optional[str]) -> str:
    t = _norm(title)
    c = _norm(category or "")

    # category hints first
    if any(k in c for k in ["finance", "business", "markets", "economy", "money"]):
        return "finance"
    if any(k in c for k in ["tech", "technology", "ai", "startups"]):
        return "tech"
    if any(k in c for k in ["world", "international", "global", "geopolitics", "politics"]):
        return "world"

    # keyword fallback
    tech = sum(w for k, w in TECH_KW.items() if k in t)
    fin = sum(w for k, w in FINANCE_KW.items() if k in t)
    wor = sum(w for k, w in WORLD_KW.items() if k in t)

    best = max([("tech", tech), ("finance", fin), ("world", wor)], key=lambda x: x[1])
    return best[0] if best[1] > 0 else "other"

def score_article(title: str, scraped_at: datetime, topic: str, category: Optional[str] = None) -> float:
    now = datetime.now(timezone.utc)
    age_h = max((now - scraped_at).total_seconds() / 3600.0, 0.0)
    recency = 10.0 / (1.0 + age_h)

    t = _norm(title)
    kw = 0.0
    if topic == "tech":
        kw = sum(w for k, w in TECH_KW.items() if k in t)
    elif topic == "finance":
        kw = sum(w for k, w in FINANCE_KW.items() if k in t)
    elif topic == "world":
        kw = sum(w for k, w in WORLD_KW.items() if k in t)

    return recency + kw

def select_top_diverse(rows: List, per_source: int = 5, final_n: int = 10,
                       topic_targets: Optional[Dict[str, int]] = None) -> List[Tuple]:
    topic_targets = topic_targets or TOPIC_TARGETS_DEFAULT

    # 1) shortlist per source
    by_source: Dict[str, List] = {}
    for r in rows:
        by_source.setdefault(r.source, []).append(r)

    shortlisted: List = []
    for src, items in by_source.items():
        items.sort(
            key=lambda a: score_article(a.title, a.scraped_at, classify_topic(a.title, a.category), a.category),
            reverse=True,
        )
        shortlisted.extend(items[:per_source])

    # 2) dedupe by normalized title
    seen = set()
    deduped = []
    for a in sorted(
        shortlisted,
        key=lambda x: score_article(x.title, x.scraped_at, classify_topic(x.title, x.category), x.category),
        reverse=True,
    ):
        k = _norm(a.title)
        if k and k not in seen:
            seen.add(k)
            deduped.append(a)

    # 3) enforce topic mix
    buckets: Dict[str, List] = {}
    scored = []
    for a in deduped:
        topic = classify_topic(a.title, a.category)
        s = score_article(a.title, a.scraped_at, topic, a.category)
        scored.append((a, topic, s))
        buckets.setdefault(topic, []).append((a, topic, s))

    for topic in buckets:
        buckets[topic].sort(key=lambda x: x[2], reverse=True)

    picked: List[Tuple] = []
    for topic, target in topic_targets.items():
        for _ in range(target):
            if len(picked) >= final_n:
                break
            if buckets.get(topic):
                picked.append(buckets[topic].pop(0))

    if len(picked) < final_n:
        remaining = []
        for lst in buckets.values():
            remaining.extend(lst)
        remaining.sort(key=lambda x: x[2], reverse=True)
        picked.extend(remaining[: (final_n - len(picked))])

    return picked[:final_n]  # list of (Article, topic, score)
