"""Research agent: finds trending health insurance topics and turns them into pain points.

It runs a set of Firecrawl searches limited to the past N months, scores recurring
themes by how many distinct sources mention them, and writes pain_points.json.
Each pain point keeps its source URLs so every claim in the copy can be verified.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field

from .firecrawl_client import FirecrawlClient

QUERIES = [
    "small business health insurance premium increase",
    "self-employed health insurance cost ACA subsidies expired",
    "employer health benefits survey premiums",
    "ICHRA CHOICE arrangement small business",
    "health insurance prior authorization denials",
    "PPO vs HMO narrow network out of network costs",
    "health insurance tax deduction business owners self-employed",
    "open enrollment 2027 premium rate filings",
]

# theme -> (keywords that signal it, employer angle, employee angle)
THEMES: dict[str, tuple[list[str], str, str]] = {
    "subsidy_cliff": (
        ["subsid", "tax credit", "400%", "cliff", "premium tax"],
        "High earners lost marketplace subsidies, so owners who relied on the exchange are now paying full price.",
        "Employees above the subsidy line face the same full-price exchange premiums on their own.",
    ),
    "premium_spike": (
        ["premium", "rate increase", "rose", "jump", "% increase", "cost"],
        "Group and individual premiums keep climbing, squeezing margins for small firms.",
        "Higher payroll deductions and deductibles eat into take-home pay.",
    ),
    "network_access": (
        ["narrow network", "out-of-network", "out of network", "ppo", "hmo", "network"],
        "A broad PPO network is a recruiting edge when competitors offer narrow HMOs.",
        "Keeping your own doctors and seeing specialists without referrals.",
    ),
    "prior_auth": (
        ["prior authorization", "prior auth", "denial", "denied"],
        "Fewer coverage hassles means less time lost to benefits complaints.",
        "Less friction getting care approved.",
    ),
    "tax_strategy": (
        ["deduct", "tax-deductible", "tax advantage", "hsa", "payroll tax"],
        "Employer-paid premiums are generally deductible and exempt from payroll taxes (confirm with a tax pro).",
        "Employer-paid premiums are generally not taxable income to the employee.",
    ),
    "ichra_alternatives": (
        ["ichra", "choice arrangement", "level-funded", "level funded", "reimbursement arrangement"],
        "New plan structures let small firms control cost; a group PPO is the simpler, richer option to compare.",
        "Employees want a real plan, not just an allowance to shop the exchange.",
    ),
    "talent_retention": (
        ["retention", "recruit", "talent", "attract", "employees value"],
        "Benefits are a top reason employees stay; a strong plan helps compete with bigger firms.",
        "Security for their family and a reason to stay.",
    ),
}


@dataclass
class PainPoint:
    theme: str
    score: int
    employer_angle: str
    employee_angle: str
    evidence: list[dict] = field(default_factory=list)  # [{url, title, snippet}]


def score_results(results: list[dict]) -> list[PainPoint]:
    hits: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in results:
        text = f"{r.get('title', '')} {r.get('description', '')} {r.get('markdown', '')}".lower()
        for theme, (keywords, _, _) in THEMES.items():
            if any(k in text for k in keywords):
                hits[theme].setdefault(r.get("url", ""), {
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "snippet": re.sub(r"\s+", " ", r.get("description", ""))[:300],
                })
    points = [
        PainPoint(theme, len(urls), THEMES[theme][1], THEMES[theme][2], list(urls.values())[:5])
        for theme, urls in hits.items()
    ]
    return sorted(points, key=lambda p: p.score, reverse=True)


def run(client: FirecrawlClient, months: int = 3, per_query: int = 8) -> list[PainPoint]:
    results: list[dict] = []
    for q in QUERIES:
        results.extend(client.search(q, limit=per_query, tbs=f"qdr:m{months}"))
    return score_results(results)


def save(points: list[PainPoint], path: str) -> None:
    with open(path, "w") as fh:
        json.dump([asdict(p) for p in points], fh, indent=2)


def load(path: str) -> list[dict]:
    with open(path) as fh:
        return json.load(fh)
