"""Niche-specific 4-email drip copy.

Plan facts come from data/plans.json, which is transcribed from the Ameristead rate
flyer and the Cigna SBC PDFs. Anything still in [BRACKETS] is a placeholder;
`unfilled_tokens` finds those before a draft is created.

Mailchimp merge tags used: *|FNAME|*, *|BIZ|* (business name), *|UNSUB|*.
"""
from __future__ import annotations

import html
import json
import os
import re
from dataclasses import dataclass

from .config import Settings

PLANS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "plans.json")


def load_plans(path: str = PLANS_PATH) -> dict:
    with open(path) as fh:
        return json.load(fh)


NICHE_HOOKS = {
    "med_spa": {
        "label": "med spa owners",
        "who": "your injectors, nurses and aestheticians",
        "hook": "Skilled aesthetic staff get recruited away constantly, and benefits are often the deciding factor.",
    },
    "cpa": {
        "label": "CPA firm owners",
        "who": "your staff accountants",
        "hook": "You spend all year helping clients structure benefits. This one is for your own firm.",
    },
    "financial_advisor": {
        "label": "independent advisors",
        "who": "your associates and support staff",
        "hook": "You plan for your clients' risks. Your own practice's health coverage deserves the same plan.",
    },
    "real_estate": {
        "label": "brokers and agents",
        "who": "your team",
        "hook": "As a broker-owner or top producer, nobody hands you a benefits package. You have to build it.",
    },
    "dental_practice": {
        "label": "practice owners",
        "who": "your hygienists and front office",
        "hook": "Hygienists and assistants are in short supply, and benefits are part of how you keep them.",
    },
    "law_firm": {
        "label": "firm owners",
        "who": "your associates and paralegals",
        "hook": "Competing with big firms for talent starts with benefits that look like theirs.",
    },
}
DEFAULT_HOOK = {"label": "business owners", "who": "your team",
                "hook": "Benefits are one of the biggest decisions a small business makes each year."}


@dataclass
class Email:
    step: int
    send_day: int  # days after step 1
    subject: str
    preview: str
    body_html: str


def _pp(pain_points: list[dict], theme: str) -> dict:
    for p in pain_points:
        if p.get("theme") == theme:
            return p
    return {"headline": "", "detail": "", "employer_angle": "", "employee_angle": ""}


def footer(s: Settings) -> str:
    return (
        '<hr><p style="font-size:12px;color:#666">'
        f"This is an advertisement for health insurance from {html.escape(s.agency_name)}. "
        + (f"{html.escape(s.agent_license_line)}. " if s.agent_license_line else "") +
        "Plan benefits shown are in-network summaries for the 2026 plan year and are subject to change. "
        "The Schedule of Benefits and plan documents govern. Availability and rates vary and are subject to "
        "eligibility and carrier approval. Not affiliated with or endorsed by any government agency. "
        + (f"{html.escape(s.carrier_disclaimer)}" if s.carrier_disclaimer else "") + "<br>"
        f"{html.escape(s.agency_address)}<br>"
        "You are receiving this because your business contact information is publicly listed. "
        '<a href="*|UNSUB|*">Unsubscribe</a> and you will not hear from us again.</p>'
    )


def _wrap(blocks: list[str], s: Settings) -> str:
    body = "".join(b if b.startswith("<table") else f"<p>{b}</p>" for b in blocks)
    return f'<div style="font-family:Arial,sans-serif;font-size:15px;line-height:1.5">{body}{footer(s)}</div>'


def plan_table(plans: dict, include_premiums: bool) -> str:
    cols = ["Plan", "Deductible (ind/fam)", "Max out of pocket", "Primary care", "Specialist", "Rx (generic/brand/NP)"]
    if include_premiums:
        cols.append("Employee only / mo")
    th = "".join(f'<th style="border:1px solid #ccc;padding:4px">{c}</th>' for c in cols)
    rows = []
    for p in plans["plans"]:
        cells = [p["name"], p["deductible"], p["max_oop"], p["primary_care"], p["specialist"], p["rx"]]
        if include_premiums:
            cells.append(f"${p['premiums']['employee']:,}")
        rows.append("<tr>" + "".join(f'<td style="border:1px solid #ccc;padding:4px">{html.escape(c)}</td>' for c in cells) + "</tr>")
    return f'<table style="border-collapse:collapse;font-size:13px"><tr>{th}</tr>{"".join(rows)}</table>'


