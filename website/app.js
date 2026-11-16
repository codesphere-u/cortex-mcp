/* Cortex-MCP v1.2.0 — Interactive Workbench, Studio, Docs & Client Switcher */

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

function fallbackCopy(text, btn) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  try {
    const ok = document.execCommand("copy");
    if (ok && btn) markCopied(btn);
    showToast(ok ? "Copied to clipboard" : "Copy unavailable in this browser");
  } catch (err) {
    showToast("Copy failed: " + (err && err.message ? err.message : "blocked"));
  }
  document.body.removeChild(ta);
}

function markCopied(btn) {
  if (!btn) return;
  const orig = btn.getAttribute("data-orig-label") || btn.innerHTML;
  if (!btn.getAttribute("data-orig-label")) {
    btn.setAttribute("data-orig-label", orig);
  }
  btn.classList.add("copied");
  btn.textContent = "Copied!";
  clearTimeout(btn.__copyTimer);
  btn.__copyTimer = setTimeout(() => {
    btn.classList.remove("copied");
    btn.innerHTML = btn.getAttribute("data-orig-label");
  }, 1800);
}

function copyText(text, btn) {
  if (!text) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(
      () => {
        markCopied(btn);
        showToast("Copied to clipboard");
      },
      () => fallbackCopy(text, btn)
    );
  } else {
    fallbackCopy(text, btn);
  }
}

/* ---------------- Theme Switcher (Dark Default / Daylight) ---------------- */
function initTheme() {
  const saved = localStorage.getItem("cortex-theme");
  if (saved === "light" || saved === "dark") {
    document.documentElement.setAttribute("data-theme", saved);
  }
  const btn = document.getElementById("themeToggleBtn");
  if (!btn) return;
  const updateIcon = () => {
    const isLight = document.documentElement.getAttribute("data-theme") === "light";
    btn.setAttribute("aria-label", isLight ? "Switch to dark theme" : "Switch to light theme");
    btn.setAttribute("title", isLight ? "Switch to dark theme" : "Switch to light theme");
    btn.innerHTML = isLight
      ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'
      : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>';
  };
  updateIcon();
  btn.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
    const next = current === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("cortex-theme", next);
    updateIcon();
  });
}

/* ---------------- Mobile Menu Drawer ---------------- */
function initMobileMenu() {
  const btn = document.getElementById("mobileMenuBtn");
  const drawer = document.getElementById("mobileDrawer");
  if (!btn || !drawer) return;
  btn.addEventListener("click", () => {
    const open = drawer.classList.toggle("open");
    btn.setAttribute("aria-expanded", String(open));
  });
}

/* ---------------- Global Cmd+K Search Index & Modal ---------------- */
const SEARCH_INDEX = [
  { title: "MCP Client Setup (Claude, Cursor, Windsurf, Antigravity)", desc: "Exact config paths, HTTP vs local stdio snippets", url: "docs.html#client-setup", badge: "Guide" },
  { title: "Transport Comparison: Streamable HTTP vs Local Stdio", desc: "When to use Vercel HTTP vs persistent --storage stdio", url: "docs.html#transports", badge: "Docs" },
  { title: "Installation & Quickstart", desc: "pip / uvx installation, demo & reproducible benchmark", url: "docs.html#install", badge: "Docs" },
  { title: "Bi-Temporal Graph Model", desc: "valid_from, valid_until, superseded_by & Merkle chain", url: "docs.html#bitemporal", badge: "Core" },
  { title: "Okapi BM25 & 2-Hop Context Compiler", desc: "Code-aware tokenizer and strict max_tokens packing", url: "docs.html#compiler", badge: "Core" },
  { title: "Contradiction Auditor & Auto-Resolve", desc: "Polarity, antonyms, alias collisions, and singular drift", url: "docs.html#contradictions", badge: "Core" },
  { title: "TruthGate GroundedSourceDocument Export", desc: "Export verifiable citations via export-sources CLI", url: "docs.html#truthgate", badge: "Export" },
  { title: "CLI Subcommand Reference", desc: "demo, benchmark, serve-stdio, serve-http, audit-contradictions", url: "docs.html#cli", badge: "CLI" },
  { title: "Bi-Temporal Memory Studio", desc: "Interactive graph topology, time-travel slider & audit sandbox", url: "studio.html", badge: "Studio" },
  { title: "Benchmarks & Architectural Proof", desc: "500 facts / 100 episodes P50/P95 latencies & ADRs", url: "proof.html", badge: "Proof" },
  { title: "memory_record_episode", desc: "MCP Tool · Record immutable ADR, bug_root_cause, or invariant", url: "rules.html#tool-memory_record_episode", badge: "Tool" },
  { title: "memory_upsert_fact", desc: "MCP Tool · Write (subject_id, predicate, object) with supersession", url: "rules.html#tool-memory_upsert_fact", badge: "Tool" },
  { title: "memory_compile_context", desc: "MCP Tool · BM25 + 2-hop subgraph packing within max_tokens", url: "rules.html#tool-memory_compile_context", badge: "Tool" },
  { title: "memory_query_entity", desc: "MCP Tool · Inspect active/superseded facts & K-hop ego graph", url: "rules.html#tool-memory_query_entity", badge: "Tool" },
  { title: "memory_time_travel", desc: "MCP Tool · Reconstruct valid graph state as_of UTC timestamp", url: "rules.html#tool-memory_time_travel", badge: "Tool" },
  { title: "memory_verify_integrity", desc: "MCP Tool · Verify SHA-256 chain & compute Merkle root digest", url: "rules.html#tool-memory_verify_integrity", badge: "Tool" },
  { title: "cortex_audit_contradictions", desc: "MCP Tool · Scan active facts for logical/polarity conflicts", url: "rules.html#tool-cortex_audit_contradictions", badge: "Tool" },
  { title: "cortex://graph/summary", desc: "MCP Resource · Live entity, active/superseded fact, episode counts", url: "rules.html#res-summary", badge: "Resource" },
  { title: "cortex://graph/integrity", desc: "MCP Resource · Full cryptographic SHA-256 integrity report", url: "rules.html#res-integrity", badge: "Resource" },
  { title: "cortex://episodes/recent", desc: "MCP Resource · Latest 20 recorded ADRs and invariants", url: "rules.html#res-episodes", badge: "Resource" },
  { title: "architecture-briefing", desc: "MCP Prompt · Verified briefing before modifying a component", url: "rules.html#prompt-arch", badge: "Prompt" },
  { title: "bug-investigation-context", desc: "MCP Prompt · Structured root-cause context for a symptom", url: "rules.html#prompt-bug", badge: "Prompt" },
  { title: "negation_polarity_conflict", desc: "CRITICAL rule · does_not_* vs affirmative predicate conflict", url: "rules.html#conflict-polarity", badge: "Rule" },
  { title: "antonym_object_conflict", desc: "CRITICAL rule · stateful vs stateless, encrypted vs plaintext", url: "rules.html#conflict-antonym", badge: "Rule" }
];

