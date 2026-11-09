# ADR 001: Bi-Temporal Knowledge Modeling for AI Agent Long-Term Memory

## Status
Accepted

## Context
AI coding agents (e.g. Claude Code, Cursor, Windsurf) frequently encounter shifting architectural requirements across multi-day and multi-session projects. When using standard append-only context logging (such as markdown scratchpads or flat vector databases), conflicting information accumulates over time. For example:
- On Monday, the database is configured as SQLite for rapid prototyping.
- On Thursday, the database is migrated to PostgreSQL for concurrency support.
- A standard similarity search over embeddings retrieves both statements with high similarity, confusing the LLM into generating conflicting schema migrations.

We require a deterministic data structure that maintains historical lineage for time-travel audits while cleanly suppressing superseded architectural assertions from active LLM context windows.

## Decision
We adopted a **Bi-Temporal Knowledge Graph** architecture:
1. **Two Time Dimensions**:
   - `created_at` (Transaction Time): Recording timestamp in the memory graph.
   - `valid_from` and `valid_until` (Valid Time): Real-world interval in which the fact is considered true in the project.
2. **Deterministic Supersession**:
   - When a singular predicate (e.g., `uses_database`) is updated for an entity, the active predecessor fact is marked as superseded: `valid_until` is set to the current timestamp, and `superseded_by` references the new fact ID.
3. **Default Stale Fact Suppression**:
   - The `ContextCompiler` strictly excludes superseded facts by default unless an explicit time-travel query (`as_of`) is requested.
4. **Local Atomic JSON Storage**:
   - Persistence is implemented via atomic filesystem writes (`os.replace`) to `.cortex/memory.json` accompanied by a SHA-256 Merkle chain to detect corruption without requiring heavy database daemons.

## Consequences
### Positive
- Zero stale fact pollution in LLM context windows.
- Full provenance and audit trails for architectural evolutions.
- Sub-millisecond queries with zero network latency or external database services.
- Seamless compatibility with any MCP-compliant AI editor.

### Negative / Trade-offs
- Manual or rule-based definition of singular vs multi-value predicates.
- Graph storage scales in memory linearly with the number of historical mutations, mitigated by periodic snapshotting.
