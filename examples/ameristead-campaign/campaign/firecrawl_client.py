"""Thin client for the Firecrawl v2 REST API (search + JSON extraction scrape)."""
from __future__ import annotations

from typing import Any

import requests

BASE_URL = "https://api.firecrawl.dev/v2"


class FirecrawlClient:
    def __init__(self, api_key: str, session: requests.Session | None = None, timeout: int = 120):
        # With no key in the environment, the request goes out without an Authorization
        # header so a proxy holding the key as a network secret can add it.
        self.session = session or requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"
        self.timeout = timeout

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        resp = self.session.post(f"{BASE_URL}{path}", json=body, timeout=self.timeout)
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("success", True):
            raise RuntimeError(f"Firecrawl error on {path}: {payload}")
        return payload

    def search(self, query: str, limit: int = 10, tbs: str | None = None, sources: list[str] | None = None) -> list[dict]:
        """Returns web results: [{url, title, description}, ...]. tbs='qdr:m3' = past 3 months."""
        body: dict[str, Any] = {"query": query, "limit": limit, "sources": sources or ["web"]}
        if tbs:
            body["tbs"] = tbs
        data = self._post("/search", body).get("data", {})
        if isinstance(data, list):  # older response shape
            return data
        return data.get("web", []) + data.get("news", [])

    def extract(self, url: str, schema: dict, prompt: str) -> dict:
        """Scrape one page and return structured JSON matching `schema`."""
        body = {
            "url": url,
            "formats": [{"type": "json", "schema": schema, "prompt": prompt}],
            "onlyMainContent": False,
        }
        return self._post("/scrape", body).get("data", {}).get("json") or {}
