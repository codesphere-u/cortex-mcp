# Cortex-MCP (`cortex-mcp`)

[![CI](https://github.com/codesphere-u/cortex-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/codesphere-u/cortex-mcp/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![MCP Spec](https://img.shields.io/badge/MCP-JSON--RPC%202.0-7c3aed.svg)](https://modelcontextprotocol.io/)
[![Zero Cloud Dependencies](https://img.shields.io/badge/dependencies-zero%20external%20runtime-10b981.svg)](#architecture)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Local-First Bi-Temporal Knowledge Graph, Cross-Agent Persistent Memory & Token-Budgeted Context Compiler MCP Server for AI Coding Agents.**

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

## Connect to Claude Code / Cursor / Windsurf / Antigravity (`mcp_config.json`)

Add `cortex-mcp` to your agent's `mcp_config.json` (or `.cursor/mcp.json` / `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "cortex-mcp": {
      "command": "python3",
      "args": [
        "-m",
        "cortex_mcp.cli",
        "serve-stdio",
        "--storage",
        ".cortex/memory_graph.json"
      ]
    }
  }
}
```

### Exposed MCP Tools (`tools/list`)

| Tool Name | Purpose |
| :--- | :--- |
| `memory_record_episode` | Record an immutable engineering episode (`adr`, `bug_root_cause`, `invariant`, `session_note`, `migration`, `incident`) with touched files and mentioned entities. |
| `memory_upsert_fact` | Record a directed `(subject_id, predicate, object)` fact with automatic bi-temporal conflict detection and supersession when `singular=True`. |
| `memory_compile_context` | Compile a provenance-cited, token-budgeted context bundle (`max_tokens`) using hybrid BM25 + 2-hop graph spreading activation. |
| `memory_query_entity` | Inspect an entity's active facts, superseded historical facts, related episodes, and K-hop ego-graph neighborhood. |
| `memory_time_travel` | Query the entire knowledge graph as of any historical ISO-8601 UTC timestamp (`as_of`). |
| `memory_verify_integrity` | Verify canonical SHA-256 hashes across all facts and episodes and compute the graph Merkle root digest. |

### Exposed MCP Resources & Prompts

- **Resources (`resources/list`, `resources/read`)**:
  - `cortex://graph/summary`: Entity, active fact, superseded fact, and episode counts + Merkle digest.
  - `cortex://graph/integrity`: Full cryptographic verification report.
  - `cortex://episodes/recent`: The 20 most recent engineering episodes.
- **Prompts (`prompts/list`, `prompts/get`)**:
  - `architecture-briefing`: Compiles a verified architectural briefing for a target `component`.
  - `bug-investigation-context`: Compiles active invariants and historical root causes for a bug `symptom`.

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

All **67 tests** validate bi-temporal supersession chains, point-in-time queries, K-hop graph traversal, token-budget compliance, cryptographic tamper detection, JSON-RPC 2.0 MCP protocol compliance, and CLI subcommands.

---

## License

MIT License — Copyright (c) 2026 [Akandwanaho Ivan Alvin](https://github.com/codesphere-u).
