# CLAUDE.md — Cortex-MCP Engineering Guide

## Project Overview
`cortex-mcp` is a zero-dependency, local-first **Bi-Temporal Knowledge Graph, Working Memory & Context Compiler MCP Server** designed for autonomous AI coding agents (Claude Code, Cursor, Windsurf). It tracks architectural decisions (ADRs), module invariants, and bug root causes, automatically superseding conflicting facts while maintaining historical lineage.

* **Package Name (PyPI)**: `cortex-bitemporal-mcp` (CLI entry point: `cortex-mcp`, module: `cortex_mcp`)
* **MCP Specification**: Tripartite support for **Tools**, **Resources**, and **Prompts** (Protocol version `2024-11-05`).
* **Hosted Production**: `https://cortex-mcp-steel.vercel.app/mcp` (Vercel Serverless Streamable HTTP + SSE).
* **Interactive Portal**: `https://cortex-mcp-steel.vercel.app/` (Developer Playground).

---

## Build, Test & Lint Commands

```bash
# Run the complete test suite
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run the built-in reproducible benchmark suite
uv run python -m cortex_mcp.cli benchmark

# Run the multi-session demonstration
uv run python -m cortex_mcp.cli demo

# Build sdist and wheel distributions
uv build

# Run local stdio server
uv run python -m cortex_mcp.cli serve-stdio
```

---

## Architecture & Code Structure

```text
src/cortex_mcp/
├── __init__.py         # Package exports
├── graph.py            # BiTemporalMemoryGraph, Entity, TemporalFact, Episode
├── compiler.py         # ContextCompiler: Okapi BM25 + 2-hop graph activation
├── auditor.py          # Contradiction auditor (polarity, antonyms, alias drift)
├── export_sources.py   # TruthGate-compatible source document bundle exporter
├── server.py           # CortexMCPServer: Model Context Protocol JSON-RPC 2.0 engine
├── http_server.py      # Standard library local HTTP & SSE server
└── cli.py              # CLI commands (demo, benchmark, audit, export, serve-stdio)

api/
├── index.py            # Vercel Serverless FastAPI gateway (rate-limited, sandboxed)
└── portal.py           # Zero-dependency interactive Developer Portal & Playground
```

---

## Model Context Protocol (MCP) Primitives

### 1. Tools (`tools/list`, `tools/call`)
* `memory_record_episode`: Record an immutable engineering episode (`adr`, `bug_root_cause`, `invariant`, `migration`).
* `memory_upsert_fact`: Record a directed `(subject, predicate, object)` fact with automatic bi-temporal supersession.
* `memory_compile_context`: Compile an Okapi BM25 + 2-hop graph context bundle under a strict `max_tokens` budget.
* `memory_query_entity`: Query an entity's active facts, history, and K-hop graph neighborhood.
* `memory_time_travel`: Inspect the entire graph as of a historical UTC timestamp (`as_of`).
* `memory_verify_integrity`: Cryptographically verify SHA-256 hashes across all facts and compute the Merkle root.
* `cortex_audit_contradictions`: Audit active facts for logical contradictions and predicate collisions.

### 2. Resources (`resources/list`, `resources/read`)
* `cortex://graph/summary`: Live counts of entities, facts, episodes, and the graph Merkle digest.
* `cortex://graph/integrity`: Cryptographic SHA-256 verification report.
* `cortex://episodes/recent`: Array of the 20 most recent engineering episodes.

### 3. Prompts (`prompts/list`, `prompts/get`)
* `architecture-briefing`: Assemble verified architectural facts and ADRs before modifying a `component`.
* `bug-investigation-context`: Structured root-cause investigation for a bug `symptom`.

---

## Claude Code Quick-Connect

```bash
# Add to Claude Code project scope:
claude mcp add --transport http cortex-mcp https://cortex-mcp-steel.vercel.app/mcp

# Or user scope (globally across all projects):
claude mcp add --scope user --transport http cortex-mcp https://cortex-mcp-steel.vercel.app/mcp
```
