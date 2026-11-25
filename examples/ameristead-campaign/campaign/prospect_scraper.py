"""Prospect scraper: finds business owners per niche from public business websites.

Flow per niche and state: Firecrawl search -> filter out sites whose terms forbid
scraping or that are aggregators -> Firecrawl JSON extraction of the business's own
contact page -> keep rows with a business email. Output columns match CSV_FIELDS.
"""
from __future__ import annotations

import csv
import re
from dataclasses import asdict, dataclass
from urllib.parse import urlparse

from .firecrawl_client import FirecrawlClient

NICHES: dict[str, list[str]] = {
    "med_spa": ["med spa owner {city} {state}", "medical spa {city} {state} contact"],
    "cpa": ["CPA firm {city} {state} contact us", "independent accountant {city} {state}"],
    "financial_advisor": ["independent financial advisor {city} {state} contact", "RIA firm {city} {state}"],
    "real_estate": ["real estate broker owner {city} {state} contact", "independent realty {city} {state}"],
    "dental_practice": ["dental practice owner {city} {state} contact"],
    "law_firm": ["small law firm {city} {state} contact"],
}

# Directories, social networks and aggregators: their terms restrict scraping, and
# listings there are not the owner's own published contact info.
BLOCKED_DOMAINS = {
    "linkedin.com", "facebook.com", "instagram.com", "yelp.com", "zillow.com", "realtor.com",
    "google.com", "yellowpages.com", "bbb.org", "angi.com", "thumbtack.com", "x.com", "twitter.com",
    "tiktok.com", "youtube.com", "indeed.com", "glassdoor.com", "nerdwallet.com", "finra.org",
}

GENERIC_PREFIXES = ("noreply", "no-reply", "donotreply", "privacy", "abuse", "webmaster")

CSV_FIELDS = ["email", "first_name", "last_name", "business_name", "niche", "city", "state",
              "phone", "employee_estimate", "source_url"]

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "business_name": {"type": "string"},
        "owner_first_name": {"type": "string"},
        "owner_last_name": {"type": "string"},
        "business_email": {"type": "string"},
        "phone": {"type": "string"},
        "city": {"type": "string"},
        "state": {"type": "string", "description": "two-letter US state code"},
        "employee_estimate": {"type": "integer", "description": "approximate staff count if shown"},
    },
    "required": ["business_name"],
}
EXTRACT_PROMPT = (
    "Extract the business's own published contact details. Use only an email address "
    "that appears on the page. Never guess or construct an email. Leave fields empty if absent."
)

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


@dataclass
class Prospect:
    email: str
    first_name: str
    last_name: str
    business_name: str
    niche: str
    city: str
    state: str
    phone: str
    employee_estimate: str
    source_url: str


def domain_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def is_blocked(url: str) -> bool:
    d = domain_of(url)
    return any(d == b or d.endswith("." + b) for b in BLOCKED_DOMAINS)


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits if len(digits) == 10 else ""


def to_prospect(data: dict, niche: str, url: str, fallback_city: str, fallback_state: str) -> Prospect | None:
    email = (data.get("business_email") or "").strip().lower()
    if not EMAIL_RE.match(email) or email.startswith(GENERIC_PREFIXES):
        return None
    emp = data.get("employee_estimate")
    return Prospect(
        email=email,
        first_name=(data.get("owner_first_name") or "").strip(),
        last_name=(data.get("owner_last_name") or "").strip(),
        business_name=(data.get("business_name") or "").strip(),
        niche=niche,
        city=(data.get("city") or fallback_city).strip(),
        state=((data.get("state") or fallback_state).strip().upper())[:2],
        phone=normalize_phone(data.get("phone") or ""),
        employee_estimate="" if emp in (None, "") else str(emp),
        source_url=url,
    )


def scrape_niche(client: FirecrawlClient, niche: str, locations: list[tuple[str, str]],
                 per_query: int = 10, max_employees: int = 99) -> list[Prospect]:
    seen_urls: set[str] = set()
    seen_emails: set[str] = set()
    out: list[Prospect] = []
    for city, state in locations:
        for template in NICHES[niche]:
            for r in client.search(template.format(city=city, state=state), limit=per_query):
                url = r.get("url", "")
                if not url or url in seen_urls or is_blocked(url):
                    continue
                seen_urls.add(url)
                try:
                    data = client.extract(url, EXTRACT_SCHEMA, EXTRACT_PROMPT)
                except Exception as exc:  # one bad page should not stop the run
                    print(f"  skip {url}: {exc}")
                    continue
                p = to_prospect(data, niche, url, city, state)
                if not p or p.email in seen_emails:
                    continue
                if p.employee_estimate and int(p.employee_estimate) > max_employees:
                    continue
                seen_emails.add(p.email)
                out.append(p)
    return out


def write_csv(prospects: list[Prospect], path: str) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        w.writeheader()
        for p in prospects:
            w.writerow(asdict(p))


def read_csv(path: str) -> list[Prospect]:
    with open(path, newline="") as fh:
        return [Prospect(**{k: row.get(k, "") for k in CSV_FIELDS}) for row in csv.DictReader(fh)]
