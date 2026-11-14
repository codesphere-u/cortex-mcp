# MCP Tools & Semantic Contradiction Auditing

## 7 Exposed MCP Tools

| Tool | Purpose |
| :--- | :--- |
| `memory_record_episode` | Store an immutable ADR, bug root cause, invariant, migration, or session note |
| `memory_upsert_fact` | Record `(subject_id, predicate, object)` with automatic bi-temporal supersession |
| `memory_compile_context` | Rank active graph via Okapi BM25 + 2-hop spreading activation within `max_tokens` |
| `memory_query_entity` | Inspect active and historical ego-graph edges around an entity |
| `memory_time_travel` | Reconstruct the exact valid knowledge graph snapshot `as_of` a UTC timestamp |
| `memory_verify_integrity` | Verify SHA-256 hash chain and Merkle root digest |
| `cortex_audit_contradictions` | Detect polarity, antonym, alias, and singular drift conflicts (`auto_resolve` optional) |

## Contradiction Detection & TruthGate Export

```bash
cortex-mcp audit-contradictions --auto-resolve --json
cortex-mcp export-sources --query "auth_service signing" --max-tokens 1200 --output sources.json
```