function initCommandSearch() {
  const modal = document.getElementById("cmdBackdrop");
  const input = document.getElementById("cmdSearchInput");
  const results = document.getElementById("cmdResults");
  const triggers = document.querySelectorAll("[data-open-search]");
  if (!modal || !input || !results) return;

  function renderResults(q) {
    const query = q.trim().toLowerCase();
    const matches = SEARCH_INDEX.filter((item) =>
      !query || item.title.toLowerCase().includes(query) || item.desc.toLowerCase().includes(query) || item.badge.toLowerCase().includes(query)
    ).slice(0, 10);

    if (!matches.length) {
      results.innerHTML = `<div style="padding:18px;text-align:center;color:var(--muted);font-size:0.86rem;">No matches for "${esc(q)}"</div>`;
      return;
    }

    results.innerHTML = matches.map((m, idx) => `
      <a class="cmd-item ${idx === 0 ? "selected" : ""}" href="${esc(m.url)}">
        <div>
          <div class="cmd-item-title">${esc(m.title)}</div>
          <div class="cmd-item-desc">${esc(m.desc)}</div>
        </div>
        <span class="pill-tag cyan">${esc(m.badge)}</span>
      </a>
    `).join("");
  }

  function openModal() {
    modal.classList.add("open");
    input.value = "";
    renderResults("");
    setTimeout(() => input.focus(), 20);
  }

  function closeModal() {
    modal.classList.remove("open");
  }

  triggers.forEach((t) => t.addEventListener("click", openModal));
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });
  input.addEventListener("input", () => renderResults(input.value));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
    if (e.key === "Enter") {
      const first = results.querySelector(".cmd-item");
      if (first) window.location.href = first.getAttribute("href");
    }
  });

  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      if (modal.classList.contains("open")) closeModal();
      else openModal();
    } else if (e.key === "Escape" && modal.classList.contains("open")) {
      closeModal();
    }
  });
}

