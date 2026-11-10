# Cortex-MCP (`cortex-mcp`)

[![CI](https://github.com/codesphere-u/cortex-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/codesphere-u/cortex-mcp/actions/workflows/ci.yml)
[![Release v1.1.0](https://img.shields.io/badge/release-v1.1.0-blue.svg)](https://github.com/codesphere-u/cortex-mcp/releases/tag/v1.1.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![MCP Spec](https://img.shields.io/badge/MCP-2024--11--05-7c3aed.svg)](https://modelcontextprotocol.io/)
[![Vercel Deployment](https://img.shields.io/badge/Vercel-Operational-10b981?logo=vercel&logoColor=white)](https://cortex-mcp-steel.vercel.app/mcp)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-✔%20Connected-10b981?logo=anthropic&logoColor=white)](#connect-to-claude-code--cursor--windsurf--antigravity)
[![Glama Score](https://glama.ai/mcp/servers/codesphere-u/cortex-mcp/badges/score.svg)](https://glama.ai/mcp/servers/codesphere-u/cortex-mcp)
[![Smithery Ready](https://img.shields.io/badge/Smithery-Ready-purple)](smithery.yaml)
[![Tests Passed](https://img.shields.io/badge/tests-91%20passed-brightgreen.svg)](tests/)
[![Zero Cloud Dependencies](https://img.shields.io/badge/dependencies-zero%20external%20runtime-10b981.svg)](#architecture)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Local-First Bi-Temporal Knowledge Graph, Cross-Agent Persistent Memory, Contradiction Auditor, `TruthGate` Citation Bundle Exporter & Token-Budgeted Context Compiler MCP Server for AI Coding Agents.**

> 🚀 **Live Interactive Developer Portal & Playground:** Visit [`https://cortex-mcp-steel.vercel.app`](https://cortex-mcp-steel.vercel.app) in your web browser to test tools live, inspect schemas, and copy 1-click configurations for Claude Code, Cursor, Windsurf, and Claude Desktop.

<p align="center">
  <a href="https://glama.ai/mcp/servers/codesphere-u/cortex-mcp">
    <img src="https://glama.ai/mcp/servers/codesphere-u/cortex-mcp/badges/card.svg" alt="cortex-mcp MCP server – quality and maintenance score on Glama" width="500" />
  </a>
</p>

---

## Why `cortex-mcp` Exists

Modern AI coding agents (**Claude Code**, **Cursor**, **Windsurf**, **Antigravity**, **LangGraph**) suffer from two compounding failure modes across multi-session engineering workflows:

1. **Cross-Session & Cross-Agent Context Amnesia**: Architectural decisions (ADRs), subtle bug root causes, and module invariants discovered in one session vanish when a developer switches sessions or tools.
2. **Stale Context Bloat**: Static `.cursorrules`, `CLAUDE.md`, or append-only vector stores accumulate contradictory facts as systems evolve (e.g., an old note saying `auth_service` uses `JWT_HS256` alongside a newer note saying it migrated to `PASETO_v4`). Stuffing both into the prompt wastes tokens and causes hallucinated regressions.

`cortex-mcp` solves both problems deterministically with **zero external API keys** and **zero cloud dependencies**:
- **Bi-Temporal Knowledge Graph (`BiTemporalMemoryGraph`)**: Tracks `Entities`, `TemporalFacts`, and `Episodes` with automatic conflict detection and temporal supersession (`valid_from`, `valid_until`, `superseded_by`). When an architectural fact changes, the old fact is retired into historical lineage rather than polluting active context.
- **Hybrid BM25 + 2-Hop Graph Spreading Activation (`ContextCompiler`)**: Ranks active facts, ADRs, bug root causes, and file invariants using Okapi BM25 lexical scoring, exact code-identifier boosting, and K-hop graph activation, then packs the highest-utility items into a strict `max_tokens` budget with `100%` stale-fact suppression.
- **Standards-Compliant JSON-RPC 2.0 MCP Server (`CortexMCPServer`)**: Exposes tools, resources, and prompts over `stdio` or in-memory transport for immediate integration with any MCP client.

---

## System Architecture

```text
+-----------------------------------------------------------------------------------+
|                AI Coding Agents (Claude Code / Cursor / Windsurf / AGY)           |
+-----------------------------------------+-----------------------------------------+
                                          |
                        JSON-RPC 2.0 over stdio / in-memory
                    (initialize, tools/call, resources/read, prompts/get)
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                           CortexMCPServer (server.py)                             |
|  Tools:                                                                           |
|   - memory_record_episode     - memory_query_entity                               |
|   - memory_upsert_fact        - memory_time_travel                                |
|   - memory_compile_context    - memory_verify_integrity                           |
+-------------------+-------------------------------------------+-------------------+
                    |                                           |
                    v                                           v
+---------------------------------------+   +---------------------------------------+
|   BiTemporalMemoryGraph (graph.py)    |   |      ContextCompiler (compiler.py)    |
|                                       |   |                                       |
| * Entities (service, module, ...)     |   | * Code-Aware Tokenizer (snake/Camel)  |
| * TemporalFacts (valid_from/until,    |   | * Okapi BM25 Lexical Scoring          |
|   singular conflict supersession)     |   | * 2-Hop Graph Spreading Activation    |
| * Episodes (ADR, bug_root_cause,      |   | * Stale-Fact Filter (valid_until=None)|
|   invariant, migration, incident)     |   | * Greedy Utility-Density Knapsack     |
| * Point-in-Time Snapshot & K-Hop BFS  |   |   Packing under strict `max_tokens`   |
| * SHA-256 Hashes + Graph Merkle Root  |   | * Provenance Citations (@sha256:...)  |
+-------------------+-------------------+   +---------------------------------------+
                    |
                    v
+---------------------------------------+
| Atomic JSON Snapshot Persistence      |
| (~/.cortex-mcp/memory.json)           |
+---------------------------------------+
```

---

## Install

```bash
pip install "git+https://github.com/codesphere-u/cortex-mcp.git@v1.1.0"
# After the first PyPI release: pip install cortex-bitemporal-mcp  (installs the `cortex-mcp` CLI; import name: cortex_mcp)
cortex-mcp --help
```

> The PyPI name `cortex-mcp` belongs to an unrelated project, so this package is published as `cortex-bitemporal-mcp`. The GitHub repository and CLI keep the `cortex-mcp` name.

## Quickstart

### 1. Installation

```bash
git clone https://github.com/codesphere-u/cortex-mcp.git
cd cortex-mcp
pip install -e ".[dev]"
```

### 2. Run the Multi-Session Engineering Demo

```bash
python -m cortex_mcp.cli demo
```

Sample output demonstrating automatic supersession of `JWT_HS256` by `PASETO_v4_public`, point-in-time historical inspection, and token-budgeted context compilation:

```text
==============================================================================
 CORTEX-MCP: BI-TEMPORAL KNOWLEDGE GRAPH & CONTEXT COMPILER DEMO
==============================================================================
Entities tracked      : 3
Active temporal facts : 6
Superseded stale facts: 2 (automatically retired)
Engineering episodes  : 4
SHA-256 Merkle Digest : e893bf67424f995283813e265a227224...
------------------------------------------------------------------------------
[Time-Travel Inspection @ 2026-02-01T00:00:00Z (Pre-PASETO Migration)]
  * auth_service --(uses_token_format)--> JWT_HS256
  * auth_service --(signing_primitive)--> HMAC_SHA256_SHARED_SECRET
------------------------------------------------------------------------------
[Compiled Active Context | Budget: 307/320 tokens (95.9%) | Suppressed Stale Facts: 2]
## Cortex-MCP Compiled Context (query: `auth_service token format signing_primitive and payment_ledger idempotency invariant`)
- [FACT:fact_auth_key_v2] `auth_service` --(signing_primitive)--> `Ed25519_Asymmetric_Keypair` (valid_from=2026-04-20T16:45:00+00:00, src=ep_adr_019)
- [FACT:fact_ledger_auth_dep] `payment_ledger` --(verifies_caller_via)--> `auth_service` (valid_from=2026-03-01T11:15:00+00:00, src=ep_inv_007)
- [INVARIANT:ep_inv_007] **INV-007: Payment Ledger Idempotency & Zero-Sum Double Entry** | files: src/payments/ledger.py
  Every mutation in payment_ledger MUST supply a deterministic idempotency_key and balance debit/credit postings to zero in a single SERIALIZABLE transaction.
- [FACT:fact_auth_token_v2] `auth_service` --(uses_token_format)--> `PASETO_v4_public` (valid_from=2026-04-20T16:45:00+00:00, src=ep_adr_019)
- [FACT:fact_ledger_isolation] `payment_ledger` --(requires_isolation_level)--> `SERIALIZABLE_WITH_IDEMPOTENCY_KEY` (valid_from=2026-03-01T11:15:00+00:00, src=ep_inv_007)
- [FACT:fact_order_depends_ledger] `order_repository` --(depends_on)--> `payment_ledger` (valid_from=2026-02-14T14:30:00+00:00, src=ep_bug_042)
==============================================================================
```

---

## Connect to Claude Code / Cursor / Windsurf / Antigravity

### 1. Claude Code CLI (Recommended)
Add Cortex-MCP directly to Claude Code with one command:
```bash
# Project-scoped:
claude mcp add --transport http cortex-mcp https://cortex-mcp-steel.vercel.app/mcp

# Global user-scoped (available across all projects):
claude mcp add --scope user --transport http cortex-mcp https://cortex-mcp-steel.vercel.app/mcp
```

### 2. Cursor / Windsurf / Claude Desktop (`mcp.json`)
Add the hosted HTTP server to `.cursor/mcp.json` or `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "cortex-mcp": {
      "type": "http",
      "url": "https://cortex-mcp-steel.vercel.app/mcp"
    }
  }
}
```

### 3. Smithery Registry (1-Click Install)
```bash
npx -y @smithery/cli install @codesphere-u/cortex-mcp --client claude
```

### 4. Local Stdio via `uvx` (Zero Install)
```json
{
  "mcpServers": {
    "cortex-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/codesphere-u/cortex-mcp.git",
        "cortex-mcp",
        "serve-stdio"
      ]
    }
  }
}
```

### Exposed MCP Tools (`tools/list`) & Detailed Usage Guide

| Tool Name | What is its use? (Purpose) | Key Arguments | Typical Output |
| :--- | :--- | :--- | :--- |
| `memory_record_episode` | Record an immutable engineering episode (`adr`, `bug_root_cause`, `invariant`, `session_note`, `migration`, `incident`) with touched files and mentioned entities. | `title` (str), `category` (enum), `content` (str), `files_touched` (list), `entities_mentioned` (list) | `{"episode": {"id": "ep_...", "sha256": "..."}}` |
| `memory_upsert_fact` | Record a directed `(subject_id, predicate, object)` fact with automatic bi-temporal conflict detection and supersession when `singular=True`. | `subject_id` (str), `predicate` (str), `object_value` (str), `singular` (bool, default `True`) | `{"fact": {"id": "fact_...", "superseded": [...]}}` |
| `memory_compile_context` | Compile a provenance-cited, token-budgeted context bundle (`max_tokens`) using hybrid BM25 + 2-hop graph spreading activation. | `query` (str), `max_tokens` (int, default `1200`), `as_of` (iso8601), `include_superseded` (bool) | `{"markdown": "...", "token_count": 842, "citations": [...]}` |
| `memory_query_entity` | Inspect an entity's active facts, superseded historical facts, related episodes, and K-hop ego-graph neighborhood. | `entity_id` (str), `max_hops` (int, default `2`), `include_superseded` (bool) | `{"entity": "...", "active_facts": [...], "history": [...]}` |
| `memory_time_travel` | Query the entire knowledge graph as of any historical ISO-8601 UTC timestamp (`as_of`). | `as_of` (iso8601 UTC timestamp str) | `{"as_of": "...", "active_facts": [...], "snapshot_hash": "..."}` |
| `memory_verify_integrity` | Verify canonical SHA-256 hashes across all facts and episodes and compute the graph Merkle root digest. | _None_ | `{"verified": true, "fact_count": 12, "merkle_root": "..."}` |
| `cortex_audit_contradictions` | Scan active facts for unresolved logical contradictions (negation polarity inversions, antonym objects, predicate alias collisions, or unsuperseded multi-value drift) with optional `auto_resolve=True`. | `as_of` (optional str), `auto_resolve` (bool, default `False`) | `{"contradiction_count": 0, "findings": [], "auto_resolved": []}` |

#### Tool Usage Examples

##### 1. `memory_upsert_fact` — Recording Architectural Facts with Automatic Supersession
When an AI agent modifies architecture (e.g. changing token signing algorithm from RS256 to Ed25519), calling `memory_upsert_fact` updates the active decision while preserving historical auditability:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "memory_upsert_fact",
    "arguments": {
      "subject_id": "auth_service",
      "predicate": "signing_algorithm",
      "object_value": "Ed25519",
      "singular": true
    }
  }
}
```

##### 2. `memory_compile_context` — Compiling Token-Budgeted Context for Coding Prompts
Before an agent begins a task, compile relevant historical decisions within a strict token budget:
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "memory_compile_context",
    "arguments": {
      "query": "authentication token signing and database transaction isolation",
      "max_tokens": 800
    }
  }
}
```

##### 3. `cortex_audit_contradictions` — Auditing Multi-Agent Fact Drift
Detect if two autonomous agents made conflicting decisions in the same codebase:
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "cortex_audit_contradictions",
    "arguments": {
      "auto_resolve": true
    }
  }
}
```

### `v1.1.0` Features: Contradiction Auditor & `TruthGate` Citation Exporter

```bash
# 1. Audit active facts in the bi-temporal graph for logical/polarity contradictions
cortex-mcp audit-contradictions --json

# 2. Export compiled context packets as a TruthGate-compatible SourceDocument JSON bundle
cortex-mcp export-sources --query "auth_service uses_token_format" --output sources.json
```

```python
from cortex_mcp import audit_contradictions, export_truthgate_sources

# Detect and auto-resolve cross-agent predicate alias or polarity conflicts
report = audit_contradictions(graph, auto_resolve=True)
print(report.summary_markdown)

# Export active facts with temporal provenance & SHA-256 Merkle root for codesphere-u/truthgate
sources = export_truthgate_sources(graph, query="payment_ledger isolation_level")
```

### Exposed MCP Resources (`resources/list`, `resources/read`)

| Resource URI | MIME Type | Purpose / Content Description |
| :--- | :--- | :--- |
| `cortex://graph/summary` | `application/json` | Real-time counts of tracked entities, active temporal facts, superseded historical facts, recorded episodes, and the graph SHA-256 Merkle root. |
| `cortex://graph/integrity` | `application/json` | Full cryptographic integrity report verifying canonical SHA-256 digests across all temporal facts and engineering episodes. |
| `cortex://episodes/recent` | `application/json` | Array of the 20 most recent engineering episodes (ADRs, invariants, bug root causes, migrations) with touched files and entity links. |

### Exposed MCP Prompts (`prompts/list`, `prompts/get`)

| Prompt Name | Purpose / Use Case | Required Arguments | Workflow Output |
| :--- | :--- | :--- | :--- |
| `architecture-briefing` | Guides an LLM agent to assemble a verified architectural briefing for a component. | `component` (string) | Pre-formatted system/user prompts instructing the model to review active facts and ADRs before modifying the component. |
| `bug-investigation-context` | Guides an LLM agent through a structured root-cause investigation for a bug symptom. | `symptom` (string) | Pre-formatted prompt querying active invariants, historical regressions, and touched files to isolate root causes without hallucinating. |

---

## Reproducible Benchmarks

Run the built-in benchmark suite (500 temporal facts, 150 bi-temporal supersessions, 100 episodes, 60 entities):

```bash
python -m cortex_mcp.cli benchmark
```

| Operation | Samples | P50 Latency (ms) | P95 Latency (ms) |
| :--- | ---: | ---: | ---: |
| `record_episode` (SHA-256 + entity indexing) | 100 | 0.003 | 0.005 |
| `upsert_fact` (bi-temporal conflict & supersession) | 500 | 0.003 | 0.004 |
| `traverse_subgraph` (2-hop active ego-graph) | 60 | 0.123 | 0.185 |
| `compile_context` (BM25 + 2-hop activation, 800 tok) | 50 | 4.879 | 5.229 |
| `verify_integrity` (600 SHA-256 hashes + Merkle root) | 1 | 1.412 | 1.412 |

- **Active Facts**: `350` | **Superseded Facts**: `150`
- **Stale-Fact Suppression Rate**: `100.0%` (`0` leaked stale facts across 50 compilation queries)
- **Token-Budget Compliance Rate**: `100.0%` (`0` budget overruns)
- **Cryptographic Integrity Verified**: `True`

---

## Architectural Decision Records (ADRs)

### ADR-01: Bi-Temporal Supersession over Destructive Overwrite or Append-Only RAG
- **Context**: Append-only vector stores return both old and new architectural facts when queried, confusing LLM agents. Destructive overwrites destroy auditability ("why did we stop using `JWT_HS256`?").
- **Decision**: Every `TemporalFact` carries `valid_from`, `valid_until`, and `superseded_by`. Inserting a new `singular=True` fact for `(subject_id, predicate)` atomically closes the prior active fact's validity window (`valid_until = new_fact.valid_from`) and links `superseded_by = new_fact.id`.
- **Consequence**: Active context compilation achieves `100%` stale-fact suppression while `memory_time_travel` and `memory_query_entity` retain complete historical lineage.

### ADR-02: Hybrid BM25 + 2-Hop Spreading Activation over Embedding-Only Retrieval
- **Context**: Dense embeddings frequently miss exact code identifiers (`OrderRepository`, `SERIALIZABLE_WITH_IDEMPOTENCY_KEY`) and fail to retrieve 2-hop architectural dependencies not lexically mentioned in the prompt.
- **Decision**: Combine a code-aware tokenizer (`snake_case`, `CamelCase`, file paths) with Okapi BM25 lexical scoring, exact identifier boosting, and 2-hop graph spreading activation over active edges, followed by greedy utility-density packing under `max_tokens`.
- **Consequence**: Deterministic, sub-5ms context compilation with zero external embedding API latency or cost.

---

## Running the Test Suite

```bash
pytest -v
```

All **100 tests** validate bi-temporal supersession chains, semantic & polarity contradiction auditing, `TruthGate` `SourceDocument` citation bundle export, point-in-time queries, K-hop graph traversal, token-budget compliance, cryptographic tamper detection, JSON-RPC 2.0 MCP protocol compliance, and CLI subcommands.

---

## Hosted endpoint (Vercel)

A free, public, stateless deployment of Cortex MCP runs over **MCP Streamable HTTP**:

| | |
|---|---|
| MCP endpoint | `https://cortex-mcp-steel.vercel.app/mcp` (JSON-RPC 2.0 over `POST`) |
| Health probe | `https://cortex-mcp-steel.vercel.app/health` |

```bash
curl -s -X POST https://cortex-mcp-steel.vercel.app/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Client Configuration

#### 1. Claude Code CLI
Add instantly to your Claude Code workspace or global user profile:
```bash
# Add to current project:
claude mcp add --transport http cortex-mcp https://cortex-mcp-steel.vercel.app/mcp

# Or add globally across all projects:
claude mcp add --scope user --transport http cortex-mcp https://cortex-mcp-steel.vercel.app/mcp
```

#### 2. Claude Desktop / Cursor / Windsurf (`mcp.json`)
```json
{
  "mcpServers": {
    "cortex-mcp": {
      "type": "http",
      "url": "https://cortex-mcp-steel.vercel.app/mcp"
    }
  }
}
```

**Hosted limitations:** All 7 tools are available. State is **in-memory and ephemeral** (per serverless instance, shared by callers) — use the local stdio install for persistent, private memory.

The hosted gateway is [`api/index.py`](api/index.py); it enforces a 1 MB body limit, strict JSON-RPC envelopes and the tool restrictions above. Deploy your own copy with `npx vercel deploy --prod` (entrypoint is configured in `pyproject.toml` under `[tool.vercel]`).

## License

MIT License — Copyright (c) 2026 [Akandwanaho Ivan Alvin](https://github.com/codesphere-u).
