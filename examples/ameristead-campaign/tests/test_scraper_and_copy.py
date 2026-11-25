from campaign.config import Settings
from campaign.copy import build_sequence, load_plans, unfilled_tokens
from campaign.prospect_scraper import is_blocked, normalize_phone, scrape_niche, to_prospect
from campaign.trend_agent import score_results


class FakeFC:
    def __init__(self, pages): self.pages = pages
    def search(self, q, limit=10, tbs=None, sources=None):
        return [{"url": u} for u in self.pages]
    def extract(self, url, schema, prompt): return self.pages[url]


def test_scrape_filters_blocked_generic_and_large():
    pages = {
        "https://glowspa.com/contact": {"business_name": "Glow", "business_email": "Ana@GlowSpa.com", "phone": "+1 512-555-0100"},
        "https://www.yelp.com/biz/x": {"business_name": "Y", "business_email": "y@y.com"},
        "https://big.com": {"business_name": "Big", "business_email": "hr@big.com", "employee_estimate": 400},
        "https://noreply.com": {"business_name": "N", "business_email": "noreply@n.com"},
        "https://guess.com": {"business_name": "G", "business_email": "not an email"},
    }
    out = scrape_niche(FakeFC(pages), "med_spa", [("Austin", "TX")])
    assert [p.email for p in out] == ["ana@glowspa.com"]
    assert out[0].phone == "5125550100" and out[0].state == "TX"


def test_helpers():
    assert is_blocked("https://www.linkedin.com/in/x") and not is_blocked("https://cpa-firm.com")
    assert normalize_phone("123") == ""
    assert to_prospect({"business_email": ""}, "cpa", "u", "c", "TX") is None


def test_trend_scoring_counts_distinct_sources():
    res = [{"url": "a", "title": "ACA subsidies expired", "description": ""},
           {"url": "b", "title": "premium tax credit cliff", "description": ""},
           {"url": "c", "title": "prior authorization denials rise", "description": ""}]
    pts = {p.theme: p.score for p in score_results(res)}
    assert pts["subsidy_cliff"] == 2 and pts["prior_auth"] == 1


def test_sequence_uses_plan_facts_and_compliance_footer():
    import json
    pains = json.load(open("data/seed_pain_points.json"))
    s = Settings()
    seq = build_sequence("cpa", pains, s)
    assert [e.send_day for e in seq] == [0, 3, 7, 12]
    allhtml = "".join(e.body_html for e in seq)
    plans = load_plans()
    assert "$250" in allhtml and "Cigna PPO" in allhtml and "$0 teledoctor" in allhtml
    for e in seq:
        assert "*|UNSUB|*" in e.body_html and "advertisement" in e.body_html
    assert "$426" not in allhtml  # premiums hidden by default
    s.include_premiums = True
    assert "$426" in "".join(e.body_html for e in build_sequence("cpa", pains, s))
    assert "[PHYSICAL MAILING ADDRESS]" in unfilled_tokens(allhtml)
    assert len(plans["plans"]) == 7
