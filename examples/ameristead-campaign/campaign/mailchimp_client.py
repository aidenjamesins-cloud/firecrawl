"""Mailchimp Marketing API v3: audience upload, niche segments, draft campaigns.

Safety: this client can create and edit drafts but cannot send or schedule. Any call
to a send/schedule/test endpoint raises, so nothing leaves Mailchimp until a person
reviews the drafts and sends them from the Mailchimp UI.

Mailchimp's Acceptable Use Policy requires permission to email every contact and
does not allow purchased, rented or scraped lists. `upload_members` therefore
requires confirm_permission=True; see the README before setting it.
"""
from __future__ import annotations

import hashlib
from typing import Any

import requests

from .copy import Email
from .prospect_scraper import Prospect

BLOCKED_ACTIONS = ("/actions/send", "/actions/schedule", "/actions/test", "/actions/replicate")
MERGE_FIELDS = [("BIZ", "Business name"), ("NICHE", "Niche"), ("STATE", "State"), ("SOURCE", "Source URL")]


class SendBlocked(RuntimeError):
    pass


def subscriber_hash(email: str) -> str:
    return hashlib.md5(email.strip().lower().encode()).hexdigest()


class MailchimpClient:
    def __init__(self, api_key: str, audience_id: str, session: requests.Session | None = None):
        if not api_key or "-" not in api_key:
            raise ValueError("MAILCHIMP_API_KEY is missing or has no data-center suffix (e.g. -us21)")
        if not audience_id:
            raise ValueError("MAILCHIMP_AUDIENCE_ID is not set")
        self.base = f"https://{api_key.rsplit('-', 1)[1]}.api.mailchimp.com/3.0"
        self.list_id = audience_id
        self.session = session or requests.Session()
        self.session.auth = ("anystring", api_key)

    def _request(self, method: str, path: str, **kw: Any) -> dict:
        if any(a in path for a in BLOCKED_ACTIONS):
            raise SendBlocked(f"Refusing {method} {path}: sending is done by a person in Mailchimp")
        resp = self.session.request(method, f"{self.base}{path}", timeout=60, **kw)
        if resp.status_code >= 400:
            raise RuntimeError(f"Mailchimp {method} {path} -> {resp.status_code}: {resp.text[:500]}")
        return resp.json() if resp.content else {}

    # ---- audience -------------------------------------------------------
    def ensure_merge_fields(self) -> None:
        existing = {f["tag"] for f in self._request("GET", f"/lists/{self.list_id}/merge-fields",
                                                     params={"count": 100}).get("merge_fields", [])}
        for tag, name in MERGE_FIELDS:
            if tag not in existing:
                self._request("POST", f"/lists/{self.list_id}/merge-fields",
                              json={"tag": tag, "name": name, "type": "text"})

    def upload_members(self, prospects: list[Prospect], confirm_permission: bool = False) -> int:
        if not confirm_permission:
            raise PermissionError("Upload blocked: confirm you have permission to email these contacts "
                                  "under Mailchimp's Acceptable Use Policy (see README).")
        self.ensure_merge_fields()
        for p in prospects:
            # status_if_new never re-subscribes someone who already unsubscribed or was cleaned.
            self._request("PUT", f"/lists/{self.list_id}/members/{subscriber_hash(p.email)}", json={
                "email_address": p.email,
                "status_if_new": "subscribed",
                "merge_fields": {"FNAME": p.first_name, "LNAME": p.last_name, "BIZ": p.business_name,
                                 "NICHE": p.niche, "STATE": p.state, "SOURCE": p.source_url[:255]},
            })
        return len(prospects)

    def unsubscribed_emails(self) -> list[str]:
        out: list[str] = []
        for status in ("unsubscribed", "cleaned"):
            offset = 0
            while True:
                page = self._request("GET", f"/lists/{self.list_id}/members", params={
                    "status": status, "count": 1000, "offset": offset, "fields": "members.email_address,total_items"})
                members = page.get("members", [])
                out.extend(m["email_address"].lower() for m in members)
                offset += len(members)
                if not members or offset >= page.get("total_items", 0):
                    break
        return out

    # ---- segments -------------------------------------------------------
    def upsert_niche_segment(self, niche: str, emails: list[str]) -> int:
        name = f"Ameristead PPO - {niche}"
        segs = self._request("GET", f"/lists/{self.list_id}/segments",
                             params={"type": "static", "count": 1000}).get("segments", [])
        for seg in segs:
            if seg["name"] == name:
                if emails:
                    self._request("POST", f"/lists/{self.list_id}/segments/{seg['id']}",
                                  json={"members_to_add": emails})
                return seg["id"]
        return self._request("POST", f"/lists/{self.list_id}/segments",
                             json={"name": name, "static_segment": emails})["id"]

    # ---- campaigns (drafts only) ----------------------------------------
    def create_draft(self, segment_id: int, niche: str, email: Email, from_name: str, reply_to: str) -> str:
        camp = self._request("POST", "/campaigns", json={
            "type": "regular",
            "recipients": {"list_id": self.list_id, "segment_opts": {"saved_segment_id": segment_id}},
            "settings": {
                "title": f"Ameristead PPO | {niche} | step {email.step} (send day +{email.send_day})",
                "subject_line": email.subject[:150],
                "preview_text": email.preview,
                "from_name": from_name,
                "reply_to": reply_to,
            },
        })
        self._request("PUT", f"/campaigns/{camp['id']}/content", json={"html": email.body_html})
        return camp["id"]