/* ---------------- Client Config Switcher (Stitch + Plannotator Inspired) ---------------- */
const CLIENT_CONFIGS = {
  "claude-code": {
    label: "Claude Code CLI",
    transport: "Streamable HTTP",
    path: "Project or User Scope (~/.claude.json)",
    lang: "bash",
    raw: `claude mcp add --transport http cortex-mcp https://cortex-mcp-steel.vercel.app/mcp\n\n# Or install globally across all repositories:\nclaude mcp add --scope user --transport http cortex-mcp https://cortex-mcp-steel.vercel.app/mcp`,
    html: `<span class="tok-f">claude</span> mcp add <span class="tok-k">--transport</span> http cortex-mcp <span class="tok-s">https://cortex-mcp-steel.vercel.app/mcp</span>\n\n<span class="tok-c"># Or install globally across all repositories:</span>\n<span class="tok-f">claude</span> mcp add <span class="tok-k">--scope</span> user <span class="tok-k">--transport</span> http cortex-mcp <span class="tok-s">https://cortex-mcp-steel.vercel.app/mcp</span>`
  },
  "cursor": {
    label: "Cursor",
    transport: "Streamable HTTP",
    path: ".cursor/mcp.json  (or ~/.cursor/mcp.json)",
    lang: "json",
    raw: `{\n  "mcpServers": {\n    "cortex-mcp": {\n      "type": "http",\n      "url": "https://cortex-mcp-steel.vercel.app/mcp"\n    }\n  }\n}`,
    html: `{\n  <span class="tok-k">"mcpServers"</span>: {\n    <span class="tok-k">"cortex-mcp"</span>: {\n      <span class="tok-k">"type"</span>: <span class="tok-s">"http"</span>,\n      <span class="tok-k">"url"</span>: <span class="tok-s">"https://cortex-mcp-steel.vercel.app/mcp"</span>\n    }\n  }\n}`
  },
  "windsurf": {
    label: "Windsurf",
    transport: "Streamable HTTP",
    path: "~/.codeium/windsurf/mcp_config.json",
    lang: "json",
    raw: `{\n  "mcpServers": {\n    "cortex-mcp": {\n      "serverUrl": "https://cortex-mcp-steel.vercel.app/mcp"\n    }\n  }\n}`,
    html: `{\n  <span class="tok-k">"mcpServers"</span>: {\n    <span class="tok-k">"cortex-mcp"</span>: {\n      <span class="tok-k">"serverUrl"</span>: <span class="tok-s">"https://cortex-mcp-steel.vercel.app/mcp"</span>\n    }\n  }\n}`
  },
  "claude-desktop": {
    label: "Claude Desktop",
    transport: "Local Stdio (Persistent JSON)",
    path: "~/Library/Application Support/Claude/claude_desktop_config.json",
    lang: "json",
    raw: `{\n  "mcpServers": {\n    "cortex-mcp": {\n      "command": "uvx",\n      "args": [\n        "--from", "git+https://github.com/codesphere-u/cortex-mcp.git",\n        "cortex-mcp", "serve-stdio", "--storage", "~/.cortex-mcp/memory.json"\n      ]\n    }\n  }\n}`,
    html: `{\n  <span class="tok-k">"mcpServers"</span>: {\n    <span class="tok-k">"cortex-mcp"</span>: {\n      <span class="tok-k">"command"</span>: <span class="tok-s">"uvx"</span>,\n      <span class="tok-k">"args"</span>: [\n        <span class="tok-s">"--from"</span>, <span class="tok-s">"git+https://github.com/codesphere-u/cortex-mcp.git"</span>,\n        <span class="tok-s">"cortex-mcp"</span>, <span class="tok-s">"serve-stdio"</span>, <span class="tok-s">"--storage"</span>, <span class="tok-s">"~/.cortex-mcp/memory.json"</span>\n      ]\n    }\n  }\n}`
  },
  "antigravity": {
    label: "Antigravity / VS Code",
    transport: "HTTP or Local Stdio",
    path: "Command Palette (Cmd+Shift+P) -> MCP: Add Server",
    lang: "json",
    raw: `{\n  "mcpServers": {\n    "cortex-mcp": {\n      "type": "http",\n      "url": "https://cortex-mcp-steel.vercel.app/mcp"\n    }\n  }\n}`,
    html: `{\n  <span class="tok-k">"mcpServers"</span>: {\n    <span class="tok-k">"cortex-mcp"</span>: {\n      <span class="tok-k">"type"</span>: <span class="tok-s">"http"</span>,\n      <span class="tok-k">"url"</span>: <span class="tok-s">"https://cortex-mcp-steel.vercel.app/mcp"</span>\n    }\n  }\n}`
  },
  "uvx-stdio": {
    label: "Local CLI / uvx",
    transport: "Local Stdio + Seed Demo",
    path: "Zero-Install Terminal Runner",
    lang: "bash",
    raw: `uvx --from git+https://github.com/codesphere-u/cortex-mcp.git cortex-mcp demo\n\n# Start local persistent stdio MCP server:\nuvx --from git+https://github.com/codesphere-u/cortex-mcp.git cortex-mcp serve-stdio --storage .cortex/memory.json`,
    html: `<span class="tok-f">uvx</span> <span class="tok-k">--from</span> <span class="tok-s">git+https://github.com/codesphere-u/cortex-mcp.git</span> cortex-mcp demo\n\n<span class="tok-c"># Start local persistent stdio MCP server:</span>\n<span class="tok-f">uvx</span> <span class="tok-k">--from</span> <span class="tok-s">git+https://github.com/codesphere-u/cortex-mcp.git</span> cortex-mcp serve-stdio <span class="tok-k">--storage</span> <span class="tok-s">.cortex/memory.json</span>`
  }
};

function initClientSwitchers() {
  document.querySelectorAll("[data-client-switcher]").forEach((shell) => {
    const pills = shell.querySelectorAll("[data-client]");
    const pathEl = shell.querySelector("[data-client-path]");
    const transportEl = shell.querySelector("[data-client-transport]");
    const langEl = shell.querySelector("[data-client-lang]");
    const codeEl = shell.querySelector("[data-client-code]");
    const copyBtn = shell.querySelector("[data-client-copy]");

    function selectClient(key) {
      const cfg = CLIENT_CONFIGS[key] || CLIENT_CONFIGS["claude-code"];
      pills.forEach((p) => p.classList.toggle("active", p.getAttribute("data-client") === key));
      if (pathEl) pathEl.textContent = cfg.path;
      if (transportEl) transportEl.textContent = cfg.transport;
      if (langEl) langEl.textContent = cfg.lang;
      if (codeEl) codeEl.innerHTML = cfg.html;
      if (copyBtn) copyBtn.setAttribute("data-copy", cfg.raw);
    }

    pills.forEach((p) => p.addEventListener("click", () => selectClient(p.getAttribute("data-client"))));
    selectClient("claude-code");
  });
}

