# Ameristead Cigna PPO campaign toolkit

Finds trending health insurance pain points, scrapes business owner prospects by niche
with Firecrawl, removes anyone who cannot be cleared for contact, and builds a 4-email
drip as **Mailchimp drafts**. Nothing is ever sent by this code.

```
trends ──► pain_points.json ─┐
scrape ──► prospects.csv ──► filter ──► clean.csv ──► export-cold ──► cold email tool (separate domain)
                                │                                          │
                                └──► excluded.csv                 replies / opt-ins only
                                                                           ▼
                                               engaged.csv ──► draft ──► Mailchimp drafts (a person sends)
```

Scraped prospects never go into Mailchimp. First touches go out from a cold outreach
tool on a separate sending domain. Only people who reply with interest or opt in are
exported from that tool into `engaged_<niche>.csv` and moved to Mailchimp.

## Setup

```bash
cd examples/ameristead-campaign
pip install -r requirements.txt
cp .env.example .env   # fill in keys and placeholders; .env is git-ignored
python -m pytest tests
```

## Commands

| Step | Command | What it does |
|---|---|---|
| 1 | `python -m campaign.cli trends` | Runs Firecrawl searches over the last 3 months, scores themes by how many sources mention them, writes `data/pain_points.json` with source URLs. Without it, the copy uses `data/seed_pain_points.json` (researched November 2026). |
| 2 | `python -m campaign.cli scrape --niche cpa --locations "Austin,TX;Houston,TX" --out data/prospects_cpa.csv` | Searches for businesses per niche and city, skips LinkedIn, Yelp, Zillow and other sites whose terms forbid scraping, and extracts only emails published on the business's own site. Niches: `med_spa`, `cpa`, `financial_advisor`, `real_estate`, `dental_practice`, `law_firm`. |
| 3 | `python -m campaign.cli filter --in data/prospects_cpa.csv --out data/clean_cpa.csv` | Compliance filter (below). |
| 4 | `python -m campaign.cli preview --niche cpa` | Writes the 4 emails to `out/` for review and lists any unfilled `[PLACEHOLDERS]`. |
| 5 | `python -m campaign.cli export-cold --in data/clean_cpa.csv --niche cpa` | Re-runs the filter and writes `out/cold_leads_cpa.csv` in Instantly's import format (Email, First Name, Last Name, Company Name, Website, plus niche/city/state custom variables) plus the 4-step plain-text sequence as CSV and TXT for your cold email tool. Uses Instantly's `{{firstName}}` and `{{companyName}}` variables (edit `COLD_TOKENS` in `copy.py` if your tool differs). Each email keeps the ad disclosure, physical address and a reply-to-unsubscribe line. Refuses while placeholders remain. Nothing is sent. |
| 6 | `python -m campaign.cli sync-suppression --from-csv unsubscribes.csv` | Merges opt-outs and bounces exported from the cold tool, plus Mailchimp unsubscribes, into the suppression list. Run before every export and upload (`--skip-mailchimp` if Mailchimp is not set up yet). |
| 7 | `python -m campaign.cli draft --in data/engaged_cpa.csv --niche cpa --engaged-only-confirmed --confirm-permission` | For repliers and opt-ins only. Re-runs the filter, uploads them, creates a niche segment and 4 draft campaigns titled with their send day (+0, +3, +7, +12). Refuses while placeholders remain. |

## Compliance filter (fails closed)

**`DNC_SCRUB=external` (James Insurance Advisory's setup):** your team runs the DNC and
litigator check on the exported file before importing it into Instantly. The export is
named `cold_leads_<niche>_NOT_SCRUBBED.csv` as a reminder. The suppression list and
licensed-state checks below still run. With `DNC_SCRUB=internal` the tool clears every
record itself, as described next.

A prospect is kept only if every check passes. Anything unknown is excluded.

* Not on the suppression list (exact email or a whole `@domain`).
* In a state listed in `LICENSED_STATES`.
* At least one scrub source is configured, and it returns a definite "clear" for **both**
  federal DNC and known TCPA litigator status. Sources are pluggable (`ScrubProvider`):
  * `ClearedListProvider` (`SCRUB_CLEARED_CSV_PATH`): for a scrub done outside this tool.
    Run the scraped prospects CSV through your DNC and litigator scrub, then save only the
    records that came back clear. Anyone not in that file is excluded.
  * `CsvListProvider`: your FTC DNC subscription download (phones) and a litigator list from your vendor (phones and/or emails).
  * `HttpScrubProvider`: any vendor API; adapt `parse()` to its response.
* Has a phone number to check against DNC (set `REQUIRE_PHONE_FOR_DNC_CHECK=false` to allow email-only records; they still need a litigator clear).

The DNC registry covers phone numbers. It does not apply to email by law, but this
campaign treats a DNC hit as do-not-contact on every channel, as requested.

## Plan facts

`data/plans.json` is transcribed from the Ameristead rate flyer and the 2026 Cigna SBCs
(HSA 9000, Bronze, HSA 6000, Silver, Gold, Platinum, Diamond; in-network figures).
Premiums from the flyer are only shown when `INCLUDE_PREMIUMS=true`.

## Before anything is sent

* **Mailchimp list policy.** Mailchimp's Acceptable Use Policy does not allow emailing
  scraped contacts who have not opted in. That is why first touches go through the cold
  tool, and `draft` requires both `--engaged-only-confirmed` and `--confirm-permission`.
* **Cold sending domain.** Use a separate domain from your main one, warm it up, and keep
  daily volume modest so your primary domain's reputation is protected.
* **CAN-SPAM.** Every email carries an ad disclosure, the physical address, a working
  unsubscribe link, and an honest subject line. Honor opt-outs within 10 business days
  (`sync-suppression` handles Mailchimp opt-outs).
* **Licensing and carrier rules.** Fill in the agent license line and states. Check whether
  Cigna or the plan administrator must approve marketing that uses their name.
* **Claims.** Pain point statistics carry source URLs in the JSON. Verify each before sending.
