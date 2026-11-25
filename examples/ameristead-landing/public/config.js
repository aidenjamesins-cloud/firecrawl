// Site settings. Edit these; nothing secret belongs here (this file is public).
// Values in [BRACKETS] are placeholders that still need Aiden's real details.
window.SITE_CONFIG = {
  agencyName: "James Insurance Advisory",
  legalName: "[AGENCY LEGAL NAME]",
  advisorName: "[ADVISOR NAME]",
  advisorTitle: "Licensed health insurance agent",
  phone: "",            // e.g. "(555) 123-4567". Empty hides the call button.
  email: "",            // public contact email. Empty hides it.
  address: "[AGENCY MAILING ADDRESS]",
  licensedStates: "[LICENSED STATES AND LICENSE NUMBERS]",
  calendarUrl: "",      // booking link (Calendly etc). Empty sends "Book a call" to the quote form.
  logoUrl: "",          // optional image URL; empty uses the built-in wordmark.

  // The pop-up offer. Only promise what you can deliver.
  incentive: {
    title: "The 2026 Cigna PPO plan comparison for business owners",
    blurb: "All seven plans side by side, with deductibles, copays and out-of-pocket limits, plus a one-page checklist for choosing between them.",
    button: "Send me the guide",
    deliverUrl: "guide.html",   // shown right after signup
    delaySeconds: 12,            // earliest the pop-up may appear
    scrollPercent: 35,           // ...and only after this much scrolling (or exit intent)
    snoozeDays: 7                // after a close, stay hidden this long
  },

  // Flyer premiums. Off until it is confirmed they apply to every visitor.
  showPremiums: false,

  // Where the form posts. Leave as-is when deployed with api/subscribe.js.
  // Set demoMode: true for a static preview that submits nowhere.
  submitUrl: "/api/subscribe",
  demoMode: false
};