/* ---------------- Hero Interactive Bi-Temporal Workbench (Univer Inspired) ---------------- */
const HERO_STATES = {
  "t1": {
    asOf: "2026-01-10T09:00:00Z",
    fx: 'memory_time_travel(as_of="2026-01-10T09:00:00Z")',
    merkle: "sha256:4a92c1f8...",
    usedTok: 164,
    maxTok: 320,
    suppressed: 0,
    tokenScheme: "JWT_HS256",
    signingScheme: "HMAC_SHA256_SHARED_SECRET",
    isMigrated: false,
    hasLedger: false,
    compiledRows: [
      { cls: "active-fact", text: "[FACT:fact_auth_token_v1] auth_service --(uses_token_format)--> JWT_HS256 (valid_from=2026-01-10)" },
      { cls: "active-fact", text: "[FACT:fact_auth_key_v1] auth_service --(signing_primitive)--> HMAC_SHA256_SHARED_SECRET" },
      { cls: "active-fact", text: "[ADR:ep_adr_001] ADR-001: Initial Session Token Format | files: src/auth/tokens.py" }
    ]
  },
  "t3": {
    asOf: "2026-03-01T11:15:00Z",
    fx: 'memory_compile_context(query="auth_service payment_ledger", as_of="2026-03-01")',
    merkle: "sha256:9f20be31...",
    usedTok: 268,
    maxTok: 320,
    suppressed: 0,
    tokenScheme: "JWT_HS256",
    signingScheme: "HMAC_SHA256_SHARED_SECRET",
    isMigrated: false,
    hasLedger: true,
    compiledRows: [
      { cls: "active-fact", text: "[INVARIANT:ep_inv_007] payment_ledger MUST supply idempotency_key in SERIALIZABLE tx" },
      { cls: "active-fact", text: "[FACT:fact_ledger_auth_dep] payment_ledger --(verifies_caller_via)--> auth_service" },
      { cls: "active-fact", text: "[FACT:fact_auth_token_v1] auth_service --(uses_token_format)--> JWT_HS256" },
      { cls: "active-fact", text: "[FACT:fact_order_depends_ledger] order_repository --(depends_on)--> payment_ledger" }
    ]
  },
  "t4": {
    asOf: "2026-04-20T16:45:00Z",
    fx: 'memory_compile_context(query="auth_service token signing & payment_ledger", max_tokens=320)',
    merkle: "sha256:e893bf67...",
    usedTok: 307,
    maxTok: 320,
    suppressed: 2,
    tokenScheme: "PASETO_v4_public",
    signingScheme: "Ed25519_Asymmetric_Keypair",
    isMigrated: true,
    hasLedger: true,
    compiledRows: [
      { cls: "active-fact", text: "[FACT:fact_auth_token_v2] auth_service --(uses_token_format)--> PASETO_v4_public (src=ep_adr_019)" },
      { cls: "active-fact", text: "[FACT:fact_auth_key_v2] auth_service --(signing_primitive)--> Ed25519_Asymmetric_Keypair" },
      { cls: "active-fact", text: "[INVARIANT:ep_inv_007] INV-007: Payment Ledger Idempotency & Zero-Sum Double Entry" },
      { cls: "superseded-fact", text: "SUPPRESSED: auth_service --(uses_token_format)--> JWT_HS256 (valid_until=2026-04-20)" }
    ]
  }
};

function initHeroWorkbench() {
  const frame = document.getElementById("heroWorkbench");
  if (!frame) return;

  const pills = frame.querySelectorAll("[data-hero-time]");
  const fxEl = document.getElementById("heroFxExpr");
  const merkleEl = document.getElementById("heroMerkle");
  const budgetTxtEl = document.getElementById("heroBudgetText");
  const budgetFillEl = document.getElementById("heroBudgetFill");
  const suppressedEl = document.getElementById("heroSuppressedBadge");
  const compiledListEl = document.getElementById("heroCompiledList");
  const graphSvgEl = document.getElementById("heroGraphSvg");

  function renderState(key) {
    const s = HERO_STATES[key] || HERO_STATES.t4;
    pills.forEach((p) => p.classList.toggle("active", p.getAttribute("data-hero-time") === key));
    if (fxEl) fxEl.textContent = s.fx;
    if (merkleEl) merkleEl.textContent = s.merkle;
    const pct = Math.round((s.usedTok / s.maxTok) * 100);
    if (budgetTxtEl) budgetTxtEl.textContent = `${s.usedTok} / ${s.maxTok} tokens (${pct}%)`;
    if (budgetFillEl) budgetFillEl.style.width = `${pct}%`;
    if (suppressedEl) {
      suppressedEl.textContent = `${s.suppressed} Stale Facts Suppressed (0% leak)`;
      suppressedEl.className = s.suppressed > 0 ? "pill-tag" : "pill-tag cyan";
    }
    if (compiledListEl) {
      compiledListEl.innerHTML = s.compiledRows.map((r) => `<div class="compiled-row ${r.cls}">${esc(r.text)}</div>`).join("");
    }
    if (graphSvgEl) {
      const legacyOpacity = s.isMigrated ? "0.38" : "1";
      const legacyStroke = s.isMigrated ? "#f59e0b" : "#10b981";
      const legacyDash = s.isMigrated ? 'stroke-dasharray="5 4"' : "";
      const newOpacity = s.isMigrated ? "1" : "0.18";
      const ledgerOpacity = s.hasLedger ? "1" : "0.25";

      graphSvgEl.innerHTML = `
        <defs>
          <marker id="arrGreen" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#10b981"/>
          </marker>
          <marker id="arrAmber" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#f59e0b"/>
          </marker>
          <marker id="arrCyan" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#38bdf8"/>
          </marker>
        </defs>
        <!-- Edges -->
        <line x1="250" y1="118" x2="430" y2="52" stroke="${legacyStroke}" stroke-width="2" ${legacyDash} opacity="${legacyOpacity}" marker-end="url(#${s.isMigrated ? "arrAmber" : "arrGreen"})"/>
        <text x="342" y="72" text-anchor="middle" fill="${s.isMigrated ? "#fbbf24" : "#94a3b8"}" font-size="10" font-family="JetBrains Mono, monospace" opacity="${legacyOpacity}">${s.isMigrated ? "superseded_by v2" : "uses_token_format"}</text>

        <line x1="250" y1="138" x2="430" y2="138" stroke="#10b981" stroke-width="2.5" opacity="${newOpacity}" marker-end="url(#arrGreen)"/>
        <text x="342" y="130" text-anchor="middle" fill="#34d399" font-size="10" font-family="JetBrains Mono, monospace" opacity="${newOpacity}">uses_token_format</text>

        <line x1="175" y1="168" x2="175" y2="214" stroke="#38bdf8" stroke-width="2" opacity="${ledgerOpacity}" marker-end="url(#arrCyan)"/>
        <text x="255" y="196" text-anchor="middle" fill="#38bdf8" font-size="10" font-family="JetBrains Mono, monospace" opacity="${ledgerOpacity}">verifies_caller_via</text>

        <!-- Nodes -->
        <g transform="translate(88, 102)">
          <rect width="162" height="62" rx="12" fill="#101a24" stroke="#10b981" stroke-width="2"/>
          <text x="81" y="26" text-anchor="middle" fill="#f8fafc" font-size="13" font-weight="700" font-family="JetBrains Mono, monospace">auth_service</text>
          <text x="81" y="45" text-anchor="middle" fill="#34d399" font-size="10" font-family="JetBrains Mono, monospace">entity · service</text>
        </g>

        <g transform="translate(436, 22)" opacity="${legacyOpacity}">
          <rect width="194" height="56" rx="11" fill="#181410" stroke="${legacyStroke}" stroke-width="1.6" ${legacyDash}/>
          <text x="97" y="24" text-anchor="middle" fill="${s.isMigrated ? "#fbbf24" : "#f8fafc"}" font-size="12" font-weight="700" font-family="JetBrains Mono, monospace">${s.isMigrated ? "JWT_HS256 (STALE)" : "JWT_HS256 (ACTIVE)"}</text>
          <text x="97" y="42" text-anchor="middle" fill="#94a3b8" font-size="9.5" font-family="JetBrains Mono, monospace">${s.isMigrated ? "valid_until: 2026-04-20" : "HMAC_SHA256_SHARED"}</text>
        </g>

        <g transform="translate(436, 108)" opacity="${newOpacity}">
          <rect width="194" height="58" rx="11" fill="#0b1f19" stroke="#10b981" stroke-width="2"/>
          <text x="97" y="25" text-anchor="middle" fill="#34d399" font-size="12" font-weight="700" font-family="JetBrains Mono, monospace">PASETO_v4_public</text>
          <text x="97" y="43" text-anchor="middle" fill="#cbd5e1" font-size="9.5" font-family="JetBrains Mono, monospace">Ed25519 · ACTIVE HEAD</text>
        </g>

        <g transform="translate(80, 218)" opacity="${ledgerOpacity}">
          <rect width="260" height="54" rx="11" fill="#0e1824" stroke="#38bdf8" stroke-width="1.8"/>
          <text x="130" y="23" text-anchor="middle" fill="#38bdf8" font-size="12" font-weight="700" font-family="JetBrains Mono, monospace">payment_ledger</text>
          <text x="130" y="40" text-anchor="middle" fill="#94a3b8" font-size="9" font-family="JetBrains Mono, monospace">SERIALIZABLE_WITH_IDEMPOTENCY_KEY</text>
        </g>

        <g transform="translate(436, 218)" opacity="${ledgerOpacity}">
          <rect width="194" height="54" rx="11" fill="#131926" stroke="#818cf8" stroke-width="1.6"/>
          <text x="97" y="23" text-anchor="middle" fill="#c7d2fe" font-size="12" font-weight="700" font-family="JetBrains Mono, monospace">order_repository</text>
          <text x="97" y="40" text-anchor="middle" fill="#94a3b8" font-size="9.5" font-family="JetBrains Mono, monospace">2-hop neighbor · BUG-042</text>
        </g>
        <line x1="342" y1="245" x2="430" y2="245" stroke="#818cf8" stroke-width="1.8" stroke-dasharray="4 3" opacity="${ledgerOpacity}"/>
      `;
    }
  }

  pills.forEach((p) => p.addEventListener("click", () => renderState(p.getAttribute("data-hero-time"))));
  renderState("t4");
}

