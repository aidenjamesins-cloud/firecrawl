from campaign.compliance import ClearedListProvider, CsvListProvider, ComplianceFilter, HttpScrubProvider, ScrubResult, ScrubProvider
from campaign.prospect_scraper import Prospect


def P(email="owner@spa.com", phone="5125550100", state="TX"):
    return Prospect(email, "Ana", "Lee", "Glow Spa", "med_spa", "Austin", state, phone, "", "https://spa.com")


class Fixed(ScrubProvider):
    name = "fixed"
    def __init__(self, dnc, lit): self.r = ScrubResult(dnc, lit, "fixed")
    def check(self, phone, email): return self.r


def F(providers, **kw):
    return ComplianceFilter(providers, kw.get("suppression", set()), kw.get("states", ["TX"]), kw.get("require_phone", True))


def test_clear_prospect_is_kept():
    assert F([Fixed(False, False)]).reason_to_exclude(P()) is None


def test_dnc_hit_excluded():
    assert "DNC" in F([Fixed(True, False)]).reason_to_exclude(P())


def test_litigator_hit_excluded():
    assert "litigator" in F([Fixed(False, True)]).reason_to_exclude(P())


def test_unknown_status_excluded():
    assert F([Fixed(None, False)]).reason_to_exclude(P()) == "DNC status unknown"
    assert F([Fixed(False, None)]).reason_to_exclude(P()) == "litigator status unknown"


def test_no_providers_excludes_everyone():
    assert "no DNC/litigator" in F([]).reason_to_exclude(P())


def test_no_phone_excluded_by_default():
    assert F([Fixed(False, False)]).reason_to_exclude(P(phone="")) == "no phone to check against DNC"
    assert F([Fixed(None, False)], require_phone=False).reason_to_exclude(P(phone="")) is None


def test_suppression_and_domain_suppression():
    assert F([Fixed(False, False)], suppression={"owner@spa.com"}).reason_to_exclude(P()) == "suppression list"
    assert F([Fixed(False, False)], suppression={"@spa.com"}).reason_to_exclude(P()) == "suppression list"


def test_unlicensed_state_excluded():
    assert "not licensed" in F([Fixed(False, False)]).reason_to_exclude(P(state="CA"))
    assert F([Fixed(False, False)], states=[]).reason_to_exclude(P(state="CA")) is None


def test_csv_provider(tmp_path):
    dnc = tmp_path / "dnc.csv"; dnc.write_text("(512) 555-0100\n")
    lit = tmp_path / "lit.csv"; lit.write_text("sue@law.com\n")
    prov = CsvListProvider(str(dnc), str(lit))
    assert prov.check("5125550100", "a@b.com").dnc is True
    r = prov.check("5125550199", "a@b.com"); assert (r.dnc, r.litigator) == (False, False)
    assert prov.check("5125550199", "SUE@law.com").litigator is True
    # missing litigator list -> unknown, which the filter excludes
    assert CsvListProvider(str(dnc), "").check("5125550199", "a@b.com").litigator is None


def test_http_provider_error_is_unknown():
    class Boom:
        def post(self, *a, **k): raise ConnectionError("down")
    r = HttpScrubProvider("https://x", "k", session=Boom()).check("5125550100", "a@b.com")
    assert (r.dnc, r.litigator) == (None, None)


def test_external_cleared_list(tmp_path):
    cleared = tmp_path / "cleared.csv"; cleared.write_text("email,phone\nowner@spa.com,5125550100\n")
    f = F([ClearedListProvider(str(cleared))])
    assert f.reason_to_exclude(P()) is None
    assert f.reason_to_exclude(P(email="other@spa.com", phone="5125550199")) == "DNC status unknown"


def test_external_scrub_mode_skips_dnc_but_keeps_other_checks():
    f = ComplianceFilter([], set(), ["TX"], True, external_scrub=True)
    assert f.reason_to_exclude(P(phone="")) is None
    assert "not licensed" in f.reason_to_exclude(P(state="CA"))
    f2 = ComplianceFilter([], {"owner@spa.com"}, ["TX"], True, external_scrub=True)
    assert f2.reason_to_exclude(P()) == "suppression list"
