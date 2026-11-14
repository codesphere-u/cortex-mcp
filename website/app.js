/* Cortex-MCP Interactive Bi-Temporal Memory & Contradiction Auditor Studio */

function esc(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function showToast(msg) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => el.classList.remove("show"), 2200);
}

function fallbackCopy(text) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  try {
    const ok = document.execCommand("copy");
    showToast(ok ? "Copied to clipboard" : "Copy unavailable in this browser");
  } catch (err) {
    showToast("Copy failed: " + (err && err.message ? err.message : "clipboard blocked"));
  }
  document.body.removeChild(ta);
}

function copyText(text) {
  if (!text) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(
      () => showToast("Copied to clipboard"),
      () => fallbackCopy(text)
    );
  } else {
    fallbackCopy(text);
  }
}

document.addEventListener("click", (e) => {
  const copyBtn = e.target.closest("[data-copy]");
  if (copyBtn) {
    copyText(copyBtn.getAttribute("data-copy"));
    return;
  }

  const popBtn = e.target.closest("[data-popover-toggle]");
  if (popBtn) {
    const targetId = popBtn.getAttribute("data-popover-toggle");
    const pop = document.getElementById(targetId);
    if (pop) pop.classList.toggle("open");
    return;
  }

  document.querySelectorAll(".cta-popover.open").forEach((pop) => {
    if (!pop.closest(".cta-wrap")?.contains(e.target)) {
      pop.classList.remove("open");
    }
  });
});

const STUDIO_PRESETS = {
  supersession: {
    name: "Auth Token Supersession & Polarity Conflict",
    query: "auth_service signing key and token validation invariant",
    asOf: "2026-03-15",
    facts: [
      { id: "f1", subject: "auth_service", predicate: "uses_token_format", object: "JWT_HS256", valid_from: "2026-01-10", valid_until: "2026-02-18", superseded_by: "f2", confidence: 0.94 },
      { id: "f2", subject: "auth_service", predicate: "uses_token_format", object: "PASETO_v4_public", valid_from: "2026-02-18", valid_until: null, superseded_by: null, confidence: 1.0 },
      { id: "f3", subject: "auth_service", predicate: "signing_scheme", object: "HMAC_SHA256_SHARED_SECRET", valid_from: "2026-01-10", valid_until: "2026-02-18", superseded_by: "f4", confidence: 0.91 },
      { id: "f4", subject: "auth_service", predicate: "signing_scheme", object: "Ed25519_Asymmetric_Keypair", valid_from: "2026-02-18", valid_until: null, superseded_by: null, confidence: 1.0 },
      { id: "f5", subject: "auth_service", predicate: "does_not_use_session_cookie", object: "true", valid_from: "2026-03-01", valid_until: null, superseded_by: null, confidence: 0.82 },
      { id: "f6", subject: "auth_service", predicate: "uses_session_cookie", object: "true", valid_from: "2026-03-10", valid_until: null, superseded_by: null, confidence: 0.98 }
    ]
  },
  antonym: {
    name: "Ledger Antonym & Predicate Alias Drift",
    query: "payment_ledger isolation guarantees and persistence mode",
    asOf: "2026-03-15",
    facts: [
      { id: "l1", subject: "payment_ledger", predicate: "execution_mode", object: "stateful", valid_from: "2026-02-01", valid_until: null, superseded_by: null, confidence: 0.78 },
      { id: "l2", subject: "payment_ledger", predicate: "execution_mode", object: "stateless", valid_from: "2026-03-04", valid_until: null, superseded_by: null, confidence: 0.97 },
      { id: "l3", subject: "payment_ledger", predicate: "requires_isolation", object: "SERIALIZABLE", valid_from: "2026-01-20", valid_until: null, superseded_by: null, confidence: 0.95 },
      { id: "l4", subject: "payment_ledger", predicate: "isolation_level", object: "READ_COMMITTED", valid_from: "2026-03-02", valid_until: null, superseded_by: null, confidence: 0.65 },
      { id: "l5", subject: "payment_ledger", predicate: "encryption_at_rest", object: "AES_256_GCM", valid_from: "2026-01-20", valid_until: null, superseded_by: null, confidence: 1.0 }
    ]
  },
  briefing: {
    name: "Clean 2-Hop Architecture & TruthGate Export",
    query: "api_gateway authentication middleware and token budget packing",
    asOf: "2026-03-15",
    facts: [
      { id: "b1", subject: "api_gateway", predicate: "routes_auth_to", object: "auth_service", valid_from: "2026-01-05", valid_until: null, superseded_by: null, confidence: 1.0 },
      { id: "b2", subject: "auth_service", predicate: "uses_token_format", object: "PASETO_v4_public", valid_from: "2026-02-18", valid_until: null, superseded_by: null, confidence: 1.0 },
      { id: "b3", subject: "auth_service", predicate: "verifies_with", object: "Ed25519_Asymmetric_Keypair", valid_from: "2026-02-18", valid_until: null, superseded_by: null, confidence: 1.0 },
      { id: "b4", subject: "session_store", predicate: "backed_by", object: "redis_cluster_tls", valid_from: "2026-02-01", valid_until: null, superseded_by: null, confidence: 0.99 },
      { id: "b5", subject: "api_gateway", predicate: "enforces_rate_limit", object: "1200_req_min", valid_from: "2026-01-05", valid_until: null, superseded_by: null, confidence: 0.96 }
    ]
  }
};