/* ---------------- Bi-Temporal Audit & Studio Presets ---------------- */
const STUDIO_PRESETS = {
  supersession: {
    name: "Auth Token Supersession & Polarity Conflict",
    query: "auth_service signing key and token validation invariant",
    asOf: "2026-03-15",
    facts: [
      { id: "f1", subject: "auth_service", predicate: "uses_token_format", object: "JWT_HS256", valid_from: "2026-01-10", valid_until: "2026-02-18", superseded_by: "f2", confidence: 0.94 },
      { id: "f2", subject: "auth_service", predicate: "uses_token_format", object: "PASETO_v4_public", valid_from: "2026-02-18", valid_until: null, superseded_by: null, confidence: 1.0 },
      { id: "f3", subject: "auth_service", predicate: "signing_primitive", object: "HMAC_SHA256_SHARED_SECRET", valid_from: "2026-01-10", valid_until: "2026-02-18", superseded_by: "f4", confidence: 0.91 },
      { id: "f4", subject: "auth_service", predicate: "signing_primitive", object: "Ed25519_Asymmetric_Keypair", valid_from: "2026-02-18", valid_until: null, superseded_by: null, confidence: 1.0 },
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
  },
  migration: {
    name: "Multi-Agent Postgres & Cache Migration",
    query: "order_repository database_engine and cache_policy",
    asOf: "2026-04-25",
    facts: [
      { id: "m1", subject: "order_repository", predicate: "db_engine", object: "sqlite_local", valid_from: "2026-01-05", valid_until: "2026-03-01", superseded_by: "m2", confidence: 0.9 },
      { id: "m2", subject: "order_repository", predicate: "database_engine", object: "postgres_16_serializable", valid_from: "2026-03-01", valid_until: null, superseded_by: null, confidence: 1.0 },
      { id: "m3", subject: "order_repository", predicate: "cache_mode", object: "mutable", valid_from: "2026-02-10", valid_until: null, superseded_by: null, confidence: 0.72 },
      { id: "m4", subject: "order_repository", predicate: "cache_mode", object: "immutable", valid_from: "2026-04-12", valid_until: null, superseded_by: null, confidence: 0.99 }
    ]
  }
};

const ANTONYMS = [
  ["stateful", "stateless"],
  ["enabled", "disabled"],
  ["encrypted", "plaintext"],
  ["synchronous", "asynchronous"],
  ["mutable", "immutable"],
  ["persistent", "ephemeral"],
  ["true", "false"]
];

const PRED_SYNONYMS = {
  auth_token: "token_format",
  token_type: "token_format",
  isolation: "isolation_level",
  db_engine: "database_engine",
  storage_engine: "database_engine",
  signing_key: "signing_primitive",
  signing_algorithm: "signing_primitive"
};

function canonicalPred(pred) {
  let p = String(pred)
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, "_")
    .replace(/^(does_not_|do_not_|must_not_|cannot_|never_|not_|no_|non_|disallows_|forbids_|prohibits_)/, "")
    .replace(/^(uses_|use_|requires_|require_|enforces_|enforce_)/, "")
    .replace(/_level$/, "");
  return PRED_SYNONYMS[p] || p;
}

