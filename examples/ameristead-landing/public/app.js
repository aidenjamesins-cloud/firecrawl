(function () {
  "use strict";
  var C = window.SITE_CONFIG || {};
  var D = window.PLAN_DATA || { plans: [] };
  var inc = C.incentive || {};
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode */ } }
  };

  /* ---------- Config into the page ---------- */
  function cfg(path) { return path.split(".").reduce(function (o, k) { return o ? o[k] : undefined; }, C); }
  $$("[data-cfg]").forEach(function (el) { var v = cfg(el.getAttribute("data-cfg")); if (v) el.textContent = v; });
  if (C.agencyName) {
    $$("#tcpa-text, #guide-consent-text").forEach(function (el) {
      el.innerHTML = el.innerHTML.replace(/James Insurance Advisory/g, C.agencyName);
    });
  }
  if (C.logoUrl) { var b = $("[data-brand]"); b.innerHTML = '<img alt="">'; b.firstChild.src = C.logoUrl; b.firstChild.alt = C.agencyName || ""; }
  var initials = (C.advisorName && C.advisorName.charAt(0) !== "[" ? C.advisorName : (C.agencyName || "")).split(/\s+/).map(function (w) { return w.charAt(0); }).join("").slice(0, 3);
  $$("[data-initials]").forEach(function (el) { el.textContent = initials; });
  if (C.phone) {
    var tel = "tel:" + C.phone.replace(/[^\d+]/g, "");
    $$("[data-phone]").forEach(function (a) { a.hidden = false; a.href = tel; if (!a.classList.contains("sticky-call")) a.textContent = C.phone; });
  }
  if (C.calendarUrl) {
    $$("[data-calendar]").forEach(function (a) { a.href = C.calendarUrl; a.target = "_blank"; a.rel = "noopener"; });
  }
  if (inc.deliverUrl) $("#guide-link").href = inc.deliverUrl;

  /* ---------- Plans: hero card + table ---------- */
  var order = ["HSA 9000", "Bronze", "HSA 6000", "Silver", "Gold", "Platinum", "Diamond"];
  var plans = order.map(function (n) { return D.plans.filter(function (p) { return p.name === n; })[0]; }).filter(Boolean);
  var slash = function (s) { return String(s).replace("/", " / "); };
  var money = function (n) { return "$" + Number(n).toLocaleString("en-US"); };

  var slider = $("#plan-slider");
  function showPlan(i) {
    var p = plans[i]; if (!p) return;
    $("#pc-name").textContent = p.name;
    $("#pc-hsa").hidden = !p.hsa;
    $("#pc-ded").textContent = slash(p.deductible);
    $("#pc-pcp").textContent = p.primary_care;
    $("#pc-spec").textContent = p.specialist;
    $("#pc-rx").textContent = p.rx;
    $("#pc-oop").textContent = slash(p.max_oop);
    var showPrem = C.showPremiums && p.premiums;
    $("#pc-prem-row").hidden = !showPrem;
    if (showPrem) $("#pc-prem").textContent = money(p.premiums.employee);
    slider.setAttribute("aria-valuetext", p.name);
    $$(".plan-table [data-col]").forEach(function (c) { c.classList.toggle("is-active", +c.getAttribute("data-col") === i); });
  }

  var rows = [
    ["Deductible (ind / fam)", function (p) { return slash(p.deductible); }],
    ["Coinsurance", function (p) { return p.coinsurance; }],
    ["Out-of-pocket max", function (p) { return slash(p.max_oop); }],
    ["Preventive care", function () { return D.common.preventive_care; }],
    ["Teledoctor", function () { return D.common.teledoctor; }],
    ["Primary care", function (p) { return p.primary_care; }],
    ["Specialist", function (p) { return p.specialist; }],
    ["Urgent care", function (p) { return p.urgent_care; }],
    ["Prescriptions", function (p) { return p.rx; }]
  ];
  if (C.showPremiums) {
    rows.push(["Employee only", function (p) { return money(p.premiums.employee); }]);
    rows.push(["Employee + spouse", function (p) { return money(p.premiums.employee_spouse); }]);
    rows.push(["Employee + children", function (p) { return money(p.premiums.employee_children); }]);
    rows.push(["Family", function (p) { return money(p.premiums.family); }]);
  }
  var head = $("#pt-head"), body = $("#pt-body");
  plans.forEach(function (p, i) {
    var th = document.createElement("th"); th.scope = "col"; th.setAttribute("data-col", i);
    th.textContent = p.name;
    if (p.hsa) { var chip = document.createElement("span"); chip.className = "hsa-chip"; chip.textContent = "HSA"; th.appendChild(chip); }
    head.appendChild(th);
  });
  rows.forEach(function (r) {
    var tr = document.createElement("tr");
    var th = document.createElement("th"); th.scope = "row"; th.textContent = r[0]; tr.appendChild(th);
    plans.forEach(function (p, i) { var td = document.createElement("td"); td.setAttribute("data-col", i); td.textContent = r[1](p); tr.appendChild(td); });
    body.appendChild(tr);
  });
  slider.addEventListener("input", function () { showPlan(+slider.value); });
  showPlan(+slider.value);

  /* ---------- Who it's for ---------- */
  var WHO = {
    medspa: ["Med spas and aesthetics practices", "Injectors, estheticians and front desk staff compare benefits when they choose where to work. A Cigna PPO with no referrals and $0 teledoctor is easy to explain in an interview, and you pick the plan design that fits your margins.", "Get a quote for my med spa"],
    cpa: ["CPA and accounting firms", "You already know what employer-paid premiums do on a return. Pick between copay plans and HSA-eligible designs, and keep seasonal and year-round staff on one simple plan.", "Get a quote for my firm"],
    advisor: ["Financial advisors and RIAs", "Pair an HSA 6000 or HSA 9000 with a health savings account for yourself, and offer your associates a recognizable PPO network that holds its own against larger firms.", "Get a quote for my practice"],
    realestate: ["Brokerages and real estate teams", "Agents and team leads who are self-employed can look at plans for just themselves, and brokers with staff can set up group coverage for the people on payroll.", "Get a quote for my team"],
    solo: ["The self-employed", "Earning too much for a marketplace subsidy doesn't have to mean a narrow network. Tell us it's just you and see what a business owner's PPO looks like.", "Get a quote for just me"]
  };
  var tabs = $$("[data-who]");
  function setWho(key, focus) {
    tabs.forEach(function (t) { var on = t.getAttribute("data-who") === key; t.setAttribute("aria-selected", on); t.tabIndex = on ? 0 : -1; if (on && focus) t.focus(); });
    $("#who-title").textContent = WHO[key][0];
    $("#who-body").textContent = WHO[key][1];
    $("#who-cta").textContent = WHO[key][2];
  }
  tabs.forEach(function (t, i) {
    t.addEventListener("click", function () { setWho(t.getAttribute("data-who")); });
    t.addEventListener("keydown", function (e) {
      var d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (d) { e.preventDefault(); setWho(tabs[(i + d + tabs.length) % tabs.length].getAttribute("data-who"), true); }
    });
  });
  setWho("medspa");

  /* ---------- Header + sticky bar ---------- */
  var top = $("#top"), sticky = $("#sticky-cta"), hero = $(".hero"), quote = $("#quote");
  var heroGone = false, quoteVisible = false;
  function updSticky() {
    var show = heroGone && !quoteVisible;
    sticky.classList.toggle("show", show);
    sticky.setAttribute("aria-hidden", !show);
    $$("a", sticky).forEach(function (a) { a.tabIndex = show ? 0 : -1; });
  }
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(function (e) { heroGone = !e[0].isIntersecting; updSticky(); }, { threshold: 0.05 }).observe(hero);
    new IntersectionObserver(function (e) { quoteVisible = e[0].isIntersecting; updSticky(); }, { threshold: 0.1 }).observe(quote);
  }
  window.addEventListener("scroll", function () { top.classList.toggle("scrolled", window.scrollY > 8); }, { passive: true });

  /* ---------- States ---------- */
  var STATES = "AL,AK,AZ,AR,CA,CO,CT,DE,DC,FL,GA,HI,ID,IL,IN,IA,KS,KY,LA,ME,MD,MA,MI,MN,MS,MO,MT,NE,NV,NH,NJ,NM,NY,NC,ND,OH,OK,OR,PA,RI,SC,SD,TN,TX,UT,VT,VA,WA,WV,WI,WY".split(",");
  var ss = $("#state-select");
  STATES.forEach(function (s) { var o = document.createElement("option"); o.value = o.textContent = s; ss.appendChild(o); });

  /* ---------- Submitting ---------- */
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
  function post(payload) {
    payload.page = location.href;
    if (C.demoMode) return new Promise(function (r) { setTimeout(function () { r({ ok: true, demo: true }); }, 500); });
    return fetch(C.submitUrl || "/api/subscribe", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (j) {
        if (!res.ok || !j.ok) throw new Error(j.error || "We couldn't send that. Check your connection and try again.");
        return j;
      });
    });
  }
  function invalid(field, bad) { field.setAttribute("aria-invalid", bad ? "true" : "false"); return bad; }
  function showErr(el, msg) { el.textContent = msg; el.hidden = !msg; }
  function busy(btn, on, label) { btn.disabled = on; if (on) { btn.dataset.label = btn.textContent; btn.textContent = label; } else if (btn.dataset.label) btn.textContent = btn.dataset.label; }

  /* ---------- Quote form (2 steps) ---------- */
  var qf = $("#quote-form"), qErr = $("#q-error");
  var steps = $$(".q-step", qf);
  function goStep(n) {
    steps.forEach(function (s) { s.hidden = +s.getAttribute("data-step") !== n; });
    $("#q-progress").style.width = n === 1 ? "50%" : "100%";
    $("#q-step-label").textContent = n === 1 ? "Step 1 of 2: your business" : "Step 2 of 2: where to send your quote";
    showErr(qErr, "");
    var first = $("input, select", steps[n - 1]); if (first) first.focus();
  }
  $("#q-next").addEventListener("click", function () {
    var bad = $$("select", steps[0]).filter(function (s) { return invalid(s, !s.value); });
    if (bad.length) { showErr(qErr, "Choose an answer for each question to continue."); bad[0].focus(); return; }
    goStep(2);
  });
  $("#q-back").addEventListener("click", function () { goStep(1); });
  qf.addEventListener("submit", function (e) {
    e.preventDefault();
    var f = qf.elements;
    var bad = [];
    ["firstName", "lastName"].forEach(function (n) { if (invalid(f[n], !f[n].value.trim())) bad.push(f[n]); });
    if (invalid(f.email, !EMAIL_RE.test(f.email.value.trim()))) bad.push(f.email);
    var digits = f.phone.value.replace(/\D/g, "");
    if (invalid(f.phone, f.phone.value && (digits.length < 10 || digits.length > 11))) bad.push(f.phone);
    if (f.smsConsent.checked && !digits) { invalid(f.phone, true); bad.push(f.phone); }
    if (bad.length) {
      showErr(qErr, f.smsConsent.checked && !digits ? "Add a mobile number so we can text you, or uncheck the text consent box." : "Check the highlighted fields: we need your name and a valid email.");
      bad[0].focus(); return;
    }
    var btn = $("button[type=submit]", qf);
    busy(btn, true, "Sending...");
    post({
      source: "quote",
      firstName: f.firstName.value.trim(), lastName: f.lastName.value.trim(),
      email: f.email.value.trim(), phone: f.phone.value.trim(),
      businessType: f.businessType.value, employees: f.employees.value, state: f.state.value,
      smsConsent: f.smsConsent.checked, smsConsentText: f.smsConsent.checked ? $("#tcpa-text").textContent.trim() : "",
      emailOptIn: f.emailOptIn.checked, emailOptInText: f.emailOptIn.checked ? $("#email-optin-text").textContent.trim() : "",
      company_website: f.company_website.value
    }).then(function () {
      store.set("jia_lead", "1");
      steps.forEach(function (s) { s.hidden = true; });
      $(".progress", qf).hidden = true; $("#q-step-label").hidden = true;
      var done = $("#q-done"); done.hidden = false; done.focus();
    }).catch(function (err) { showErr(qErr, err.message); }).then(function () { busy(btn, false); });
  });

  /* ---------- Pop-up ---------- */
  var modal = $("#guide-modal"), gf = $("#guide-form"), lastFocus = null, popupShown = false;
  var SNOOZE = "jia_popup_snooze", DONE = "jia_guide";
  function canAuto() {
    if (store.get(DONE) || store.get("jia_lead")) return false;
    var until = +store.get(SNOOZE) || 0;
    return Date.now() > until;
  }
  function openModal() {
    if (!modal.hidden) return;
    popupShown = true;
    lastFocus = document.activeElement;
    modal.hidden = false; document.body.classList.add("modal-open");
    var first = $("input", modal); if (first && !gf.hidden) first.focus(); else $(".modal-x", modal).focus();
  }
  function closeModal() {
    if (modal.hidden) return;
    modal.hidden = true; document.body.classList.remove("modal-open");
    if (!store.get(DONE)) store.set(SNOOZE, String(Date.now() + (inc.snoozeDays || 7) * 864e5));
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  $$("[data-open-guide]").forEach(function (b) { b.addEventListener("click", openModal); });
  $$("[data-close]", modal).forEach(function (b) { b.addEventListener("click", closeModal); });
  modal.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { closeModal(); return; }
    if (e.key !== "Tab") return;
    var f = $$("a[href], button, input:not([tabindex='-1'])", modal).filter(function (el) { return el.offsetParent !== null; });
    if (!f.length) return;
    if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
    else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
  });

  // Auto-open: after a delay AND some scrolling, or on exit intent (desktop). Never on load.
  var timeOk = false, scrollOk = false;
  function maybeAuto() { if (!popupShown && timeOk && scrollOk && canAuto() && !quoteVisible) openModal(); }
  setTimeout(function () { timeOk = true; maybeAuto(); }, (inc.delaySeconds || 12) * 1000);
  window.addEventListener("scroll", function () {
    var max = document.documentElement.scrollHeight - innerHeight;
    if (max > 0 && scrollY / max * 100 >= (inc.scrollPercent || 35)) { scrollOk = true; maybeAuto(); }
  }, { passive: true });
  document.addEventListener("mouseout", function (e) {
    if (!e.relatedTarget && e.clientY <= 0 && timeOk && !popupShown && canAuto()) openModal();
  });

  gf.addEventListener("submit", function (e) {
    e.preventDefault();
    var f = gf.elements, err = $(".form-error", gf);
    var bad = [];
    if (invalid(f.firstName, !f.firstName.value.trim())) bad.push(f.firstName);
    if (invalid(f.email, !EMAIL_RE.test(f.email.value.trim()))) bad.push(f.email);
    if (bad.length) { showErr(err, "Add your first name and a valid email to get the guide."); bad[0].focus(); return; }
    var btn = $("button[type=submit]", gf);
    busy(btn, true, "Sending...");
    post({
      source: "guide", firstName: f.firstName.value.trim(), email: f.email.value.trim(),
      emailOptIn: true, emailOptInText: $("#guide-consent-text").textContent.trim(),
      company_website: f.company_website.value
    }).then(function () {
      store.set(DONE, "1");
      gf.hidden = true; var done = $(".modal-done", modal); done.hidden = false; $("#guide-link").focus();
    }).catch(function (er) { showErr(err, er.message); }).then(function () { busy(btn, false); });
  });
})();
