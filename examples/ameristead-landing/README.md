# Lead funnel landing page (Cigna PPO for business owners)

A rebuild of the James Insurance Advisory funnel as a single conversion page. It's a static
site with one serverless function. Nothing in it is live until you deploy it, and it doesn't
touch the current domain.

## What's on the page

- **Hero with a live plan card.** Visitors slide through all seven plans (HSA 9000 to
  Diamond) and see the deductible, copays, Rx and out-of-pocket max change.
- **Email pop-up offering a free guide** ("The 2026 Cigna PPO plan comparison for
  business owners", `public/guide.html`, printable to PDF). It appears only after 12 seconds
  *and* 35% scroll, or on exit intent on desktop. It never shows on load, waits 7 days after a
  close, and stops once someone signs up or requests a quote. On phones it opens as a bottom
  sheet. Change the offer and timing in `public/config.js` → `incentive`.
- **Two-step quote form**: business type, team size and state, then name, email and
  optional phone. It has a separate, unchecked one-to-one TCPA call/text consent box and a
  separate email opt-in box. A sticky "Get my free quote" bar shows on phones.
- Pain-point section, tabs by niche (med spa, CPA, advisor, real estate, self-employed),
  owner vs. team benefits, the full comparison table, FAQ, and a footer with the license,
  address and disclaimer.

All plan numbers come from `public/plans.js`, which is generated from
`../ameristead-campaign/data/plans.json` (the rate flyer and the 2026 SBCs). A test fails if
the two ever drift apart. Premiums stay hidden unless `showPremiums: true`.

## Where submissions go

| Form | Mailchimp | `LEAD_WEBHOOK_URL` |
|---|---|---|
| Guide pop-up (an explicit email signup) | Yes, tagged `lead-magnet-guide` | Yes, if set |
| Quote, email box checked | Yes, tagged `quote-request`, `biz-…`, `size-…`, `state-…` | Yes |
| Quote, email box unchecked | **No** | Yes |

- Mailchimp uses `PUT …/members/{hash}` with `status_if_new: "pending"`, so new people
  get Mailchimp's confirmation email (double opt-in). Anyone who unsubscribed is never
  re-subscribed. Set `MAILCHIMP_DOUBLE_OPT_IN=false` for single opt-in.
- The webhook receives the full lead plus the consent record: the exact consent wording
  shown, the time, the IP and the user agent. Point it at Zapier, Make, your CRM or a Google
  Sheet so you get notified of quote requests.
- If neither destination is configured, the form returns an error instead of silently
  losing the lead.
- The API key is read only from server env vars. Tests check that no public file holds a
  key or calls Mailchimp directly.

## Run it

```bash
cd examples/ameristead-landing
npm test                      # 10 tests, no dependencies
LEAD_WEBHOOK_URL=... node server.js   # http://localhost:8080
```

For a static preview with no backend, set `demoMode: true` in `public/config.js`.

## Deploy (when you're ready)

On Vercel: import the repo, set the root directory to `examples/ameristead-landing`, and add
the variables from `.env.example` under Settings → Environment Variables. `public/` is served
as the site and `api/subscribe.js` becomes `/api/subscribe`.

## Before going live

Fill in the `[BRACKETED]` values in `public/config.js`: legal name, advisor name, mailing
address (CAN-SPAM requires it), licensed states and numbers, phone, booking link and logo.
Have counsel review `privacy.html`, `terms.html` and the TCPA wording. Confirm with
Ameristead/Cigna that the plan descriptions and use of the Cigna name are approved. Also
confirm that "plans for a team of one to 99" matches eligibility.