function isNegated(pred, obj) {
  const p = String(pred).toLowerCase();
  const o = String(obj).toLowerCase();
  return /^(does_not_|do_not_|must_not_|cannot_|never_|not_|no_|non_|disallows_|forbids_|prohibits_)/.test(p)
    || ["false", "disabled", "no", "none", "forbidden", "prohibited"].includes(o);
}

function auditFactsJS(facts, asOf, autoResolve) {
  const visible = facts.filter((f) => f.valid_from <= asOf && (!f.valid_until || f.valid_until > asOf));
  const active = visible.filter((f) => !f.superseded_by || facts.every((other) => other.id !== f.superseded_by || other.valid_from > asOf));
  const superseded = facts.filter((f) => (f.superseded_by && facts.some((o) => o.id === f.superseded_by && o.valid_from <= asOf)) || (f.valid_until && f.valid_until <= asOf));
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
  return { visible, active: finalActive, superseded: [...superseded, ...active.filter((f) => resolvedIds.has(f.id))], conflicts, resolvedIds };
}

function initHomePage() {
  const btns = document.querySelectorAll("[data-home-preset]");
  const out = document.getElementById("quickSampleOut");
  if (!btns.length || !out) return;

  function renderPreset(key) {
    btns.forEach((b) => b.classList.toggle("active", b.getAttribute("data-home-preset") === key));
    const preset = STUDIO_PRESETS[key] || STUDIO_PRESETS.supersession;
    const res = auditFactsJS(preset.facts, preset.asOf, false);
    const conflictHtml = res.conflicts.length
      ? res.conflicts.map((c) => `
          <div class="finding-item critical">
            <div class="finding-head">
              <strong>${esc(c.subject)}.${esc(c.predicate)}</strong>
              <span class="pill-tag danger">${esc(c.severity)} · ${esc(c.kind)}</span>
            </div>
            <p style="margin:0;font-size:0.84rem;color:var(--muted);">
              <code>${esc(c.a.predicate)}=${esc(c.a.object)}</code> vs <code>${esc(c.b.predicate)}=${esc(c.b.object)}</code>
            </p>
          </div>
        `).join("")
      : `<div class="finding-item pass">
           <div class="finding-head">
             <strong>${esc(preset.name)}</strong>
             <span class="pill-tag">0 Contradictions · Merkle Verified</span>
           </div>
           <p style="margin:0;font-size:0.84rem;color:var(--muted);">All ${res.active.length} active facts cleanly grounded across 2-hop relations.</p>
         </div>`;

    out.innerHTML = `
      <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;">
        <span class="pill-tag">${res.active.length} Active Facts</span>
        <span class="pill-tag amber">${res.superseded.length} Stale Suppressed (100%)</span>
        <span class="pill-tag cyan">Query: ${esc(preset.query)}</span>
      </div>
      ${conflictHtml}
    `;
  }

  btns.forEach((b) => b.addEventListener("click", () => renderPreset(b.getAttribute("data-home-preset"))));
  renderPreset("supersession");
}

