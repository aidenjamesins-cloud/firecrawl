import { test } from "node:test";
import assert from "node:assert/strict";
import { handleLead, validate, mailchimpTags } from "../lib/lead.js";

const MC = { MAILCHIMP_API_KEY: "k-us6", MAILCHIMP_AUDIENCE_ID: "abc123", MAILCHIMP_SERVER_PREFIX: "us6" };
const quote = (o = {}) => ({ source: "quote", firstName: "Dana", lastName: "Lee", email: "Dana@Example.com", phone: "",
  businessType: "Med spa or aesthetics", employees: "2 to 9", state: "tx", emailOptIn: false, smsConsent: false, ...o });
const guide = (o = {}) => ({ source: "guide", firstName: "Dana", email: "dana@example.com", ...o });

function fakeFetch(status = 200, body = {}) {
  const calls = [];
  const fn = async (url, init) => { calls.push({ url, init, body: init.body ? JSON.parse(init.body) : null }); return { ok: status < 300, status, json: async () => body }; };
  fn.calls = calls; return fn;
}

test("guide signup goes to Mailchimp as pending (double opt-in) with tags", async () => {
  const f = fakeFetch();
  const [status, json] = await handleLead(guide(), {}, MC, f);
  assert.equal(status, 200); assert.equal(json.ok, true);
  assert.equal(f.calls.length, 2);
  assert.match(f.calls[0].url, /^https:\/\/us6\.api\.mailchimp\.com\/3\.0\/lists\/abc123\/members\/[a-f0-9]{32}$/);
  assert.equal(f.calls[0].init.method, "PUT");
  assert.equal(f.calls[0].body.status_if_new, "pending");
  assert.equal(f.calls[0].body.status, undefined, "never forces status, so unsubscribes stay unsubscribed");
  assert.deepEqual(f.calls[1].body.tags.map((t) => t.name), ["website", "lead-magnet-guide"]);
});

test("quote without email opt-in never reaches Mailchimp, goes to the webhook with consent record", async () => {
  const f = fakeFetch();
  const env = { ...MC, LEAD_WEBHOOK_URL: "https://hooks.example.com/x" };
  const [status] = await handleLead(quote({ phone: "(555) 123-4567", smsConsent: true, smsConsentText: "I agree..." }), { submittedAt: "t", ip: "1.2.3.4" }, env, f);
  assert.equal(status, 200);
  assert.equal(f.calls.length, 1);
  assert.equal(f.calls[0].url, "https://hooks.example.com/x");
  assert.equal(f.calls[0].body.smsConsentText, "I agree...");
  assert.equal(f.calls[0].body.ip, "1.2.3.4");
  assert.equal(f.calls[0].body.email, "dana@example.com");
});

test("quote with email opt-in is tagged by business, size and state", () => {
  const { lead } = validate(quote({ emailOptIn: true }));
  assert.deepEqual(mailchimpTags(lead), ["website", "quote-request", "biz-med-spa-or-aesthetics", "size-2-to-9", "state-tx"]);
});

test("nothing configured returns 503 instead of silently dropping the lead", async () => {
  const [status, json] = await handleLead(quote(), {}, {}, fakeFetch());
  assert.equal(status, 503); assert.equal(json.ok, false);
});

test("bad input is rejected with a fixable message", async () => {
  for (const [body, re] of [
    [guide({ email: "nope" }), /valid email/],
    [quote({ state: "" }), /business questions/],
    [quote({ phone: "123" }), /10-digit/],
    [quote({ smsConsent: true, smsConsentText: "x" }), /phone number/],
    [{ source: "other", email: "a@b.co", firstName: "A" }, /Unknown form/],
  ]) {
    const [status, json] = await handleLead(body, {}, MC, fakeFetch());
    assert.equal(status, 400); assert.match(json.error, re);
  }
});

test("honeypot submissions are accepted silently and sent nowhere", async () => {
  const f = fakeFetch();
  const [status] = await handleLead(guide({ company_website: "spam.biz" }), {}, MC, f);
  assert.equal(status, 200); assert.equal(f.calls.length, 0);
});

test("Mailchimp error surfaces as 502 and does not leak details", async () => {
  const [status, json] = await handleLead(guide(), {}, MC, fakeFetch(401, { title: "API Key Invalid" }));
  assert.equal(status, 502); assert.doesNotMatch(json.error, /API Key/);
});
