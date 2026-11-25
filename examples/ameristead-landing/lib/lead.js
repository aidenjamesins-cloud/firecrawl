// Validates a form submission and routes it:
//  - Mailchimp: only people who opted in to email (the guide pop-up, or the quote form's email box).
//  - LEAD_WEBHOOK_URL: every quote request, with the consent record (Zapier, Make, a CRM, a Google Sheet...).
// Secrets come only from the environment. Nothing here is sent to the browser.
import { createHash } from "node:crypto";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const MAX = 200;
const clean = (v) => (typeof v === "string" ? v.trim().slice(0, MAX) : "");
const slug = (v) => clean(v).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export function validate(body) {
  if (!body || typeof body !== "object") return { error: "Send the form as JSON." };
  if (clean(body.company_website)) return { spam: true };
  const source = body.source === "quote" ? "quote" : body.source === "guide" ? "guide" : null;
  if (!source) return { error: "Unknown form." };
  const lead = {
    source,
    firstName: clean(body.firstName),
    lastName: clean(body.lastName),
    email: clean(body.email).toLowerCase(),
    phone: clean(body.phone),
    businessType: clean(body.businessType),
    employees: clean(body.employees),
    state: clean(body.state).toUpperCase().slice(0, 2),
    emailOptIn: body.emailOptIn === true,
    emailOptInText: clean(body.emailOptInText ? String(body.emailOptInText) : "").slice(0, MAX),
    smsConsent: body.smsConsent === true,
    smsConsentText: typeof body.smsConsentText === "string" ? body.smsConsentText.trim().slice(0, 1000) : "",
    page: clean(body.page),
  };
  if (!EMAIL_RE.test(lead.email)) return { error: "Enter a valid email address." };
  if (!lead.firstName) return { error: "Enter your first name." };
  if (source === "guide") lead.emailOptIn = true; // the pop-up is an explicit email signup
  if (source === "quote") {
    if (!lead.lastName) return { error: "Enter your last name." };
    if (!lead.businessType || !lead.employees || !lead.state) return { error: "Answer the business questions." };
    const digits = lead.phone.replace(/\D/g, "");
    if (lead.phone && (digits.length < 10 || digits.length > 11)) return { error: "Enter a 10-digit phone number." };
    if (lead.smsConsent && !digits) return { error: "Add a phone number for calls and texts, or uncheck that box." };
    if (lead.smsConsent && !lead.smsConsentText) return { error: "Consent wording is missing." };
  }
  return { lead };
}

export function mailchimpTags(lead) {
  const tags = ["website", lead.source === "guide" ? "lead-magnet-guide" : "quote-request"];
  if (lead.businessType) tags.push("biz-" + slug(lead.businessType));
  if (lead.employees) tags.push("size-" + slug(lead.employees));
  if (lead.state) tags.push("state-" + lead.state.toLowerCase());
  return tags;
}

export async function addToMailchimp(lead, env, fetchImpl = fetch) {
  const key = env.MAILCHIMP_API_KEY, list = env.MAILCHIMP_AUDIENCE_ID, dc = env.MAILCHIMP_SERVER_PREFIX;
  if (!key || !list || !dc) return { skipped: "mailchimp-not-configured" };
  if (!/^[a-z]{2}\d{1,3}$/.test(dc)) throw new Error("MAILCHIMP_SERVER_PREFIX looks wrong (expected something like us6).");
  const hash = createHash("md5").update(lead.email).digest("hex");
  const base = `https://${dc}.api.mailchimp.com/3.0/lists/${encodeURIComponent(list)}/members/${hash}`;
  const headers = { Authorization: "Basic " + Buffer.from("site:" + key).toString("base64"), "Content-Type": "application/json" };
  const doubleOptIn = env.MAILCHIMP_DOUBLE_OPT_IN !== "false";
  // PUT with status_if_new: creates new people, and never re-subscribes someone who unsubscribed.
  const res = await fetchImpl(base, {
    method: "PUT", headers,
    body: JSON.stringify({
      email_address: lead.email,
      status_if_new: doubleOptIn ? "pending" : "subscribed",
      merge_fields: { FNAME: lead.firstName, LNAME: lead.lastName },
    }),
  });
  if (!res.ok) {
    const j = await res.json().catch(() => ({}));
    // A permanently deleted or compliance-blocked address: respect it, don't fail the form.
    if (res.status === 400 && /forgotten|compliance|permanently/i.test(j.title + " " + j.detail)) return { skipped: "mailchimp-blocked" };
    throw new Error(`Mailchimp ${res.status}: ${j.title || "error"}`);
  }
  const tr = await fetchImpl(base + "/tags", {
    method: "POST", headers,
    body: JSON.stringify({ tags: mailchimpTags(lead).map((name) => ({ name, status: "active" })) }),
  });
  if (!tr.ok) throw new Error(`Mailchimp tags ${tr.status}`);
  return { mailchimp: doubleOptIn ? "pending" : "subscribed" };
}

export async function sendLead(lead, meta, env, fetchImpl = fetch) {
  if (!env.LEAD_WEBHOOK_URL) return { skipped: "webhook-not-configured" };
  const res = await fetchImpl(env.LEAD_WEBHOOK_URL, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...lead, ...meta }),
  });
  if (!res.ok) throw new Error(`Lead webhook ${res.status}`);
  return { webhook: "sent" };
}

// Returns [status, json]. `meta` carries the consent evidence (time, IP, user agent).
export async function handleLead(body, meta, env, fetchImpl = fetch) {
  const v = validate(body);
  if (v.spam) return [200, { ok: true }];
  if (v.error) return [400, { ok: false, error: v.error }];
  const lead = v.lead;
  const mcReady = env.MAILCHIMP_API_KEY && env.MAILCHIMP_AUDIENCE_ID && env.MAILCHIMP_SERVER_PREFIX;
  const destinations = (lead.emailOptIn && mcReady ? 1 : 0) + (env.LEAD_WEBHOOK_URL ? 1 : 0);
  if (!destinations) {
    console.error("[lead] no destination configured; set Mailchimp env vars and/or LEAD_WEBHOOK_URL");
    return [503, { ok: false, error: "Our form is offline right now. Please call or email us instead." }];
  }
  const out = {};
  try {
    if (lead.emailOptIn) Object.assign(out, await addToMailchimp(lead, env, fetchImpl));
    Object.assign(out, await sendLead(lead, meta, env, fetchImpl));
  } catch (e) {
    console.error("[lead]", e.message);
    return [502, { ok: false, error: "We couldn't save that just now. Try again in a minute." }];
  }
  return [200, { ok: true }];
}
