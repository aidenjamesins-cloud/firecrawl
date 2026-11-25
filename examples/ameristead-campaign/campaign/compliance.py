"""Compliance filter. Fails closed: anyone who cannot be cleared is excluded.

A prospect is kept only if ALL of these hold:
  * not on the suppression list (unsubscribes, bounces, complaints, do-not-contact)
  * the state is one the agent is licensed in (when LICENSED_STATES is set; else excluded)
  * at least one scrub provider is configured, and every provider returns "clear"
    for both DNC and litigator status
  * a phone number exists to check against DNC, unless REQUIRE_PHONE_FOR_DNC_CHECK=false

Providers implement `check(phone, email) -> ScrubResult`. Add new vendors by
subclassing ScrubProvider; see CsvListProvider and HttpScrubProvider.
"""
from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass, field

import requests

from .config import Settings
from .prospect_scraper import Prospect, normalize_phone


@dataclass
class ScrubResult:
    dnc: bool | None = None        # True = on DNC, None = unknown
    litigator: bool | None = None  # True = known TCPA litigator, None = unknown
    source: str = ""


class ScrubProvider:
    name = "base"

    def check(self, phone: str, email: str) -> ScrubResult:  # pragma: no cover
        raise NotImplementedError


def _read_values(path: str) -> set[str]:
    values: set[str] = set()
    if not path or not os.path.exists(path):
        return values
    with open(path, newline="") as fh:
        for row in csv.reader(fh):
            for cell in row:
                cell = cell.strip().lower()
                if "@" in cell:
                    values.add(cell)
                elif normalize_phone(cell):
                    values.add(normalize_phone(cell))
    return values


class CsvListProvider(ScrubProvider):
    """Local lists: an FTC DNC download (phones) and a litigator list (phones and/or emails).

    The provider can only say "clear" for a list it actually has, so a missing file
    leaves that status unknown, which the filter treats as excluded.
    """
    name = "csv"

    def __init__(self, dnc_path: str = "", litigator_path: str = ""):
        self.has_dnc = bool(dnc_path) and os.path.exists(dnc_path)
        self.has_lit = bool(litigator_path) and os.path.exists(litigator_path)
        self.dnc = _read_values(dnc_path)
        self.lit = _read_values(litigator_path)

    def check(self, phone: str, email: str) -> ScrubResult:
        dnc = (phone in self.dnc) if (self.has_dnc and phone) else None
        lit = None
        if self.has_lit:
            lit = (email.lower() in self.lit) or (bool(phone) and phone in self.lit)
        return ScrubResult(dnc=dnc, litigator=lit, source=self.name)


class ClearedListProvider(ScrubProvider):
    """For a DNC and litigator scrub done outside this tool.

    Send the scraped prospects CSV through your scrub process and save the records that
    came back CLEAR of both DNC and litigator lists (any CSV with an email and/or phone
    column). Only those are cleared; anyone missing from the file stays excluded.
    """
    name = "external scrub"

    def __init__(self, cleared_path: str):
        self.cleared = _read_values(cleared_path)

    def check(self, phone: str, email: str) -> ScrubResult:
        if email.lower() in self.cleared or (phone and phone in self.cleared):
            return ScrubResult(dnc=False, litigator=False, source=self.name)
        return ScrubResult(source=self.name)


class HttpScrubProvider(ScrubProvider):
    """Generic vendor API. Expects POST {phone, email} -> {"dnc": bool, "litigator": bool}.

    Adapt `parse` for your vendor's response. Any error returns unknown (excluded).
    """
    name = "http"

    def __init__(self, url: str, api_key: str, session: requests.Session | None = None):
        self.url, self.api_key = url, api_key
        self.session = session or requests.Session()

    def parse(self, body: dict) -> ScrubResult:
        def flag(key: str) -> bool | None:
            v = body.get(key)
            return v if isinstance(v, bool) else None
        return ScrubResult(dnc=flag("dnc"), litigator=flag("litigator"), source=self.name)

    def check(self, phone: str, email: str) -> ScrubResult:
        try:
            resp = self.session.post(self.url, json={"phone": phone, "email": email},
                                     headers={"Authorization": f"Bearer {self.api_key}"}, timeout=30)
            resp.raise_for_status()
            return self.parse(resp.json())
        except Exception:
            return ScrubResult(source=self.name)


@dataclass
class FilterReport:
    kept: list[Prospect] = field(default_factory=list)
    excluded: list[tuple[Prospect, str]] = field(default_factory=list)


class ComplianceFilter:
    def __init__(self, providers: list[ScrubProvider], suppression: set[str],
                 licensed_states: list[str], require_phone: bool = True, external_scrub: bool = False):
        # external_scrub=True: DNC and litigator checks are done by the operator's team on
        # the exported file before import. Suppression and licensed-state checks still run.
        self.external_scrub = external_scrub
        self.providers = providers
        self.suppression = {s.lower() for s in suppression}
        self.licensed_states = {s.upper() for s in licensed_states}
        self.require_phone = require_phone

    @classmethod
    def from_settings(cls, s: Settings) -> "ComplianceFilter":
        providers: list[ScrubProvider] = []
        if s.scrub_cleared_csv_path:
            providers.append(ClearedListProvider(s.scrub_cleared_csv_path))
        if s.dnc_csv_path or s.litigator_csv_path:
            providers.append(CsvListProvider(s.dnc_csv_path, s.litigator_csv_path))
        if s.scrub_api_url:
            providers.append(HttpScrubProvider(s.scrub_api_url, s.scrub_api_key))
        return cls(providers, _read_values(s.suppression_csv_path), s.licensed_states,
                   s.require_phone_for_dnc_check, external_scrub=s.dnc_scrub == "external")

    def reason_to_exclude(self, p: Prospect) -> str | None:
        email = p.email.lower()
        domain = email.split("@")[-1]
        if email in self.suppression or f"@{domain}" in self.suppression:
            return "suppression list"
        if not self.licensed_states:
            return "no licensed states configured"
        if p.state.upper() not in self.licensed_states:
            return f"not licensed in {p.state or 'unknown state'}"
        if self.external_scrub:
            return None
        if not self.providers:
            return "no DNC/litigator scrub source configured"
        phone = normalize_phone(p.phone)
        if not phone and self.require_phone:
            return "no phone to check against DNC"
        dnc_cleared = not phone  # no phone and not required -> nothing to check
        lit_cleared = False
        for provider in self.providers:
            r = provider.check(phone, email)
            if r.dnc is True:
                return f"on DNC ({r.source})"
            if r.litigator is True:
                return f"known litigator ({r.source})"
            dnc_cleared = dnc_cleared or r.dnc is False
            lit_cleared = lit_cleared or r.litigator is False
        if not dnc_cleared:
            return "DNC status unknown"
        if not lit_cleared:
            return "litigator status unknown"
        return None

    def run(self, prospects: list[Prospect]) -> FilterReport:
        report = FilterReport()
        for p in prospects:
            why = self.reason_to_exclude(p)
            if why:
                report.excluded.append((p, why))
            else:
                report.kept.append(p)
        return report


def add_to_suppression(path: str, emails: list[str]) -> None:
    existing = _read_values(path)
    with open(path, "a", newline="") as fh:
        w = csv.writer(fh)
        for e in emails:
            e = e.strip().lower()
            if e and e not in existing and re.match(r".+@.+", e):
                w.writerow([e])