/* ---------------- Full Bi-Temporal Studio ---------------- */
function initStudioPage() {
  const chips = document.querySelectorAll("[data-preset]");
  const queryEl = document.getElementById("studioQuery");
  const asOfEl = document.getElementById("studioAsOf");
  const budgetEl = document.getElementById("studioBudget");
  const budgetReadout = document.getElementById("studioBudgetVal");
  const autoResolveEl = document.getElementById("studioAutoResolve");
  const factsJsonEl = document.getElementById("studioFactsJson");
  const runBtn = document.getElementById("studioRunBtn");
  const addConflictBtn = document.getElementById("studioAddConflictBtn");
  const outputEl = document.getElementById("studioOutput");
  const compiledMdEl = document.getElementById("studioCompiledMd");
  const truthGateOut = document.getElementById("studioTruthGateOut");
  const svgTopologyEl = document.getElementById("studioGraphSvg");
  const tabBtns = document.querySelectorAll("[data-studio-tab]");
  const tabPanes = document.querySelectorAll("[data-studio-pane]");
  if (!factsJsonEl || !outputEl) return;

  let activePreset = "supersession";

  tabBtns.forEach((b) => {
    b.addEventListener("click", () => {
      const target = b.getAttribute("data-studio-tab");
      tabBtns.forEach((x) => x.classList.toggle("active", x.getAttribute("data-studio-tab") === target));
      tabPanes.forEach((p) => {
        p.style.display = p.getAttribute("data-studio-pane") === target ? "block" : "none";
      });
    });
  });

  function renderStudioTopology(res) {
    if (!svgTopologyEl) return;
    const allFacts = [...res.active.slice(0, 6), ...res.superseded.slice(0, 3)];
    if (!allFacts.length) {
      svgTopologyEl.innerHTML = `<text x="300" y="100" text-anchor="middle" fill="#94a3b8" font-size="12" font-family="JetBrains Mono">No facts visible at selected as_of timestamp</text>`;
      return;
    }
    const conflictIds = new Set();
    res.conflicts.forEach((c) => {
      conflictIds.add(c.a.id);
      conflictIds.add(c.b.id);
    });

    const rows = allFacts.map((f, idx) => {
      const y = 26 + idx * 32;
      const isSuperseded = res.superseded.some((s) => s.id === f.id);
      const isConflict = conflictIds.has(f.id) && !isSuperseded;
      const stroke = isConflict ? "#ef4444" : isSuperseded ? "#f59e0b" : "#10b981";
      const dash = isSuperseded ? 'stroke-dasharray="4 3"' : "";
      const opacity = isSuperseded ? "0.52" : "1";
      const statusTxt = isConflict ? "CONFLICT" : isSuperseded ? "SUPERSEDED" : "ACTIVE";
      return `
        <g opacity="${opacity}">
          <rect x="12" y="${y - 16}" width="132" height="24" rx="6" fill="#101824" stroke="#38bdf8" stroke-width="1.2"/>
          <text x="78" y="${y}" text-anchor="middle" fill="#e2e8f0" font-size="10.5" font-family="JetBrains Mono">${esc(f.subject.slice(0, 17))}</text>
          <line x1="146" y1="${y - 4}" x2="296" y2="${y - 4}" stroke="${stroke}" stroke-width="1.8" ${dash}/>
          <text x="221" y="${y - 8}" text-anchor="middle" fill="${stroke}" font-size="9.5" font-family="JetBrains Mono">${esc(f.predicate.slice(0, 22))}</text>
          <rect x="298" y="${y - 16}" width="196" height="24" rx="6" fill="#0d151d" stroke="${stroke}" stroke-width="1.4" ${dash}/>
          <text x="396" y="${y}" text-anchor="middle" fill="#f8fafc" font-size="10.5" font-family="JetBrains Mono">${esc(String(f.object).slice(0, 25))}</text>
          <text x="506" y="${y}" fill="${stroke}" font-size="9.5" font-weight="700" font-family="JetBrains Mono">${statusTxt}</text>
        </g>
      `;
    }).join("");
    const h = Math.max(140, 34 + allFacts.length * 32);
    svgTopologyEl.setAttribute("viewBox", `0 0 600 ${h}`);
    svgTopologyEl.innerHTML = rows;
  }

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
      outputEl.innerHTML = `<div class="finding-item critical"><strong>Invalid JSON</strong><p style="margin:4px 0 0;font-size:0.85rem;">${esc(err.message)}</p></div>`;
      return;
    }

    const asOf = asOfEl ? asOfEl.value : "2026-03-15";
    const budget = budgetEl ? Number(budgetEl.value) : 320;
    if (budgetReadout) budgetReadout.textContent = `${budget} tok`;
    const autoResolve = autoResolveEl ? autoResolveEl.checked : false;
    const res = auditFactsJS(parsedFacts, asOf, autoResolve);

    renderStudioTopology(res);

    const statusBadge = res.conflicts.length === 0
      ? `<span class="studio-badge-pill">Clean Graph · 0 Conflicts</span>`
      : autoResolve
        ? `<span class="studio-badge-pill">Auto-Resolved ${res.conflicts.length} Conflict(s)</span>`
        : `<span class="studio-badge-pill coral">${res.conflicts.length} Active Contradiction(s)</span>`;

    const conflictCards = res.conflicts.map((c) => `
      <div class="finding-item critical">
        <div class="finding-head">
          <strong>${esc(c.subject)}.${esc(c.predicate)}</strong>
          <span class="pill-tag danger">${esc(c.severity)} · ${esc(c.kind)}</span>
        </div>
        <p style="margin:4px 0 0;font-size:0.84rem;color:var(--muted);">
          Conflict between <code>${esc(c.a.predicate)}=${esc(c.a.object)}</code> (conf ${c.a.confidence}) and <code>${esc(c.b.predicate)}=${esc(c.b.object)}</code> (conf ${c.b.confidence}).
          ${autoResolve ? `Superseded <code>${esc(c.loser.id)}</code> in favor of <code>${esc(c.winner.id)}</code>.` : "Enable auto_resolve=True to supersede the older or lower-confidence fact."}
        </p>
      </div>
    `).join("");

    const activeCards = res.active.map((f) => `
      <div class="finding-item pass">
        <div class="finding-head">
          <code>${esc(f.subject)} --[${esc(f.predicate)}]--> ${esc(f.object)}</code>
          <span class="pill-tag">Active · conf ${f.confidence}</span>
        </div>
        <p style="margin:4px 0 0;font-size:0.79rem;color:var(--muted);">valid_from=${esc(f.valid_from)} · stale_suppressed=${res.superseded.length}</p>
      </div>
    `).join("");

    const usedTokens = Math.min(budget, Math.max(48, res.active.length * 46));
    const pct = Math.min(100, Math.round((usedTokens / Math.max(1, budget)) * 100));
    outputEl.innerHTML = `
      <div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;margin-bottom:12px;">
        ${statusBadge}
        <span style="font-size:0.82rem;color:var(--muted);">Budget: <strong>${usedTokens}/${budget} tok (${pct}%)</strong> · Stale Suppressed: <strong>${res.superseded.length}</strong></span>
      </div>
      ${conflictCards}
      ${activeCards || "<p style='color:var(--muted);'>No facts visible at this timestamp.</p>"}
    `;

    if (compiledMdEl) {
      const q = queryEl ? queryEl.value : "";
      const lines = [
        `## Cortex-MCP Compiled Context (query: \`${q}\` | as_of: ${asOf})`,
        `# Budget: ${usedTokens}/${budget} tokens (${pct}%) | Suppressed Stale Facts: ${res.superseded.length}`,
        "",
        ...res.active.map((f) => `- [FACT:${f.id}] \`${f.subject}\` --(${f.predicate})--> \`${f.object}\` (valid_from=${f.valid_from}, conf=${f.confidence})`)
      ];
      compiledMdEl.textContent = lines.join("\n");
    }

    if (truthGateOut) {
      const docs = res.active.slice(0, 4).map((f) => ({
        source_id: f.id,
        title: `Bi-Temporal Fact ${f.id}: ${f.subject}.${f.predicate}`,
        content: `${f.subject} ${f.predicate} is ${f.object}.`,
        metadata: {
          item_type: "fact",
          fact_id: f.id,
          valid_from: f.valid_from,
          is_active: true,
          graph_merkle_digest: "e893bf67424f995283813e265a227224...",
          preset: activePreset
        }
      }));
      truthGateOut.textContent = JSON.stringify(docs, null, 2);
    }
  }

  chips.forEach((chip) => chip.addEventListener("click", () => loadPreset(chip.getAttribute("data-preset"))));
  if (runBtn) runBtn.addEventListener("click", runAudit);
  if (asOfEl) asOfEl.addEventListener("change", runAudit);
  if (budgetEl) budgetEl.addEventListener("input", runAudit);
  if (autoResolveEl) autoResolveEl.addEventListener("change", runAudit);
  if (addConflictBtn) {
    addConflictBtn.addEventListener("click", () => {
      try {
        const arr = JSON.parse(factsJsonEl.value);
        arr.push({
          id: `f_drift_${arr.length + 1}`,
          subject: arr[0]?.subject || "auth_service",
          predicate: "encryption_mode",
          object: "plaintext",
          valid_from: asOfEl?.value || "2026-03-15",
          valid_until: null,
          superseded_by: null,
          confidence: 0.55
        });
        arr.push({
          id: `f_drift_${arr.length + 1}`,
          subject: arr[0]?.subject || "auth_service",
          predicate: "encryption_mode",
          object: "encrypted",
          valid_from: asOfEl?.value || "2026-03-15",
          valid_until: null,
          superseded_by: null,
          confidence: 0.99
        });
        factsJsonEl.value = JSON.stringify(arr, null, 2);
        runAudit();
        showToast("Injected antonym conflict pair");
      } catch (_) {
        showToast("Fix JSON syntax before injecting");
      }
    });
  }

  loadPreset("supersession");
}

