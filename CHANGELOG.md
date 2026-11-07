# Changelog

All notable changes to `cortex-mcp` are documented in this file.

## [1.1.0] - 2026-11-07

### Added
- **Semantic & Polarity Contradiction Auditor (`src/cortex_mcp/contradictions.py`)**:
  - `ContradictionAuditor` and `audit_contradictions()` scanning active facts in `BiTemporalMemoryGraph` to detect unresolved logical contradictions:
    - Negation polarity inversions (`allows_*` vs `disallows_*` / `does_not_*`).
    - Opposing technical antonym objects (`enabled` vs `disabled`, `encrypted` vs `plaintext`, `stateful` vs `stateless`, `synchronous` vs `asynchronous`, etc.).
    - Predicate alias collisions (`uses_token_format` vs `token_format` vs `auth_token`).
    - Unsuperseded multi-value drift on singular attributes.
  - Supports `auto_resolve=True` to deterministically supersede older or lower-confidence conflicting facts.
- **Grounded Citation Bundle Exporter for `truthgate` (`src/cortex_mcp/grounding_export.py`)**:
  - `export_truthgate_sources()` exporting compiled context packets or active graph items as a [`codesphere-u/truthgate`](https://github.com/codesphere-u/truthgate)-compatible `SourceDocument` JSON bundle (`source_id`, `title`, `content`, `metadata` with temporal provenance and SHA-256 Merkle root `graph_merkle_digest`) for zero stale-fact leakage verification.
- **CLI & MCP Server Extensions (`cli.py`, `server.py`, `mcp_server.py`)**:
  - Added `cortex-mcp audit-contradictions` and `cortex-mcp export-sources` CLI subcommands.
  - Added `cortex_audit_contradictions` MCP tool to `CortexMCPServer`.
- **Test Suite Expansion**:
  - Added 17 new tests in `tests/test_contradictions_and_export.py` (bringing total tests from 67 to **84 passing tests**).

## [1.0.0] - 2026-11-07

### Added
- Initial release of `cortex-mcp`:
  - `BiTemporalMemoryGraph` with `Entity`, `TemporalFact`, and `Episode` primitives, automatic singular conflict detection, temporal supersession, K-hop ego-graph traversal, point-in-time snapshots, and SHA-256 Merkle integrity verification.
  - `ContextCompiler` combining Okapi BM25 lexical scoring, code-aware tokenization, and 2-hop graph spreading activation under a strict `max_tokens` budget.
  - `CortexMCPServer` implementing JSON-RPC 2.0 Model Context Protocol over stdio and in-memory transports.
