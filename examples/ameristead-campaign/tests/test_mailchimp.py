import pytest

from campaign.copy import Email
from campaign.mailchimp_client import MailchimpClient, SendBlocked
from campaign.prospect_scraper import Prospect


class Resp:
    def __init__(self, body, code=200): self.body, self.status_code, self.content, self.text = body, code, b"x", ""
    def json(self): return self.body


class FakeSession:
    def __init__(self): self.calls = []; self.auth = None
    def request(self, method, url, **kw):
        self.calls.append((method, url, kw))
        if url.endswith("/merge-fields"): return Resp({"merge_fields": []})
        if method == "GET" and url.endswith("/segments"): return Resp({"segments": []})
        if url.endswith("/segments"): return Resp({"id": 77})
        if url.endswith("/campaigns"): return Resp({"id": "c1"})
        return Resp({})


def mc():
    return MailchimpClient("key-us21", "L1", session=FakeSession())


def test_send_and_schedule_are_blocked():
    c = mc()
    for path in ("/campaigns/c1/actions/send", "/campaigns/c1/actions/schedule"):
        with pytest.raises(SendBlocked):
            c._request("POST", path)


def test_upload_requires_permission_confirmation():
    p = Prospect("a@b.com", "A", "B", "Biz", "cpa", "X", "TX", "", "", "u")
    with pytest.raises(PermissionError):
        mc().upload_members([p])
    c = mc(); c.upload_members([p], confirm_permission=True)
    put = [k for m, u, k in c.session.calls if m == "PUT"][0]
    assert put["json"]["status_if_new"] == "subscribed" and "status" not in put["json"]


def test_draft_creation_never_sends():
    c = mc()
    seg = c.upsert_niche_segment("cpa", ["a@b.com"])
    cid = c.create_draft(seg, "cpa", Email(1, 0, "S", "P", "<p>x</p>"), "From", "r@x.com")
    assert seg == 77 and cid == "c1"
    assert c.base == "https://us21.api.mailchimp.com/3.0"
    assert not any("/actions/" in u for _, u, _ in c.session.calls)