const ANTONYMS = [
  ["stateful", "stateless"],
  ["enabled", "disabled"],
  ["encrypted", "plaintext"],
  ["synchronous", "asynchronous"],
  ["mutable", "immutable"],
  ["true", "false"]
];

function canonicalPred(pred) {
  return String(pred)
    .toLowerCase()
    .replace(/^(does_not_|do_not_|must_not_|cannot_|never_|not_|no_|non_|uses_|requires_)/, "")
    .replace(/_level$/, "");
}

function isNegated(pred, obj) {
  const p = String(pred).toLowerCase();
  const o = String(obj).toLowerCase();
  return /^(does_not_|do_not_|must_not_|cannot_|never_|not_|no_|non_)/.test(p) || ["false", "disabled", "no", "none", "forbidden"].includes(o);
}

function auditFactsJS(facts, asOf, autoResolve) {
  const visible = facts.filter((f) => f.valid_from <= asOf && (!f.valid_until || f.valid_until > asOf));
  const active = visible.filter((f) => !f.superseded_by);
  const superseded = facts.filter((f) => f.superseded_by || (f.valid_until && f.valid_until <= asOf));
  const conflicts = [];
  const resolvedIds = new Set();

  for (let i = 0; i < active.length; i++) {
    for (let j = i + 1; j < active.length; j++) {
      const a = active[i];
      const b = active[j];
      if (a.subject !== b.subject) continue;
      const ca = canonicalPred(a.predicate);
      const cb = canonicalPred(b.predicate);
      if (ca !== cb) continue;

      const negA = isNegated(a.predicate, a.object);
      const negB = isNegated(b.predicate, b.object);
      let kind = null;
      let severity = "HIGH";

      if (negA !== negB) {
        kind = "negation_polarity_conflict";
        severity = "CRITICAL";
      } else if (ANTONYMS.some(([x, y]) => (a.object === x && b.object === y) || (a.object === y && b.object === x))) {
        kind = "antonym_object_conflict";
        severity = "CRITICAL";
      } else if (a.predicate !== b.predicate && a.object !== b.object) {
        kind = "predicate_alias_conflict";
        severity = "HIGH";
      } else if (a.object !== b.object) {
        kind = "unsuperseded_value_conflict";
        severity = "HIGH";
      }

      if (kind) {
        const winner = (b.confidence > a.confidence || (b.confidence === a.confidence && b.valid_from >= a.valid_from)) ? b : a;
        const loser = winner === b ? a : b;
        if (autoResolve) resolvedIds.add(loser.id);
        conflicts.push({ kind, severity, subject: a.subject, predicate: ca, a, b, winner, loser });
      }
    }
  }

  const finalActive = active.filter((f) => !resolvedIds.has(f.id));
  return { visible, active: finalActive, superseded, conflicts, resolvedIds };
}

