"""Comprehensive test suite for Cortex-MCP (55+ tests)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from cortex_mcp.cli import build_demo_scenario, percentile, run_benchmark, run_demo
from cortex_mcp.cli import main as cli_main
from cortex_mcp.compiler import ContextCompiler, estimate_tokens, tokenize
from cortex_mcp.graph import (
    VALID_EPISODE_CATEGORIES,
    BiTemporalMemoryGraph,
    Episode,
    TemporalFact,
    parse_iso_timestamp,
)
from cortex_mcp.server import (
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    CortexMCPServer,
)

# ============================================================================
# 1. Bi-Temporal Graph & Entity / Episode Primitives
# ============================================================================


def test_parse_iso_timestamp_variants() -> None:
    dt_z = parse_iso_timestamp("2026-01-15T12:00:00Z")
    dt_offset = parse_iso_timestamp("2026-01-15T12:00:00+00:00")
    dt_naive = parse_iso_timestamp("2026-01-15T12:00:00")
    assert dt_z == dt_offset == dt_naive


def test_entity_upsert_and_update() -> None:
    graph = BiTemporalMemoryGraph()
    ent = graph.upsert_entity(
        "auth_service",
        name="Auth Service",
        entity_type="service",
        summary="Handles login",
        attributes={"tier": "critical"},
    )
    assert ent.id == "auth_service"
    assert ent.entity_type == "service"
    assert ent.attributes["tier"] == "critical"

    updated = graph.upsert_entity(
        "auth_service",
        name="Authentication Service v2",
        summary="Handles PASETO login",
        attributes={"owner": "security-team"},
    )
    assert updated.name == "Authentication Service v2"
    assert updated.summary == "Handles PASETO login"
    assert updated.attributes["tier"] == "critical"
    assert updated.attributes["owner"] == "security-team"


def test_entity_empty_id_raises() -> None:
    graph = BiTemporalMemoryGraph()
    with pytest.raises(ValueError, match="entity_id cannot be empty"):
        graph.upsert_entity("   ")


def test_episode_recording_and_auto_entities() -> None:
    graph = BiTemporalMemoryGraph()
    ep = graph.record_episode(
        title="ADR-001: Use Redis Streams",
        category="adr",
        content="Selected Redis Streams for consumer groups.",
        files_touched=["src/events/stream.py"],
        entities_mentioned=["event_bus", "worker_pool"],
    )
    assert ep.id.startswith("ep_")
    assert len(ep.sha256) == 64
    assert "event_bus" in graph.entities
    assert "worker_pool" in graph.entities


def test_episode_invalid_category_raises() -> None:
    graph = BiTemporalMemoryGraph()
    with pytest.raises(ValueError, match="Invalid episode category"):
        graph.record_episode(
            title="Bad Category",
            category="invalid_cat",
            content="Should fail",
        )


def test_all_valid_episode_categories() -> None:
    graph = BiTemporalMemoryGraph()
    for cat in VALID_EPISODE_CATEGORIES:
        ep = graph.record_episode(title=f"Title {cat}", category=cat, content=f"Content {cat}")
        assert ep.category == cat


def test_temporal_fact_validation_errors() -> None:
    with pytest.raises(ValueError, match="requires either object_id or object_value"):
        TemporalFact(id="f1", subject_id="s1", predicate="p1")

    with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
        TemporalFact(id="f2", subject_id="s1", predicate="p1", object_value="val", confidence=1.5)


def test_upsert_fact_empty_subject_or_predicate_raises() -> None:
    graph = BiTemporalMemoryGraph()
    with pytest.raises(ValueError, match="subject_id and predicate must be non-empty"):
        graph.upsert_fact("", "uses", object_value="x")
    with pytest.raises(ValueError, match="subject_id and predicate must be non-empty"):
        graph.upsert_fact("svc", "  ", object_value="x")


# ============================================================================
# 2. Automatic Conflict Detection & Temporal Supersession
# ============================================================================


def test_singular_fact_automatic_supersession() -> None:
    graph = BiTemporalMemoryGraph()
    t1 = "2026-01-01T00:00:00+00:00"
    t2 = "2026-02-01T00:00:00+00:00"

    f1, sup1 = graph.upsert_fact(
        subject_id="auth_service",
        predicate="uses_token_format",
        object_value="JWT_HS256",
        singular=True,
        valid_from=t1,
    )
    assert len(sup1) == 0
    assert f1.is_active_at(None)

    f2, sup2 = graph.upsert_fact(
        subject_id="auth_service",
        predicate="uses_token_format",
        object_value="PASETO_v4",
        singular=True,
        valid_from=t2,
    )
    assert len(sup2) == 1
    assert sup2[0].id == f1.id
    assert not f1.is_active_at(None)
    assert f1.valid_until == t2
    assert f1.superseded_by == f2.id
    assert f2.is_active_at(None)


def test_three_generation_supersession_chain() -> None:
    graph = BiTemporalMemoryGraph()
    f1, _ = graph.upsert_fact(
        subject_id="db",
        predicate="pool_mode",
        object_value="session",
        valid_from="2026-01-01T00:00:00+00:00",
    )
    f2, sup2 = graph.upsert_fact(
        subject_id="db",
        predicate="pool_mode",
        object_value="transaction",
        valid_from="2026-02-01T00:00:00+00:00",
    )
    f3, sup3 = graph.upsert_fact(
        subject_id="db",
        predicate="pool_mode",
        object_value="statement",
        valid_from="2026-03-01T00:00:00+00:00",
    )
    assert [s.id for s in sup2] == [f1.id]
    assert [s.id for s in sup3] == [f2.id]
    active = graph.get_facts(subject_id="db", predicate="pool_mode")
    assert len(active) == 1
    assert active[0].id == f3.id
    all_history = graph.get_facts(subject_id="db", predicate="pool_mode", include_superseded=True)
    assert len(all_history) == 3


def test_idempotent_duplicate_fact_upsert_and_confidence_upgrade() -> None:
    graph = BiTemporalMemoryGraph()
    f1, _ = graph.upsert_fact(
        subject_id="api",
        predicate="protocol",
        object_value="gRPC",
        confidence=0.75,
    )
    f1_again, sup = graph.upsert_fact(
        subject_id="api",
        predicate="protocol",
        object_value="gRPC",
        confidence=0.95,
    )
    assert f1_again.id == f1.id
    assert len(sup) == 0
    assert f1.confidence == 0.95
    assert len(graph.facts) == 1


def test_non_singular_facts_coexist_without_supersession() -> None:
    graph = BiTemporalMemoryGraph()
    _f1, sup1 = graph.upsert_fact(
        subject_id="gateway",
        predicate="routes_to",
        object_id="billing_svc",
        singular=False,
    )
    _f2, sup2 = graph.upsert_fact(
        subject_id="gateway",
        predicate="routes_to",
        object_id="search_svc",
        singular=False,
    )
    assert len(sup1) == 0
    assert len(sup2) == 0
    active = graph.get_facts(subject_id="gateway", predicate="routes_to")
    assert {f.object_id for f in active} == {"billing_svc", "search_svc"}


# ============================================================================
# 3. Point-in-Time Time Travel & K-Hop Graph Traversal
# ============================================================================


def test_point_in_time_historical_queries() -> None:
    graph = build_demo_scenario()

    # At 2026-01-20: JWT_HS256 was active, PASETO_v4 did not exist yet
    jan_facts = graph.get_facts(
        subject_id="auth_service",
        predicate="uses_token_format",
        as_of="2026-01-20T00:00:00+00:00",
    )
    assert len(jan_facts) == 1
    assert jan_facts[0].object_value == "JWT_HS256"

    # At 2026-05-01: PASETO_v4_public is active, JWT_HS256 is superseded
    may_facts = graph.get_facts(
        subject_id="auth_service",
        predicate="uses_token_format",
        as_of="2026-05-01T00:00:00+00:00",
    )
    assert len(may_facts) == 1
    assert may_facts[0].object_value == "PASETO_v4_public"


def test_snapshot_as_of_counts() -> None:
    graph = build_demo_scenario()
    snap_early = graph.snapshot_as_of("2026-01-15T00:00:00+00:00")
    assert snap_early["active_fact_count"] == 2
    assert snap_early["historical_superseded_count"] == 0
    assert snap_early["episode_count"] == 1

    snap_late = graph.snapshot_as_of("2026-05-01T00:00:00+00:00")
    assert snap_late["active_fact_count"] == 6
    assert snap_late["historical_superseded_count"] == 2
    assert snap_late["episode_count"] == 4


def test_k_hop_ego_graph_traversal() -> None:
    graph = build_demo_scenario()
    # order_repository -> (1 hop) -> payment_ledger -> (2 hops) -> auth_service
    hop1 = graph.traverse_subgraph("order_repository", max_hops=1)
    hop1_ids = {e["id"] for e in hop1["entities"]}
    assert "order_repository" in hop1_ids
    assert "payment_ledger" in hop1_ids
    assert "auth_service" not in hop1_ids

    hop2 = graph.traverse_subgraph("order_repository", max_hops=2)
    hop2_ids = {e["id"] for e in hop2["entities"]}
    assert {"order_repository", "payment_ledger", "auth_service"}.issubset(hop2_ids)


def test_query_entity_includes_active_and_superseded() -> None:
    graph = build_demo_scenario()
    info = graph.query_entity("auth_service", include_superseded=True, max_hops=1)
    assert info["exists"] is True
    assert len(info["active_outgoing_facts"]) == 2
    assert len(info["superseded_outgoing_facts"]) == 2
    assert len(info["active_incoming_facts"]) == 1
    assert len(info["related_episodes"]) >= 2


def test_query_nonexistent_entity() -> None:
    graph = BiTemporalMemoryGraph()
    info = graph.query_entity("missing_node", include_superseded=False, max_hops=1)
    assert info["exists"] is False
    assert info["active_outgoing_facts"] == []


# ============================================================================
# 4. Cryptographic Integrity & Persistence
# ============================================================================


def test_verify_integrity_and_tamper_detection() -> None:
    graph = build_demo_scenario()
    report = graph.verify_integrity()
    assert report["valid"] is True
    assert report["corrupted_facts"] == []
    assert report["corrupted_episodes"] == []

    # Simulate tampering with a fact's object_value without updating its hash
    graph.facts["fact_auth_token_v2"].object_value = "TAMPERED_TOKEN"
    tampered_report = graph.verify_integrity()
    assert tampered_report["valid"] is False
    assert "fact_auth_token_v2" in tampered_report["corrupted_facts"]

    # Simulate tampering with an episode's content
    graph.episodes["ep_inv_007"].content = "TAMPERED_CONTENT"
    tampered_report_2 = graph.verify_integrity()
    assert "ep_inv_007" in tampered_report_2["corrupted_episodes"]


def test_persistence_save_and_load_roundtrip(tmp_path: Path) -> None:
    storage_file = tmp_path / "memory_graph.json"
    graph = BiTemporalMemoryGraph(storage_path=storage_file)
    build_demo_scenario(graph)

    assert storage_file.exists()
    digest_before = graph.verify_integrity()["graph_merkle_digest"]

    loaded_graph = BiTemporalMemoryGraph(storage_path=storage_file)
    digest_after = loaded_graph.verify_integrity()["graph_merkle_digest"]
    assert digest_before == digest_after
    assert len(loaded_graph.entities) == len(graph.entities)
    assert len(loaded_graph.facts) == len(graph.facts)
    assert len(loaded_graph.episodes) == len(graph.episodes)


def test_save_without_path_raises() -> None:
    graph = BiTemporalMemoryGraph()
    with pytest.raises(ValueError, match="No storage_path specified"):
        graph.save()


def test_load_missing_file_raises(tmp_path: Path) -> None:
    graph = BiTemporalMemoryGraph()
    with pytest.raises(FileNotFoundError):
        graph.load(tmp_path / "does_not_exist.json")


# ============================================================================
# 5. Token-Budgeted Context Compiler & BM25 + Spreading Activation
# ============================================================================


def test_tokenize_splits_snake_camel_and_paths() -> None:
    tokens = tokenize("src/orders/OrderRepository.py uses_token_format")
    assert "orderrepository" in tokens
    assert "order" in tokens
    assert "repository" in tokens
    assert "uses" in tokens
    assert "token" in tokens


def test_tokenize_and_estimate_tokens_empty() -> None:
    assert tokenize("") == []
    assert estimate_tokens("") == 0
    assert estimate_tokens("short text") >= 2


def test_compiler_suppresses_superseded_facts_by_default() -> None:
    graph = build_demo_scenario()
    compiler = ContextCompiler(graph)
    bundle = compiler.compile_context(
        query="auth_service uses_token_format signing_primitive",
        max_tokens=500,
        include_superseded=False,
    )
    assert bundle.excluded_stale_fact_count >= 2
    assert "PASETO_v4_public" in bundle.rendered_markdown
    assert "JWT_HS256" not in [
        item.formatted_text for item in bundle.items if item.item_type == "fact"
    ]
    assert all(not item.is_superseded for item in bundle.items)


def test_compiler_can_include_superseded_when_requested() -> None:
    graph = build_demo_scenario()
    compiler = ContextCompiler(graph)
    bundle = compiler.compile_context(
        query="auth_service uses_token_format JWT_HS256 PASETO_v4_public",
        max_tokens=800,
        include_superseded=True,
    )
    assert any(item.is_superseded for item in bundle.items)


def test_compiler_strict_token_budget_enforcement() -> None:
    graph = build_demo_scenario()
    compiler = ContextCompiler(graph)
    for budget in [45, 90, 150, 250, 600]:
        bundle = compiler.compile_context(
            query="auth_service payment_ledger order_repository invariant",
            max_tokens=budget,
        )
        assert bundle.used_tokens <= budget
        assert 0.0 <= bundle.utilization_ratio <= 1.0


def test_compiler_invalid_budget_raises() -> None:
    graph = build_demo_scenario()
    compiler = ContextCompiler(graph)
    with pytest.raises(ValueError, match="max_tokens must be positive"):
        compiler.compile_context("auth_service", max_tokens=0)


def test_compiler_graph_spreading_activation_reaches_connected_entity() -> None:
    graph = build_demo_scenario()
    compiler = ContextCompiler(graph)
    # Querying `payment_ledger` should also activate `auth_service` via `verifies_caller_via`
    bundle = compiler.compile_context(
        query="payment_ledger",
        max_tokens=600,
    )
    assert "payment_ledger" in bundle.activated_entities
    assert "auth_service" in bundle.activated_entities


def test_compiler_time_travel_as_of() -> None:
    graph = build_demo_scenario()
    compiler = ContextCompiler(graph)
    bundle_jan = compiler.compile_context(
        query="auth_service uses_token_format",
        max_tokens=500,
        as_of="2026-01-20T00:00:00+00:00",
    )
    fact_texts = [item.formatted_text for item in bundle_jan.items if item.item_type == "fact"]
    assert any("JWT_HS256" in t for t in fact_texts)
    assert not any("PASETO_v4_public" in t for t in fact_texts)


# ============================================================================
# 6. Model Context Protocol (MCP) JSON-RPC 2.0 Server
# ============================================================================


def test_mcp_initialize_and_ping() -> None:
    server = CortexMCPServer()
    init_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "clientInfo": {"name": "pytest", "version": "1.0"}},
        }
    )
    assert init_resp is not None
    assert init_resp["result"]["serverInfo"]["name"] == "cortex-mcp"
    assert "tools" in init_resp["result"]["capabilities"]

    # Notification returns None
    notif_resp = server.handle_request({"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert notif_resp is None
    assert server.initialized is True

    ping_resp = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "ping"})
    assert ping_resp == {"jsonrpc": "2.0", "id": 2, "result": {}}


def test_mcp_tools_list_exposes_six_tools() -> None:
    server = CortexMCPServer()
    resp = server.handle_request({"jsonrpc": "2.0", "id": 10, "method": "tools/list"})
    assert resp is not None
    tools = resp["result"]["tools"]
    names = [t["name"] for t in tools]
    assert names == [
        "memory_record_episode",
        "memory_upsert_fact",
        "memory_compile_context",
        "memory_query_entity",
        "memory_time_travel",
        "memory_verify_integrity",
        "cortex_audit_contradictions",
    ]


def test_mcp_tools_call_full_workflow() -> None:
    server = CortexMCPServer()

    # 1. Record episode
    ep_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "memory_record_episode",
                "arguments": {
                    "title": "ADR-100: Cache Layer",
                    "category": "adr",
                    "content": "Use DragonflyDB for session caching.",
                    "files_touched": ["src/cache/client.py"],
                    "entities_mentioned": ["cache_service"],
                    "timestamp": "2026-01-10T00:00:00+00:00",
                },
            },
        }
    )
    assert ep_resp is not None
    ep_data = ep_resp["result"]["structuredContent"]
    assert ep_data["status"] == "recorded"
    ep_id = ep_data["episode"]["id"]

    # 2. Upsert initial fact
    f1_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "memory_upsert_fact",
                "arguments": {
                    "subject_id": "cache_service",
                    "predicate": "engine",
                    "object_value": "Memcached",
                    "singular": True,
                    "valid_from": "2026-01-01T00:00:00+00:00",
                },
            },
        }
    )
    assert f1_resp is not None
    assert f1_resp["result"]["structuredContent"]["superseded_count"] == 0

    # 3. Upsert superseding fact
    f2_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "memory_upsert_fact",
                "arguments": {
                    "subject_id": "cache_service",
                    "predicate": "engine",
                    "object_value": "DragonflyDB",
                    "singular": True,
                    "source_episode_id": ep_id,
                    "valid_from": "2026-01-10T00:00:00+00:00",
                },
            },
        }
    )
    assert f2_resp is not None
    assert f2_resp["result"]["structuredContent"]["superseded_count"] == 1

    # 4. Compile context
    comp_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "memory_compile_context",
                "arguments": {"query": "cache_service engine", "max_tokens": 400},
            },
        }
    )
    assert comp_resp is not None
    bundle = comp_resp["result"]["structuredContent"]
    assert "DragonflyDB" in bundle["rendered_markdown"]
    assert "Memcached" not in bundle["rendered_markdown"]

    # 5. Query entity
    q_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "memory_query_entity",
                "arguments": {"entity_id": "cache_service", "include_superseded": True},
            },
        }
    )
    assert q_resp is not None
    q_data = q_resp["result"]["structuredContent"]
    assert len(q_data["active_outgoing_facts"]) == 1
    assert len(q_data["superseded_outgoing_facts"]) == 1

    # 6. Time travel
    tt_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "memory_time_travel",
                "arguments": {"as_of": "2026-01-05T00:00:00+00:00"},
            },
        }
    )
    assert tt_resp is not None
    tt_data = tt_resp["result"]["structuredContent"]
    assert tt_data["active_facts"][0]["object_value"] == "Memcached"

    # 7. Verify integrity
    ver_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "memory_verify_integrity", "arguments": {}},
        }
    )
    assert ver_resp is not None
    assert ver_resp["result"]["structuredContent"]["valid"] is True


def test_mcp_resources_list_and_read() -> None:
    graph = build_demo_scenario()
    server = CortexMCPServer(graph=graph)

    list_resp = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "resources/list"})
    assert list_resp is not None
    uris = [r["uri"] for r in list_resp["result"]["resources"]]
    assert "cortex://graph/summary" in uris
    assert "cortex://graph/integrity" in uris
    assert "cortex://episodes/recent" in uris

    for uri in uris:
        read_resp = server.handle_request(
            {"jsonrpc": "2.0", "id": 2, "method": "resources/read", "params": {"uri": uri}}
        )
        assert read_resp is not None
        contents = read_resp["result"]["contents"]
        assert len(contents) == 1
        parsed = json.loads(contents[0]["text"])
        assert isinstance(parsed, dict)


def test_mcp_prompts_list_and_get() -> None:
    graph = build_demo_scenario()
    server = CortexMCPServer(graph=graph)

    list_resp = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "prompts/list"})
    assert list_resp is not None
    names = [p["name"] for p in list_resp["result"]["prompts"]]
    assert "architecture-briefing" in names
    assert "bug-investigation-context" in names

    p1 = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "prompts/get",
            "params": {"name": "architecture-briefing", "arguments": {"component": "auth_service"}},
        }
    )
    assert p1 is not None
    assert "PASETO_v4_public" in p1["result"]["messages"][0]["content"]["text"]

    p2 = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "prompts/get",
            "params": {"name": "bug-investigation-context", "arguments": {"symptom": "order_repository N+1"}},
        }
    )
    assert p2 is not None
    assert "BUG-042" in p2["result"]["messages"][0]["content"]["text"]


def test_mcp_error_handling_cases() -> None:
    server = CortexMCPServer()

    # Invalid JSON-RPC envelope
    r1 = server.handle_request({"jsonrpc": "1.0", "id": 1, "method": "ping"})
    assert r1 is not None and r1["error"]["code"] == INVALID_REQUEST

    # Missing method
    r2 = server.handle_request({"jsonrpc": "2.0", "id": 2})
    assert r2 is not None and r2["error"]["code"] == INVALID_REQUEST

    # Unknown method
    r3 = server.handle_request({"jsonrpc": "2.0", "id": 3, "method": "unknown/method"})
    assert r3 is not None and r3["error"]["code"] == METHOD_NOT_FOUND

    # Missing tool name
    r4 = server.handle_request({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {}})
    assert r4 is not None and r4["error"]["code"] == INVALID_PARAMS

    # Unknown tool name
    r5 = server.handle_request(
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "nonexistent_tool"}}
    )
    assert r5 is not None and r5["error"]["code"] == INVALID_PARAMS

    # Tool execution ValueError returns isError=True
    r6 = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "memory_record_episode",
                "arguments": {"title": "T", "category": "bad_cat", "content": "C"},
            },
        }
    )
    assert r6 is not None and r6["result"]["isError"] is True

    # Unknown resource URI
    r7 = server.handle_request(
        {"jsonrpc": "2.0", "id": 7, "method": "resources/read", "params": {"uri": "cortex://bad"}}
    )
    assert r7 is not None and r7["error"]["code"] == INVALID_PARAMS

    # Missing resource URI
    r8 = server.handle_request({"jsonrpc": "2.0", "id": 8, "method": "resources/read", "params": {}})
    assert r8 is not None and r8["error"]["code"] == INVALID_PARAMS

    # Unknown prompt
    r9 = server.handle_request(
        {"jsonrpc": "2.0", "id": 9, "method": "prompts/get", "params": {"name": "bad_prompt"}}
    )
    assert r9 is not None and r9["error"]["code"] == INVALID_PARAMS

    # Missing prompt argument
    r10 = server.handle_request(
        {"jsonrpc": "2.0", "id": 10, "method": "prompts/get", "params": {"name": "architecture-briefing"}}
    )
    assert r10 is not None and r10["error"]["code"] == INVALID_PARAMS

    # Missing prompt name
    r11 = server.handle_request({"jsonrpc": "2.0", "id": 11, "method": "prompts/get", "params": {}})
    assert r11 is not None and r11["error"]["code"] == INVALID_PARAMS


def test_mcp_stdio_stream_and_parse_errors() -> None:
    server = CortexMCPServer(graph=build_demo_scenario())
    input_lines = [
        "",
        "   ",
        "{malformed json",
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}),
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
    ]
    stdin = io.StringIO("\n".join(input_lines) + "\n")
    stdout = io.StringIO()
    server.serve_stdio(stdin=stdin, stdout=stdout)

    output_lines = [json.loads(line) for line in stdout.getvalue().strip().splitlines()]
    assert len(output_lines) == 3
    assert output_lines[0]["error"]["code"] == PARSE_ERROR
    assert output_lines[1]["id"] == 1 and output_lines[1]["result"] == {}
    assert output_lines[2]["id"] == 2 and len(output_lines[2]["result"]["tools"]) == 7


# ============================================================================
# 7. CLI Subcommands & Reproducible Benchmark Runner
# ============================================================================


def test_percentile_helper() -> None:
    assert percentile([], 50) == 0.0
    assert percentile([10.0], 95) == 10.0
    assert percentile([1.0, 2.0, 3.0, 4.0, 5.0], 50) == 3.0


def test_cli_demo_and_benchmark_programmatic(capsys: pytest.CaptureFixture[str]) -> None:
    rc_demo = cli_main(["demo", "--json"])
    assert rc_demo == 0
    demo_out = json.loads(capsys.readouterr().out)
    assert demo_out["integrity"]["valid"] is True
    assert demo_out["integrity"]["superseded_facts"] == 2

    rc_bench = cli_main(["benchmark", "--facts", "60", "--episodes", "20", "--json"])
    assert rc_bench == 0
    bench_out = json.loads(capsys.readouterr().out)
    assert bench_out["guarantees"]["stale_fact_suppression_rate_pct"] == 100.0
    assert bench_out["guarantees"]["token_budget_compliance_rate_pct"] == 100.0
    assert bench_out["guarantees"]["cryptographic_integrity_valid"] is True


def test_cli_serve_stdio_subcommand(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    stdin = io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 99, "method": "ping"}) + "\n")
    stdout = io.StringIO()
    monkeypatch.setattr("sys.stdin", stdin)
    monkeypatch.setattr("sys.stdout", stdout)
    storage_file = tmp_path / "cli_stdio.json"
    rc = cli_main(["serve-stdio", "--storage", str(storage_file), "--seed-demo"])
    assert rc == 0
    resp = json.loads(stdout.getvalue().strip())
    assert resp["id"] == 99
    assert storage_file.exists()


# ============================================================================
# 8. Extended Parametrized & Edge-Case Coverage (55+ Total Tests)
# ============================================================================


@pytest.mark.parametrize(
    "category",
    ["adr", "bug_root_cause", "invariant", "session_note", "migration", "incident"],
)
def test_parametrized_episode_category_roundtrip(category: str) -> None:
    graph = BiTemporalMemoryGraph()
    ep = graph.record_episode(
        title=f"Episode for {category}",
        category=category,
        content=f"Testing {category} persistence and hash calculation.",
        files_touched=[f"src/{category}.py"],
        entities_mentioned=[f"svc_{category}"],
    )
    restored = Episode.from_dict(ep.to_dict())
    assert restored.id == ep.id
    assert restored.sha256 == ep.sha256
    assert restored.calculate_hash() == ep.sha256


@pytest.mark.parametrize(
    "max_tokens",
    [35, 60, 100, 180, 260, 400, 750, 1200],
)
def test_parametrized_token_budgets_never_overflow(max_tokens: int) -> None:
    graph = build_demo_scenario()
    compiler = ContextCompiler(graph)
    bundle = compiler.compile_context(
        query="auth_service payment_ledger order_repository token format N+1 idempotency",
        max_tokens=max_tokens,
    )
    assert bundle.used_tokens <= max_tokens
    assert bundle.max_tokens == max_tokens


@pytest.mark.parametrize(
    "hop_count,expected_min_entities",
    [(1, 2), (2, 3), (3, 3)],
)
def test_parametrized_hop_traversal_depths(hop_count: int, expected_min_entities: int) -> None:
    graph = build_demo_scenario()
    sub = graph.traverse_subgraph("order_repository", max_hops=hop_count)
    assert len(sub["entities"]) >= expected_min_entities


@pytest.mark.parametrize(
    "tool_name",
    [
        "memory_record_episode",
        "memory_upsert_fact",
        "memory_compile_context",
        "memory_query_entity",
        "memory_time_travel",
        "memory_verify_integrity",
    ],
)
def test_parametrized_mcp_tool_schema_integrity(tool_name: str) -> None:
    server = CortexMCPServer()
    tools = {t["name"]: t for t in server.get_tool_definitions()}
    assert tool_name in tools
    schema = tools[tool_name]["inputSchema"]
    assert schema["type"] == "object"
    assert "properties" in schema


def test_register_on_change_callback_invoked() -> None:
    graph = BiTemporalMemoryGraph()
    events: list[int] = []
    graph.register_on_change(lambda: events.append(1))
    graph.upsert_entity("node_a")
    graph.upsert_fact("node_a", "rel", object_value="val")
    graph.record_episode("Title", "adr", "Body")
    assert len(events) == 3


def test_get_facts_filtering_by_object_id_and_predicate() -> None:
    graph = build_demo_scenario()
    incoming = graph.get_facts(object_id="payment_ledger")
    assert len(incoming) == 1
    assert incoming[0].subject_id == "order_repository"

    pred_filtered = graph.get_facts(predicate="verifies_caller_via")
    assert len(pred_filtered) == 1
    assert pred_filtered[0].object_id == "auth_service"


def test_traverse_subgraph_with_multiple_seeds() -> None:
    graph = build_demo_scenario()
    sub = graph.traverse_subgraph(["auth_service", "order_repository"], max_hops=1)
    ids = {e["id"] for e in sub["entities"]}
    assert {"auth_service", "order_repository", "payment_ledger"}.issubset(ids)


def test_compiler_empty_query_returns_prioritized_items() -> None:
    graph = build_demo_scenario()
    compiler = ContextCompiler(graph)
    bundle = compiler.compile_context(query="", max_tokens=400)
    assert bundle.used_tokens <= 400
    assert len(bundle.items) > 0


def test_cli_demo_and_benchmark_human_readable_output(capsys: pytest.CaptureFixture[str]) -> None:
    run_demo(output_json=False)
    out_demo = capsys.readouterr().out
    assert "CORTEX-MCP: BI-TEMPORAL KNOWLEDGE GRAPH" in out_demo
    assert "PASETO_v4_public" in out_demo

    run_benchmark(num_facts=40, num_episodes=10, output_json=False)
    out_bench = capsys.readouterr().out
    assert "Cortex-MCP Reproducible Benchmark Report" in out_bench
    assert "100.0%" in out_bench