/* ---------------- Rules & MCP Tools Filter ---------------- */
function initRulesPage() {
  const searchInput = document.getElementById("rulesSearch");
  const catBtns = document.querySelectorAll("[data-rule-cat]");
  const cards = document.querySelectorAll("[data-rule-card]");
  const countEl = document.getElementById("rulesCount");
  if (!searchInput || !cards.length) return;

  let activeCat = "all";

  function filterRules() {
    const q = searchInput.value.trim().toLowerCase();
    let shown = 0;
    cards.forEach((card) => {
      const cardCat = card.getAttribute("data-cat") || "";
      const text = card.textContent.toLowerCase();
      const match = (activeCat === "all" || cardCat === activeCat) && (!q || text.includes(q));
      card.style.display = match ? "" : "none";
      if (match) shown++;
    });
    if (countEl) countEl.textContent = `Showing ${shown} of ${cards.length} protocol specifications`;
  }

  catBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      activeCat = btn.getAttribute("data-rule-cat");
      catBtns.forEach((b) => b.classList.toggle("active", b.getAttribute("data-rule-cat") === activeCat));
      filterRules();
    });
  });

  searchInput.addEventListener("input", filterRules);
  filterRules();
}

/* ---------------- Docs Scroll-Spy & Tab Switchers ---------------- */
function initDocsScrollSpy() {
  const headings = document.querySelectorAll(".docs-article h2[id], .docs-article h3[id]");
  const tocLinks = document.querySelectorAll(".toc-links a, .docs-tree a");
  if (!headings.length || !tocLinks.length || !("IntersectionObserver" in window)) return;

  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        const id = entry.target.getAttribute("id");
        tocLinks.forEach((link) => {
          link.classList.toggle("active", link.getAttribute("href") === `#${id}`);
        });
      }
    }
  }, { rootMargin: "-84px 0px -65% 0px", threshold: 0.05 });

  headings.forEach((h) => observer.observe(h));
}

function initGenericTabs() {
  document.querySelectorAll("[data-tab-group]").forEach((group) => {
    const btns = group.querySelectorAll("[data-tab-target]");
    const panes = group.querySelectorAll("[data-tab-pane]");
    btns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = btn.getAttribute("data-tab-target");
        btns.forEach((b) => b.classList.toggle("active", b.getAttribute("data-tab-target") === target));
        panes.forEach((p) => {
          p.style.display = p.getAttribute("data-tab-pane") === target ? "block" : "none";
        });
      });
    });
  });
}

/* ---------------- Global Click Handlers ---------------- */
document.addEventListener("click", (e) => {
  const copyBtn = e.target.closest("[data-copy]");
  if (copyBtn) {
    copyText(copyBtn.getAttribute("data-copy"), copyBtn);
    return;
  }
  const targetCopyBtn = e.target.closest("[data-copy-target]");
  if (targetCopyBtn) {
    const targetEl = document.getElementById(targetCopyBtn.getAttribute("data-copy-target"));
    if (targetEl) copyText(targetEl.textContent, targetCopyBtn);
  }
});

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initMobileMenu();
  initCommandSearch();
  initClientSwitchers();
  initHeroWorkbench();
  initHomePage();
  initStudioPage();
  initRulesPage();
  initDocsScrollSpy();
  initGenericTabs();
});
