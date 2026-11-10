"""
Tests for Cortex-MCP v1.1.0:
- Semantic & Polarity Contradiction Auditor (`src/cortex_mcp/contradictions.py`)
- Grounded Citation Bundle Exporter for `truthgate` (`src/cortex_mcp/grounding_export.py`)
- CLI subcommands (`cortex-mcp audit-contradictions` and `cortex-mcp export-sources`)
- MCP tool `cortex_audit_contradictions` in `server.py` / `mcp_server.py`
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from cortex_mcp import (
    BiTemporalMemoryGraph,
    ContextCompiler,
    ContradictionAuditor,
    ContradictionAuditReport,
    CortexMCPServer,
    __version__,
    audit_contradictions,
    export_truthgate_sources,
    normalize_predicate,
)
from cortex_mcp.cli import build_demo_scenario, main as cli_main
from cortex_mcp.mcp_server import SERVER_VERSION


def test_version_is_1_1_0() -> None:
    assert __version__ == "1.1.0"
    assert SERVER_VERSION == "1.1.0"


def test_normalize_predicate_aliases_and_negations() -> None:
    assert normalize_predicate("uses_token_format") == ("token_format", False)
    assert normalize_predicate("token_format") == ("token_format", False)
    assert normalize_predicate("auth_token") == ("token_format", False)
    assert normalize_predicate("does_not_use_token_format") == ("token_format", True)
    assert normalize_predicate("never_allows_plaintext") == ("plaintext", True)
    assert normalize_predicate("requires_isolation") == ("isolation_level", False)


def test_clean_demo_graph_has_zero_contradictions() -> None:
    graph = build_demo_scenario()
    report = audit_contradictions(graph)
    assert isinstance(report, ContradictionAuditReport)
    assert report.clean is True
    assert report.contradiction_count == 0
    assert report.critical_count == 0
    assert "CLEAN (0 CONTRADICTIONS)" in report.summary_markdown


def test_detect_negation_polarity_conflict() -> None:
    graph = BiTemporalMemoryGraph()
    graph.upsert_fact(
        fact_id="fact_tls_pos",
        subject_id="api_gateway",
        predicate="allows_mtls",
        object_value="true",
        singular=True,
        valid_from="2026-01-01T00:00:00+00:00",
    )
    graph.upsert_fact(
        fact_id="fact_tls_neg",
        subject_id="api_gateway",
        predicate="disallows_mtls",
        object_value="true",
        singular=True,
        valid_from="2026-02-01T00:00:00+00:00",
    )
    report = audit_contradictions(graph)
    assert report.clean is False
    assert report.contradiction_count == 1
    conflict = report.conflicts[0]
    assert conflict.kind == "negation_polarity_conflict"
    assert conflict.severity == "CRITICAL"
    assert conflict.recommended_winner_id == "fact_tls_neg"
    assert conflict.recommended_supersede_id == "fact_tls_pos"


def test_detect_antonym_object_conflict() -> None:
    graph = BiTemporalMemoryGraph()
    graph.upsert_fact(
        fact_id="fact_enc_1",
        subject_id="audit_log_sink",
        predicate="has_storage_mode",
        object_value="encrypted",
        singular=False,
        valid_from="2026-01-10T00:00:00+00:00",
    )
    graph.upsert_fact(
        fact_id="fact_enc_2",
        subject_id="audit_log_sink",
        predicate="storage_mode",
        object_value="plaintext",
        singular=False,
        valid_from="2026-01-15T00:00:00+00:00",
    )
    report = audit_contradictions(graph)
    assert report.clean is False
    assert report.contradiction_count == 1
    conflict = report.conflicts[0]
    assert conflict.kind == "antonym_object_conflict"
    assert conflict.severity == "CRITICAL"
    assert "encrypted" in conflict.explanation and "plaintext" in conflict.explanation


def test_detect_predicate_alias_conflict() -> None:
    graph = BiTemporalMemoryGraph()
    graph.upsert_fact(
        fact_id="fact_tok_a",
        subject_id="auth_service",
        predicate="uses_token_format",
        object_value="PASETO_v4",
        singular=True,
        valid_from="2026-03-01T00:00:00+00:00",
    )
    # Inserted by a second agent using alias `auth_token` without triggering exact-predicate supersession
    graph.upsert_fact(
        fact_id="fact_tok_b",
        subject_id="auth_service",
        predicate="auth_token",
        object_value="JWT_HS256",
        singular=True,
        valid_from="2026-01-01T00:00:00+00:00",
    )
    report = audit_contradictions(graph)
    assert report.clean is False
    assert report.contradiction_count == 1
    conflict = report.conflicts[0]
    assert conflict.kind == "predicate_alias_conflict"
    assert conflict.severity == "HIGH"
    assert conflict.recommended_winner_id == "fact_tok_a"
    assert conflict.recommended_supersede_id == "fact_tok_b"


def test_detect_unsuperseded_multi_value_conflict() -> None:
    graph = BiTemporalMemoryGraph()
    graph.upsert_fact(
        fact_id="fact_port_1",
        subject_id="metrics_server",
        predicate="listen_port",
        object_value="8080",
        singular=False,
        valid_from="2026-01-01T00:00:00+00:00",
    )
    graph.upsert_fact(
        fact_id="fact_port_2",
        subject_id="metrics_server",
        predicate="listen_port",
        object_value="9090",
        singular=False,
        valid_from="2026-02-01T00:00:00+00:00",
    )
    report = audit_contradictions(graph)
    assert report.clean is False
    assert report.contradiction_count == 1
    assert report.conflicts[0].kind == "unsuperseded_value_conflict"
    assert report.conflicts[0].severity == "MEDIUM"


def test_contradiction_confidence_tiebreaker() -> None:
    graph = BiTemporalMemoryGraph()
    graph.upsert_fact(
        fact_id="fact_high_conf",
        subject_id="worker",
        predicate="uses_execution_mode",
        object_value="asynchronous",
        confidence=0.98,
        valid_from="2026-01-01T00:00:00+00:00",
    )
    graph.upsert_fact(
        fact_id="fact_low_conf",
        subject_id="worker",
        predicate="execution_mode",
        object_value="synchronous",
        confidence=0.55,
        valid_from="2026-02-01T00:00:00+00:00",
    )
    report = audit_contradictions(graph)
    assert report.contradiction_count == 1
    assert report.conflicts[0].recommended_winner_id == "fact_high_conf"
    assert report.conflicts[0].recommended_supersede_id == "fact_low_conf"


def test_auto_resolve_supersedes_conflicting_loser() -> None:
    graph = BiTemporalMemoryGraph()
    graph.upsert_fact(
        fact_id="fact_old_alias",
        subject_id="auth_service",
        predicate="auth_token",
        object_value="JWT_HS256",
        valid_from="2026-01-01T00:00:00+00:00",
    )
    graph.upsert_fact(
        fact_id="fact_new_alias",
        subject_id="auth_service",
        predicate="uses_token_format",
        object_value="PASETO_v4",
        valid_from="2026-04-01T00:00:00+00:00",
    )
    report = audit_contradictions(graph, auto_resolve=True)
    assert report.contradiction_count == 1
    assert report.resolved_fact_ids == ["fact_old_alias"]
    assert not graph.facts["fact_old_alias"].is_active_at(None)
    assert graph.facts["fact_old_alias"].superseded_by == "fact_new_alias"

    # Re-auditing after auto_resolve is now 100% clean!
    after_report = audit_contradictions(graph)
    assert after_report.clean is True
    assert after_report.contradiction_count == 0


def test_export_truthgate_sources_full_active_graph() -> None:
    graph = build_demo_scenario()
    sources = export_truthgate_sources(graph)
    source_ids = {s["source_id"] for s in sources}

    # Active facts and episodes are exported
    assert "fact_auth_token_v2" in source_ids
    assert "fact_auth_key_v2" in source_ids
    assert "fact_ledger_isolation" in source_ids
    assert "ep_inv_007" in source_ids

    # Superseded stale facts are strictly excluded (zero stale-fact leakage!)
    assert "fact_auth_token_v1" not in source_ids
    assert "fact_auth_key_v1" not in source_ids

    # Check metadata & Merkle root on exported SourceDocuments
    sample = next(s for s in sources if s["source_id"] == "fact_auth_token_v2")
    assert "PASETO_v4_public" in sample["content"]
    assert sample["metadata"]["is_active"] is True
    assert len(sample["metadata"]["content_hash"]) == 64
    assert len(sample["metadata"]["graph_merkle_digest"]) == 64


def test_export_truthgate_sources_with_query_and_file_output(tmp_path: Path) -> None:
    graph = build_demo_scenario()
    out_file = tmp_path / "truthgate_sources.json"
    sources = export_truthgate_sources(
        graph,
        query="auth_service uses_token_format signing_primitive",
        max_tokens=300,
        output_path=out_file,
    )
    assert len(sources) > 0
    assert out_file.exists()
    loaded = json.loads(out_file.read_text(encoding="utf-8"))
    assert len(loaded) == len(sources)
    assert all("compiler_score" in doc["metadata"] for doc in loaded)


def test_export_truthgate_sources_from_precompiled_bundle() -> None:
    graph = build_demo_scenario()
    compiler = ContextCompiler(graph)
    bundle = compiler.compile_context("payment_ledger SERIALIZABLE_WITH_IDEMPOTENCY_KEY", max_tokens=400)
    sources = export_truthgate_sources(graph, bundle=bundle)
    source_ids = {s["source_id"] for s in sources}
    assert "fact_ledger_isolation" in source_ids


def test_mcp_tool_cortex_audit_contradictions() -> None:
    graph = BiTemporalMemoryGraph()
    graph.upsert_fact(
        fact_id="f_pos",
        subject_id="cache",
        predicate="is_stateful",
        object_value="stateful",
        singular=False,
        valid_from="2026-01-01T00:00:00+00:00",
    )
    graph.upsert_fact(
        fact_id="f_neg",
        subject_id="cache",
        predicate="is_stateful",
        object_value="stateless",
        singular=False,
        valid_from="2026-02-01T00:00:00+00:00",
    )
    server = CortexMCPServer(graph=graph)
    resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 42,
            "method": "tools/call",
            "params": {
                "name": "cortex_audit_contradictions",
                "arguments": {"auto_resolve": True},
            },
        }
    )
    assert resp is not None
    data = resp["result"]["structuredContent"]
    assert data["contradiction_count"] == 1
    assert data["resolved_fact_ids"] == ["f_pos"]


def test_cli_audit_contradictions_subcommand(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Default demo scenario is clean -> exit code 0
    rc_clean = cli_main(["audit-contradictions", "--json"])
    out_clean = json.loads(capsys.readouterr().out)
    assert rc_clean == 0
    assert out_clean["clean"] is True

    # Persisted graph with a contradiction -> exit code 1
    store_path = tmp_path / "dirty_graph.json"
    g = BiTemporalMemoryGraph(storage_path=store_path)
    g.upsert_fact(
        fact_id="f1",
        subject_id="svc",
        predicate="uses_token_format",
        object_value="JWT",
        valid_from="2026-01-01T00:00:00+00:00",
    )
    g.upsert_fact(
        fact_id="f2",
        subject_id="svc",
        predicate="token_format",
        object_value="PASETO",
        valid_from="2026-02-01T00:00:00+00:00",
    )

    rc_dirty = cli_main(["audit-contradictions", "--storage", str(store_path)])
    out_md = capsys.readouterr().out
    assert rc_dirty == 1
    assert "CONTRADICTIONS FOUND" in out_md


def test_cli_export_sources_subcommand(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_path = tmp_path / "sources.json"
    rc = cli_main(
        [
            "export-sources",
            "--query",
            "auth_service uses_token_format",
            "--output",
            str(out_path),
        ]
    )
    msg = capsys.readouterr().out
    assert rc == 0
    assert "Exported" in msg
    assert out_path.exists()

    rc_stdout = cli_main(["export-sources"])
    parsed = json.loads(capsys.readouterr().out)
    assert rc_stdout == 0
    assert any(doc["source_id"] == "fact_auth_token_v2" for doc in parsed)


def test_audit_contradictions_as_of_time_travel() -> None:
    graph = BiTemporalMemoryGraph()
    graph.upsert_fact(
        fact_id="f_early_1",
        subject_id="gateway",
        predicate="allows_cors",
        object_value="allowed",
        singular=False,
        valid_from="2026-01-01T00:00:00+00:00",
    )
    graph.upsert_fact(
        fact_id="f_late_2",
        subject_id="gateway",
        predicate="allows_cors",
        object_value="forbidden",
        singular=False,
        valid_from="2026-03-01T00:00:00+00:00",
    )
    # At 2026-01-15 only f_early_1 was active -> clean!
    early_report = audit_contradictions(graph, as_of="2026-01-15T00:00:00+00:00")
    assert early_report.clean is True
    assert early_report.active_facts_scanned == 1

    # At 2026-04-01 both are active -> contradiction detected!
    late_report = audit_contradictions(graph, as_of="2026-04-01T00:00:00+00:00")
    assert late_report.clean is False
    assert late_report.contradiction_count == 1


def test_export_truthgate_sources_includes_entity_items() -> None:
    graph = BiTemporalMemoryGraph()
    graph.upsert_entity(
        "billing_engine",
        name="Billing Engine",
        entity_type="service",
        summary="Processes recurring subscriptions and ledger settlements.",
    )
    compiler = ContextCompiler(graph)
    bundle = compiler.compile_context("Billing Engine subscriptions", max_tokens=300)
    sources = export_truthgate_sources(graph, bundle=bundle)
    assert any(s["source_id"] == "billing_engine" and s["metadata"]["item_type"] == "entity" for s in sources)



def test_quickstart_example_runs_end_to_end():
    import runpy
    ns = runpy.run_path("examples/quickstart.py")
    res = ns["main"]()
    assert res["entities_count"] == 2
    assert res["facts_count"] == 2
    assert res["contradictions"] == 0
    assert res["integrity_valid"] is True


def test_detect_lifecycle_antonym_contradictions() -> None:
    """Verify that opposing lifecycle status (deprecated vs active/supported) flags an antonym conflict."""
    graph = BiTemporalMemoryGraph()
    graph.upsert_fact(
        fact_id="fact_dep",
        subject_id="service_v1",
        predicate="lifecycle_state",
        object_value="deprecated",
        singular=False,
    )
    graph.upsert_fact(
        fact_id="fact_act",
        subject_id="service_v1",
        predicate="lifecycle_state",
        object_value="active",
        singular=False,
    )

    report = audit_contradictions(graph)
    assert report.clean is False
    assert report.contradiction_count == 1
    assert report.conflicts[0].kind == "antonym_object_conflict"


def test_detect_foundation_model_synonym_contradictions() -> None:
    """Verify that predicate aliases 'llm' and 'model_name' collide when values diverge."""
    graph = BiTemporalMemoryGraph()
    graph.upsert_fact(
        fact_id="fact_llm1",
        subject_id="summarizer",
        predicate="llm",
        object_value="claude-3-5-sonnet",
        singular=False,
    )
    graph.upsert_fact(
        fact_id="fact_llm2",
        subject_id="summarizer",
        predicate="model_name",
        object_value="gpt-4o",
        singular=False,
    )

    report = audit_contradictions(graph)
    assert report.clean is False
    assert report.contradiction_count == 1
    assert report.conflicts[0].kind == "predicate_alias_conflict"

