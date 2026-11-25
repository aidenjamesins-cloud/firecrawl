import csv
import json

from campaign import cli
from campaign.config import Settings
from campaign.copy import cold_sequence


def test_cold_sequence_is_plain_text_with_opt_out():
    pains = json.load(open("data/seed_pain_points.json"))
    steps = cold_sequence("cpa", pains, Settings())
    assert len(steps) == 4
    for st in steps:
        assert "<" not in st["body"] and "*|" not in st["body"]
        assert 'Reply "unsubscribe"' in st["body"]
        assert "advertisement" in st["body"]
    assert "{{firstName}}" in steps[0]["body"] and "{{companyName}}" in steps[0]["body"]


def _write_prospects(path):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["email", "first_name", "last_name", "business_name", "niche", "city", "state", "phone", "employee_estimate", "source_url"])
        w.writerow(["ok@cpa.com", "A", "B", "OK CPA", "cpa", "Austin", "TX", "5125550100", "", "https://cpa.com"])
        w.writerow(["dnc@cpa.com", "C", "D", "DNC CPA", "cpa", "Austin", "TX", "5125550111", "", "https://dnc.com"])


def test_export_cold_reruns_compliance_filter(tmp_path, monkeypatch):
    dnc = tmp_path / "dnc.csv"; dnc.write_text("5125550111\n")
    lit = tmp_path / "lit.csv"; lit.write_text("sue@law.com\n")
    inp = tmp_path / "p.csv"; _write_prospects(inp)
    for k, v in {"DNC_CSV_PATH": str(dnc), "LITIGATOR_CSV_PATH": str(lit), "LICENSED_STATES": "TX",
                 "SUPPRESSION_CSV_PATH": str(tmp_path / "sup.csv")}.items():
        monkeypatch.setenv(k, v)
    rc = cli.main(["export-cold", "--in", str(inp), "--niche", "cpa", "--out-dir", str(tmp_path), "--allow-placeholders"])
    assert rc == 0
    rows = list(csv.DictReader(open(tmp_path / "cold_leads_cpa.csv")))
    assert [r["Email"] for r in rows] == ["ok@cpa.com"]
    assert len(list(csv.DictReader(open(tmp_path / "cold_sequence_cpa.csv")))) == 4


def test_export_cold_blocks_placeholders(tmp_path):
    inp = tmp_path / "p.csv"; _write_prospects(inp)
    assert cli.main(["export-cold", "--in", str(inp), "--niche", "cpa", "--out-dir", str(tmp_path)]) == 2


def test_sync_suppression_from_cold_tool_csv(tmp_path, monkeypatch):
    sup = tmp_path / "sup.csv"
    monkeypatch.setenv("SUPPRESSION_CSV_PATH", str(sup))
    src = tmp_path / "unsubs.csv"; src.write_text("email,date\nGone@x.com,2026-11-25\n")
    assert cli.main(["sync-suppression", "--from-csv", str(src), "--skip-mailchimp"]) == 0
    assert "gone@x.com" in sup.read_text()


def test_draft_requires_engaged_confirmation(tmp_path):
    inp = tmp_path / "p.csv"; _write_prospects(inp)
    assert cli.main(["draft", "--in", str(inp), "--niche", "cpa", "--confirm-permission"]) == 2
