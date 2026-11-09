"""End-to-end Cortex-MCP example: Bi-temporal fact tracking, automatic supersession,
token-budgeted context compilation, contradiction auditing, and TruthGate export.

Run:  python examples/quickstart.py
Zero cloud dependencies, sub-millisecond local execution.
"""

import tempfile
from pathlib import Path

from cortex_mcp import (
    BiTemporalMemoryGraph,
    ContextCompiler,
    audit_contradictions,
    export_truthgate_sources,
)


def main() -> dict:
    graph = BiTemporalMemoryGraph()

    # 1. Register architectural entities
    auth_service = graph.upsert_entity(
        entity_id="auth_service",
        entity_type="service",
        attributes={"runtime": "python3.12", "team": "security"},
    )
    db_service = graph.upsert_entity(
        entity_id="primary_database",
        entity_type="database",
        attributes={"engine": "sqlite-wal"},
    )

    # 2. Record an architectural decision episode (ADR)
    adr_ep = graph.record_episode(
        title="ADR-019: Token Standard Migration to PASETO v4",
        category="adr",
        content="JWT HS256 was vulnerable to algorithm-confusion attacks. We now enforce PASETO v4.",
        entities_mentioned=["auth_service"],
    )

    # 3. Bi-temporal fact recording with automatic supersession
    # Fact 1: Old fact (JWT HS256) valid in early 2026
    old_fact, _ = graph.upsert_fact(
        subject_id="auth_service",
        predicate="uses_token_format",
        object_value="JWT_HS256",
        valid_from="2026-01-01T00:00:00Z",
        singular=True,
    )

    # Fact 2: New fact (PASETO_v4_public) - automatically supersedes old fact
    new_fact, superseded = graph.upsert_fact(
        subject_id="auth_service",
        predicate="uses_token_format",
        object_value="PASETO_v4_public",
        valid_from="2026-04-20T16:45:00Z",
        singular=True,
    )

    print("BiTemporalMemoryGraph: Recorded facts.")
    print(f"  Old Fact Superseded: {old_fact.id} -> superseded_by={graph.facts[old_fact.id].superseded_by}")
    assert graph.facts[old_fact.id].superseded_by == new_fact.id, "Old fact should be superseded"

    # 4. Context Compilation: BM25 + Graph Spreading within strict token budget (200 tokens)
    compiler = ContextCompiler(graph)
    bundle = compiler.compile_context(
        query="auth_service token format signing",
        max_tokens=200,
    )
    print(f"ContextCompiler: Compiled {len(bundle.items)} items ({bundle.used_tokens} tokens / 200 budget)")
    # Assert superseded fact is suppressed (zero stale context bloat)
    rendered = bundle.rendered_markdown
    assert "PASETO_v4_public" in rendered, "Active fact should be in compiled context"
    assert "JWT_HS256" not in rendered, "Superseded fact MUST be suppressed from active context"

    # 5. Contradiction Auditor: Verify graph consistency
    audit_report = audit_contradictions(graph)
    print(f"ContradictionAuditor: Clean={audit_report.clean}, Conflicts={audit_report.contradiction_count}")
    assert audit_report.clean is True, "Graph should have zero active contradictions"

    # 6. TruthGate Export: Export grounded sources for citation verification
    truthgate_docs = export_truthgate_sources(graph)
    print(f"TruthGate Export: Generated {len(truthgate_docs)} verified citation documents")
    assert len(truthgate_docs) > 0

    # 7. Local atomic persistence and tamper-evident Merkle hash verification
    with tempfile.TemporaryDirectory() as tmp:
        save_path = Path(tmp) / "cortex_memory.json"
        graph.save(save_path)
        restored_graph = BiTemporalMemoryGraph()
        restored_graph.load(save_path)
        integrity = restored_graph.verify_integrity()
        assert integrity["valid"] is True, "Hash-chain integrity check failed"
        print(f"Persistence: Verified Merkle state digest: {integrity['graph_merkle_digest'][:16]}...")

    return {
        "entities_count": len(graph.entities),
        "facts_count": len(graph.facts),
        "compiled_tokens": bundle.used_tokens,
        "contradictions": audit_report.contradiction_count,
        "integrity_valid": integrity["valid"],
    }


if __name__ == "__main__":
    main()