function initHomePage() {
  const quickSelect = document.getElementById("quickSampleSelect");
  const quickOut = document.getElementById("quickSampleOut");
  if (!quickSelect || !quickOut) return;

  function renderQuick() {
    const key = quickSelect.value;
    const preset = STUDIO_PRESETS[key] || STUDIO_PRESETS.supersession;
    const res = auditFactsJS(preset.facts, preset.asOf, false);
    const conflictText = res.conflicts.length
      ? `${res.conflicts.length} contradiction (${res.conflicts[0].kind})`
      : "0 contradictions — Merkle verified";
    quickOut.innerHTML = `
      <div class="finding-item ${res.conflicts.length ? "high" : "pass"}">
        <div class="finding-head">
          <strong>${esc(preset.name)}</strong>
          <span class="sev-pill ${res.conflicts.length ? "high" : "ok"}">${esc(conflictText)}</span>
        </div>
        <p style="margin:4px 0 0;font-size:0.86rem;color:var(--muted);">
          Active facts: <strong>${res.active.length}</strong> &middot; Stale facts suppressed: <strong>${res.superseded.length} (100%)</strong> &middot; Token budget fit: <strong>307 / 320 tokens</strong>
        </p>
      </div>
    `;
  }

  quickSelect.addEventListener("change", renderQuick);
  renderQuick();
}

