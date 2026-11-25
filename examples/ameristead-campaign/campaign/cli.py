"""Command line entry point.

  python -m campaign.cli trends    --out data/pain_points.json
  python -m campaign.cli scrape    --niche med_spa --locations "Austin,TX;Dallas,TX" --out data/prospects_med_spa.csv
  python -m campaign.cli filter    --in data/prospects_med_spa.csv --out data/clean_med_spa.csv
  python -m campaign.cli preview   --niche med_spa
  python -m campaign.cli export-cold --in data/clean_med_spa.csv --niche med_spa
  python -m campaign.cli sync-suppression [--from-csv cold_tool_unsubscribes.csv]
  python -m campaign.cli draft     --in data/engaged_med_spa.csv --niche med_spa --engaged-only-confirmed --confirm-permission

First touches go out from a cold email tool (export-cold). Only people who reply or
opt in are moved to Mailchimp (draft), so Mailchimp never receives scraped contacts.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

from . import trend_agent
from .compliance import ComplianceFilter, add_to_suppression
from .config import Settings
from .copy import build_sequence, cold_sequence, unfilled_tokens
from .firecrawl_client import FirecrawlClient
from .prospect_scraper import NICHES, read_csv, scrape_niche, write_csv

SEED = os.path.join("data", "seed_pain_points.json")


def _pain_points(path: str | None) -> list[dict]:
    for p in (path, os.path.join("data", "pain_points.json"), SEED):
        if p and os.path.exists(p):
            with open(p) as fh:
                return json.load(fh)
    return []


def _leftovers(s: Settings, texts: list[str]) -> list[str]:
    return sorted({t for x in texts for t in unfilled_tokens(x)} | set(s.unfilled_placeholders()))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="campaign")
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("trends"); t.add_argument("--out", default="data/pain_points.json"); t.add_argument("--months", type=int, default=3)
    sc = sub.add_parser("scrape"); sc.add_argument("--niche", choices=sorted(NICHES), required=True)
    sc.add_argument("--locations", required=True, help='"City,ST;City,ST"'); sc.add_argument("--out", required=True)
    sc.add_argument("--per-query", type=int, default=10)
    f = sub.add_parser("filter"); f.add_argument("--in", dest="inp", required=True); f.add_argument("--out", required=True)
    f.add_argument("--excluded-out", default="data/excluded.csv")
    pv = sub.add_parser("preview"); pv.add_argument("--niche", required=True); pv.add_argument("--pain-points")
    ss = sub.add_parser("sync-suppression")
    ss.add_argument("--from-csv", help="unsubscribes/bounces exported from the cold email tool")
    ss.add_argument("--skip-mailchimp", action="store_true")
    ec = sub.add_parser("export-cold"); ec.add_argument("--in", dest="inp", required=True)
    ec.add_argument("--niche", required=True); ec.add_argument("--pain-points"); ec.add_argument("--out-dir", default="out")
    ec.add_argument("--allow-placeholders", action="store_true")
    d = sub.add_parser("draft"); d.add_argument("--in", dest="inp", required=True); d.add_argument("--niche", required=True)
    d.add_argument("--pain-points"); d.add_argument("--confirm-permission", action="store_true")
    d.add_argument("--allow-placeholders", action="store_true")
    d.add_argument("--engaged-only-confirmed", action="store_true",
                   help="confirm --in lists only people who replied or opted in")
    a = ap.parse_args(argv)
    s = Settings.from_env()

    if a.cmd == "trends":
        points = trend_agent.run(FirecrawlClient(s.firecrawl_api_key), months=a.months)
        trend_agent.save(points, a.out)
        for p in points:
            print(f"{p.score:>3}  {p.theme}")
        print(f"Wrote {a.out}. Review the evidence URLs before using any claim in copy.")
        return 0

    if a.cmd == "scrape":
        locs = [tuple(x.strip() for x in loc.split(",")) for loc in a.locations.split(";") if loc.strip()]
        rows = scrape_niche(FirecrawlClient(s.firecrawl_api_key), a.niche, locs, per_query=a.per_query)
        write_csv(rows, a.out)
        print(f"Wrote {len(rows)} prospects to {a.out}. Run `filter` before any upload.")
        return 0

    if a.cmd == "filter":
        report = ComplianceFilter.from_settings(s).run(read_csv(a.inp))
        write_csv(report.kept, a.out)
        with open(a.excluded_out, "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["email", "business_name", "reason"])
            for p, why in report.excluded:
                w.writerow([p.email, p.business_name, why])
        print(f"Kept {len(report.kept)}, excluded {len(report.excluded)} (reasons in {a.excluded_out}).")
        return 0

    if a.cmd == "preview":
        os.makedirs("out", exist_ok=True)
        for e in build_sequence(a.niche, _pain_points(a.pain_points), s):
            path = f"out/{a.niche}_step{e.step}.html"
            with open(path, "w") as fh:
                fh.write(f"<h3>Subject: {e.subject}</h3><p><i>{e.preview}</i></p>{e.body_html}")
            print(f"{path}  (day +{e.send_day})  placeholders: {unfilled_tokens(e.body_html) or 'none'}")
        return 0

    if a.cmd == "export-cold":
        steps = cold_sequence(a.niche, _pain_points(a.pain_points), s)
        leftovers = _leftovers(s, [st["subject"] + st["body"] for st in steps])
        if leftovers and not a.allow_placeholders:
            print("Fill these before exporting (or pass --allow-placeholders for a test export):")
            print("  " + "\n  ".join(leftovers))
            return 2
        # Re-run the compliance filter so a stale or hand-edited CSV can't bypass it.
        report = ComplianceFilter.from_settings(s).run(read_csv(a.inp))
        leads = [p for p in report.kept if p.niche == a.niche]
        os.makedirs(a.out_dir, exist_ok=True)
        leads_path = os.path.join(a.out_dir, f"cold_leads_{a.niche}.csv")
        with open(leads_path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["email", "first_name", "last_name", "company_name", "niche", "city", "state", "website"])
            for p in leads:
                w.writerow([p.email, p.first_name, p.last_name, p.business_name, p.niche, p.city, p.state, p.source_url])
        seq_csv = os.path.join(a.out_dir, f"cold_sequence_{a.niche}.csv")
        with open(seq_csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["step", "send_day", "subject", "body"])
            w.writeheader(); w.writerows(steps)
        seq_txt = os.path.join(a.out_dir, f"cold_sequence_{a.niche}.txt")
        with open(seq_txt, "w") as fh:
            for st in steps:
                fh.write(f"=== Step {st['step']} (day +{st['send_day']})\nSubject: {st['subject']}\n\n{st['body']}\n\n")
        print(f"{len(leads)} cleared leads -> {leads_path} (excluded {len(report.excluded)})")
        print(f"Sequence -> {seq_csv} and {seq_txt}. Import both into your cold email tool; nothing was sent.")
        return 0

    if a.cmd == "sync-suppression":
        path = s.suppression_csv_path or "data/suppression.csv"
        emails: list[str] = []
        if a.from_csv:
            with open(a.from_csv, newline="") as fh:
                emails += [c.strip().lower() for row in csv.reader(fh) for c in row if "@" in c]
        if not a.skip_mailchimp:
            from .mailchimp_client import MailchimpClient
            emails += MailchimpClient(s.mailchimp_api_key, s.mailchimp_audience_id, server_prefix=s.mailchimp_server_prefix).unsubscribed_emails()
        add_to_suppression(path, emails)
        print(f"Merged {len(emails)} opt-out addresses into {path}.")
        return 0

    if a.cmd == "draft" and not a.engaged_only_confirmed:
        print("Mailchimp is only for people who replied or opted in. Pass --engaged-only-confirmed "
              "once --in lists only those people (not the scraped list).")
        return 2

    from .mailchimp_client import MailchimpClient
    mc = MailchimpClient(s.mailchimp_api_key, s.mailchimp_audience_id, server_prefix=s.mailchimp_server_prefix)

    if a.cmd == "draft":
        seq = build_sequence(a.niche, _pain_points(a.pain_points), s)
        leftovers = _leftovers(s, [e.subject + e.body_html for e in seq])
        if leftovers and not a.allow_placeholders:
            print("Fill these before creating drafts (or pass --allow-placeholders for a test draft):")
            print("  " + "\n  ".join(leftovers))
            return 2
        # Re-run the compliance filter here so a stale or hand-edited CSV can't bypass it.
        report = ComplianceFilter.from_settings(s).run(read_csv(a.inp))
        prospects = [p for p in report.kept if p.niche == a.niche]
        if not prospects:
            print("No prospects passed the compliance filter; nothing uploaded.")
            return 1
        mc.upload_members(prospects, confirm_permission=a.confirm_permission)
        seg = mc.upsert_niche_segment(a.niche, [p.email for p in prospects])
        ids = [mc.create_draft(seg, a.niche, e, s.from_name, s.reply_to) for e in seq]
        print(f"Uploaded {len(prospects)} contacts to segment {seg}. Created {len(ids)} DRAFT campaigns: {', '.join(ids)}")
        print("Nothing was sent. Review in Mailchimp > Campaigns and send each step on its day after approval.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
