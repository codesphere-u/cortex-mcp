# Cortex-MCP System Architecture

## 1. Executive Summary

`cortex-mcp` is an open-source, local-first bi-temporal knowledge graph and context compilation engine exposed via the Model Context Protocol (MCP) JSON-RPC 2.0 specification. It solves two critical bottlenecks in multi-session AI coding agent workflows:
1. **Cross-Session Context Amnesia**: Agents lose track of architectural decisions, invariant constraints, and bug root causes when sessions terminate.
2. **Context Bloat & Contradiction**: Static append-only context accumulation fills agent token windows with stale, superseded, or contradictory facts.

By modeling knowledge using bi-temporal semantics (transaction time vs. valid time) and providing deterministic Okapi BM25 ranking coupled with 2-hop graph spreading activation, `cortex-mcp` guarantees that coding agents operate on coherent, verified, token-budgeted memory without relying on remote cloud vector databases.

---

## 2. Architectural Blueprint

```text
+-----------------------------------------------------------------------------------+
|               AI Coding Assistants (Cursor, Claude Code, Windsurf, AGY)           |
+-----------------------------------------+-----------------------------------------+
                                          |
                              JSON-RPC 2.0 via stdio
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                           CortexMCPServer (server.py)                             |
|  Exposed MCP Tools:                                                               |
|   - memory_record_episode     - memory_query_entity      - cortex_audit_contradictions|
|   - memory_upsert_fact        - memory_time_travel       - cortex_export_sources   |
|   - memory_compile_context    - memory_verify_integrity                           |
+-------------------+-------------------------------------------+-------------------+
                    |                                           |
                    v                                           v
+---------------------------------------+   +---------------------------------------+
|   BiTemporalMemoryGraph (graph.py)    |   |      ContextCompiler (compiler.py)    |
|                                       |   |                                       |
| - Entities (id, type, attrs)          |   | - Tokenizer (CamelCase, snake_case)   |
| - TemporalFacts (s, p, o, valid_from, |   | - Okapi BM25 Ranking Engine           |
|                  valid_until,         |   | - 2-Hop Graph Spreading Activation    |
|                  superseded_by)       |   | - Exact Code-Identifier Boosting      |
| - Episodes (adr, invariant, root_cause|   | - Greedy Knapsack Token Packer        |
| - Cryptographic SHA-256 Merkle Chain  |   | - Stale Fact Suppression (100%)       |
| - Contradiction & Antonym Detector    |   | - TruthGate Citation Exporter         |
+-------------------+-------------------+-------------------+-------------------+
                    |                                       |
                    +-------------------+-------------------+
                                        |
                                        v
                    +---------------------------------------+
                    |       Local Atomic Persistence        |
                    |   .cortex/memory.json (Atomic Rename) |
                    |      SHA-256 Checksum Verification    |
                    +---------------------------------------+
```

---

## 3. Core Subsystems

### 3.1 BiTemporalMemoryGraph (`src/cortex_mcp/graph.py`)
- **Entities**: Nodes representing files, services, modules, architectural boundaries, or data models.
- **TemporalFacts**: Directed labeled relations `(Subject, Predicate, Object)` characterized by two temporal dimensions:
  - *Transaction Time*: When the fact was recorded into the graph (`created_at`).
  - *Valid Time*: The period during which the fact holds true in the physical codebase (`valid_from` to `valid_until`).
- **Supersession Engine**: Singular facts (such as framework versions, ports, cryptographic algorithms) automatically supersede previous values. The previous fact's `valid_until` is updated, and its `superseded_by` pointer links to the successor fact.
- **Tamper-Evident Merkle Hashing**: Every state mutation increments a SHA-256 chain ensuring memory integrity across developer environments.

### 3.2 Contradiction Auditor & Resolution
- Normalizes predicate aliases (e.g. `uses_database` vs `persists_to`) and antonyms (`enabled` vs `disabled`).
- Identifies active un-superseded conflicting claims across the graph.
- Provides automatic tie-breaking based on evidence confidence ratings and recency.

### 3.3 ContextCompiler (`src/cortex_mcp/compiler.py`)
- **Lexical BM25 Scoring**: Tokenizes queries into programming identifiers (breaking down snake_case, camelCase, path delimiters).
- **Graph Spreading Activation**: Propagates relevance scores along the 2-hop ego network from seeded entities to relevant neighbors.
- **Greedy Knapsack Packing**: Fits the most informative, non-superseded memory items into a user-specified token budget (e.g. 500, 1000, 2000 tokens), preventing prompt bloat.

### 3.4 MCP Server Protocol (`src/cortex_mcp/server.py`)
- Implements standard MCP JSON-RPC 2.0 protocol over `stdio`.
- Exposes tools for recording decisions, querying entity ego-graphs, auditing contradictions, and executing point-in-time time travel.

---

## 4. Verification and Quality Assurance

- **100% Deterministic Testing**: 84 unit and integration tests passing in under 0.25 seconds without external mock servers.
- **Zero Cloud Runtime**: Pure Python standard library implementation with zero external runtime dependencies.