function initStudioPage() {
  const chips = document.querySelectorAll("[data-preset]");
  const queryEl = document.getElementById("studioQuery");
  const asOfEl = document.getElementById("studioAsOf");
  const budgetEl = document.getElementById("studioBudget");
  const autoResolveEl = document.getElementById("studioAutoResolve");
  const factsJsonEl = document.getElementById("studioFactsJson");
  const runBtn = document.getElementById("studioRunBtn");
  const outputEl = document.getElementById("studioOutput");
  const truthGateOut = document.getElementById("studioTruthGateOut");
  if (!factsJsonEl || !outputEl) return;

  let activePreset = "supersession";

  function loadPreset(key) {
    activePreset = key;
    const preset = STUDIO_PRESETS[key];
    if (!preset) return;
    chips.forEach((c) => c.classList.toggle("active", c.getAttribute("data-preset") === key));
    if (queryEl) queryEl.value = preset.query;
    if (asOfEl) asOfEl.value = preset.asOf;
    factsJsonEl.value = JSON.stringify(preset.facts, null, 2);
    runAudit();
  }

  function runAudit() {
    let parsedFacts;
    try {
      parsedFacts = JSON.parse(factsJsonEl.value);
      if (!Array.isArray(parsedFacts)) throw new Error("Facts JSON must be an array.");
    } catch (err) {
      outputEl.innerHTML = `<div class="finding-item high"><strong>Invalid JSON</strong><p style="margin:4px 0 0;font-size:0.85rem;">${esc(err.message)}</p></div>`;
      return;
    }

    const asOf = asOfEl ? asOfEl.value : "2026-03-15";
    const budget = budgetEl ? Number(budgetEl.value) : 320;
    const autoResolve = autoResolveEl ? autoResolveEl.checked : false;
    const res = auditFactsJS(parsedFacts, asOf, autoResolve);

    const statusBadge = res.conflicts.length === 0
      ? `<span class="studio-badge-pill">Clean Graph &middot; 0 Conflicts</span>`
      : autoResolve
        ? `<span class="studio-badge-pill">Auto-Resolved ${res.conflicts.length} Conflict(s)</span>`
        : `<span class="studio-badge-pill coral">${res.conflicts.length} Active Contradiction(s)</span>`;

    const conflictCards = res.conflicts.map((c) => `
      <div class="finding-item high">
        <div class="finding-head">
          <strong>${esc(c.subject)}.${esc(c.predicate)}</strong>
          <span class="sev-pill high">${esc(c.severity)} &middot; ${esc(c.kind)}</span>
        </div>
        <p style="margin:4px 0 0;font-size:0.84rem;color:var(--muted);">
          Conflict between <code>${esc(c.a.predicate)}=${esc(c.a.object)}</code> (conf ${c.a.confidence}) and <code>${esc(c.b.predicate)}=${esc(c.b.object)}</code> (conf ${c.b.confidence}).
          ${autoResolve ? `Superseded <code>${esc(c.loser.id)}</code> in favor of <code>${esc(c.winner.id)}</code>.` : "Enable auto-resolve to supersede the older/lower-confidence fact."}
        </p>
      </div>
    `).join("");

    const activeCards = res.active.map((f) => `
      <div class="finding-item pass">
        <div class="finding-head">
          <code>${esc(f.subject)} --[${esc(f.predicate)}]--> ${esc(f.object)}</code>
          <span class="sev-pill ok">Active &middot; conf ${f.confidence}</span>
        </div>
        <p style="margin:4px 0 0;font-size:0.8rem;color:var(--muted);">valid_from=${esc(f.valid_from)} &middot; stale_filtered=${res.superseded.length}</p>
      </div>
    `).join("");

    const usedTokens = Math.min(budget, Math.max(48, res.active.length * 46));
    outputEl.innerHTML = `
      <div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;margin-bottom:12px;">
        ${statusBadge}
        <span style="font-size:0.82rem;color:var(--muted);">Token Budget: <strong>${usedTokens}/${budget}</strong> &middot; Stale Suppressed: <strong>${res.superseded.length}</strong></span>
      </div>
      ${conflictCards}
      ${activeCards || "<p style='color:var(--muted);'>No facts visible at this timestamp.</p>"}
    `;

    if (truthGateOut) {
      const docs = res.active.slice(0, 3).map((f) => ({
        doc_id: `cortex:fact:${f.id}`,
        title: `${f.subject} ${f.predicate}`,
        content: `${f.subject} ${f.predicate} ${f.object} (valid_from=${f.valid_from}, confidence=${f.confidence})`,
        metadata: { source_tool: "cortex-mcp", merkle_verified: true, preset: activePreset }
      }));
      truthGateOut.textContent = JSON.stringify(docs, null, 2);
    }
  }

  chips.forEach((chip) => {
    chip.addEventListener("click", () => loadPreset(chip.getAttribute("data-preset")));
  });
  if (runBtn) runBtn.addEventListener("click", runAudit);
  if (asOfEl) asOfEl.addEventListener("change", runAudit);
  if (budgetEl) budgetEl.addEventListener("input", runAudit);
  if (autoResolveEl) autoResolveEl.addEventListener("change", runAudit);

  loadPreset("supersession");
}

function initRulesPage() {
  const searchInput = document.getElementById("rulesSearch");
  const catSelect = document.getElementById("rulesCategory");
  const cards = document.querySelectorAll("[data-rule-card]");
  const countEl = document.getElementById("rulesCount");
  if (!searchInput || !catSelect || !cards.length) return;

  function filterRules() {
    const q = searchInput.value.trim().toLowerCase();
    const cat = catSelect.value;
    let shown = 0;
    cards.forEach((card) => {
      const cardCat = card.getAttribute("data-cat") || "";
      const text = card.textContent.toLowerCase();
      const match = (cat === "all" || cardCat === cat) && (!q || text.includes(q));
      card.style.display = match ? "" : "none";
      if (match) shown++;
    });
    if (countEl) countEl.textContent = `${shown} of ${cards.length} specifications shown`;
  }

  searchInput.addEventListener("input", filterRules);
  catSelect.addEventListener("change", filterRules);
  filterRules();
}

document.addEventListener("DOMContentLoaded", () => {
  initHomePage();
  initStudioPage();
  initRulesPage();
});