def build_sequence(niche: str, pain_points: list[dict], s: Settings, plans: dict | None = None) -> list[Email]:
    plans = plans or load_plans()
    c = plans["common"]
    by_name = {p["name"]: p for p in plans["plans"]}
    n_plans = len(plans["plans"])
    cheapest = min(plans["plans"], key=lambda p: p["premiums"]["employee"])
    h = NICHE_HOOKS.get(niche, DEFAULT_HOOK)
    cliff = _pp(pain_points, "subsidy_cliff")
    spike = _pp(pain_points, "premium_spike")
    tax = _pp(pain_points, "tax_strategy")
    alt = _pp(pain_points, "ichra_alternatives")
    deadline = _pp(pain_points, "open_enrollment_deadline")
    brochure = f'<a href="{s.brochure_url}">See the plan flyer</a>'
    book = f'<a href="{s.booking_url}">Grab a time on my calendar</a>'
    sign = f"{html.escape(s.from_name.split('|')[0].strip())}<br>{html.escape(s.agency_name)}"
    price_line = (f" Employee-only coverage starts at ${cheapest['premiums']['employee']:,}/month on the {cheapest['name']} plan."
                  if s.include_premiums else "")

    return [
        Email(1, 0,
              f"Health coverage got pricier in 2026. An option for {h['label']}",
              f"{n_plans} {plans['network']} plans, $0 preventive care and $0 teledoctor visits.",
              _wrap([
                  "Hi *|FNAME|*,",
                  h["hook"],
                  f"{cliff['detail']} {spike['detail']}".strip(),
                  f"Ameristead Health offers {n_plans} plans on the {plans['network']} network, from a "
                  f"{by_name['Platinum']['deductible'].split('/')[0]} deductible Platinum plan and a "
                  f"{by_name['Diamond']['deductible'].split('/')[0]} deductible Diamond plan to two HSA-qualified options. "
                  f"Every plan includes {c['preventive_care']} preventive care and {c['teledoctor']} teledoctor visits.{price_line}",
                  f"{brochure}. If it looks useful, reply and I will price it for *|BIZ|*.",
                  sign,
              ], s)),
        Email(2, 3,
              "The owner's side: deductible, recruitable, flexible",
              "Why these plans work for the business, not just the staff.",
              _wrap([
                  "Hi *|FNAME|*,",
                  "Quick follow-up on the business side.",
                  f"<b>Tax:</b> {tax['employer_angle']}",
                  f"<b>Recruiting:</b> a {plans['network']} plan with no referrals needed is a real edge when you compete for {h['who']}.",
                  f"<b>Flexibility:</b> {alt['detail']} With {n_plans} tiers, you can pick a rich plan for yourself and "
                  "a budget option for the team, or pair an HSA plan with a tax-advantaged savings account.",
                  "Here is how the tiers compare in-network:",
                  plan_table(plans, s.include_premiums),
                  f"{book} and I will run the numbers for *|BIZ|*.",
                  sign,
              ], s)),
        Email(3, 7,
              f"What {h['who'].replace('your ', '')} actually get",
              "The employee side of the same plans.",
              _wrap([
                  "Hi *|FNAME|*,",
                  f"The other half of the picture is what {h['who']} experience day to day.",
                  f"<b>See any specialist without a referral</b> on the {plans['network']} network.",
                  f"<b>{c['preventive_care']} preventive care and {c['teledoctor']} teledoctor</b> on every plan.",
                  f"<b>Predictable copays:</b> on the Gold plan, primary care is {by_name['Gold']['primary_care']}, "
                  f"specialists are {by_name['Gold']['specialist']} and generic prescriptions are "
                  f"{by_name['Gold']['rx'].split('/')[0]}.",
                  f"<b>GLP-1 path:</b> {c['glp1_note']}.",
                  f"<b>Take-home pay:</b> {tax['employee_angle']}",
                  f"{brochure} to share with your team.",
                  sign,
              ], s)),
        Email(4, 12,
              deadline["headline"] or "Before the new plan year",
              "Last note from me on this.",
              _wrap([
                  "Hi *|FNAME|*,",
                  f"{deadline['detail']} {deadline['employer_angle']}".strip(),
                  "If health coverage for you or your team is on the list this year, I would be glad to compare your "
                  f"current plan with the {plans['network']} options. If not, no worries, this is my last email on it.",
                  book,
                  sign,
              ], s)),
    ]


def unfilled_tokens(text: str) -> list[str]:
    return sorted(set(re.findall(r"\[[A-Z][^\]]*\]", text)))


# ---- cold email export ----------------------------------------------------
# Instantly variables. Its CSV import maps the "First Name" and "Company Name" columns
# to {{firstName}} and {{companyName}}. Change these for another cold email tool.
COLD_TOKENS = {
    "*|FNAME|*": "{{firstName}}",
    "*|BIZ|*": "{{companyName}}",
}
COLD_OPT_OUT = "Not interested? Reply \"unsubscribe\" and you will not hear from me again."


def to_plain_text(body_html: str) -> str:
    text = body_html.replace('<a href="*|UNSUB|*">Unsubscribe</a> and you will not hear from us again.', COLD_OPT_OUT)
    text = re.sub(r'<a href="([^"]+)">([^<]+)</a>', r"\2: \1", text)
    text = re.sub(r"</tr>", "\n", text)
    text = re.sub(r"</t[dh]>", " | ", text)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</p>|<hr>", "\n\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    for mc, cold in COLD_TOKENS.items():
        text = text.replace(mc, cold)
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+\n", "\n", text)).strip()


def cold_sequence(niche: str, pain_points: list[dict], s: Settings, plans: dict | None = None) -> list[dict]:
    """Plain-text steps for a cold tool. The plan comparison table is dropped (plain text
    tables read poorly and heavy formatting hurts cold deliverability)."""
    out = []
    for e in build_sequence(niche, pain_points, s, plans):
        body = re.sub(r"<p>Here is how the tiers compare in-network:</p><table.*?</table>", "", e.body_html, flags=re.S)
        subject = e.subject
        for mc, cold in COLD_TOKENS.items():
            subject = subject.replace(mc, cold)
        out.append({"step": e.step, "send_day": e.send_day, "subject": subject, "body": to_plain_text(body)})
    return out
