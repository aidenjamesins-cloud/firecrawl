import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";

const read = (p) => readFileSync(new URL(p, import.meta.url), "utf8");

test("plan figures on the site match the campaign's plans.json exactly", () => {
  const site = read("../public/plans.js");
  const json = JSON.parse(site.slice(site.indexOf("=") + 1).trim().replace(/;$/, ""));
  assert.deepEqual(json, JSON.parse(read("../../ameristead-campaign/data/plans.json")));
});

test("no secrets or Mailchimp API calls in public files", () => {
  for (const f of readdirSync(new URL("../public/", import.meta.url))) {
    const s = read("../public/" + f);
    assert.doesNotMatch(s, /api\.mailchimp\.com|MAILCHIMP_API_KEY|[0-9a-f]{32}-us\d+/i, f);
  }
});

test("consent boxes start unchecked and premiums start hidden", () => {
  const html = read("../public/index.html");
  for (const m of html.matchAll(/<input type="checkbox"[^>]*>/g)) assert.doesNotMatch(m[0], /checked/);
  assert.match(read("../public/config.js"), /showPremiums: false/);
});
