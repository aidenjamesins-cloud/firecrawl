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
  licensedStatesShort: "",  // e.g. "in TX, FL and GA" for the fact strip
  npn: "[NPN]",             // National Producer Number, shown next to your name
  advisorBio: "",           // 1-2 sentences: years in insurance, who you help, where you're based
  advisorPhoto: "",         // URL of a real headshot. Real staff photos earn attention; stock photos get ignored.
  // Real client reviews only (FTC rule bans fake or AI-written testimonials). Leave empty to hide the section.
  // Example: { quote: "...", name: "Dana L.", detail: "Med spa owner, Austin", stars: 5 }
  testimonials: [],
  calendarUrl: "",      // booking link (Calendly etc). Empty sends "Book a call" to the quote form.
  logoUrl: "",          // optional image URL; empty uses the built-in wordmark.

  // The pop-up offer. Only promise what you can deliver.
  incentive: {
    title: "The 2026 Cigna PPO plan comparison for business owners",
    blurb: "All 15 plans side by side, with deductibles, copays and out-of-pocket limits, plus a one-page checklist for choosing between them.",
    button: "Send me the guide",
    deliverUrl: "guide.html",   // shown right after signup
    delaySeconds: 10,            // earliest the pop-up may appear (desktop)
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
