"""Unit tests for the developer portal and upgraded HTTP/SSE endpoints."""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
API_DIR = ROOT_DIR / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from portal import render_developer_portal


def test_portal_html_render():
    html = render_developer_portal(
        server_name="cortex-mcp",
        server_version="1.1.0",
        tagline="Test Tagline",
        endpoint_url="https://test.vercel.app/mcp",
        github_url="https://github.com/codesphere-u/cortex-mcp",
        tools=[{"name": "test_tool", "description": "A test tool", "inputSchema": {"properties": {"x": {"type": "string"}}, "required": ["x"]}}],
        resources=[{"uri": "test://res", "name": "Test Resource", "mimeType": "application/json", "description": "A test resource"}],
        prompts=[{"name": "test-prompt", "description": "A test prompt", "arguments": [{"name": "comp", "required": True}]}],
        sample_tool_call={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "test_tool", "arguments": {"x": "val"}}},
    )
    assert "<!DOCTYPE html>" in html
    assert "cortex-mcp" in html
    assert "test_tool" in html
    assert "test://res" in html
    assert "test-prompt" in html
    assert "Operational" in html
    assert "claude mcp add" in html


def test_fastapi_portal_endpoints():
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from api.index import app

    client = TestClient(app)
    # Default health check returns JSON
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["server"] == "cortex-mcp"
    assert "streamable-http" in data["transport"]

    # HTML requested on root
    res_html = client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers["content-type"]
    assert "<!DOCTYPE html>" in res_html.text
    assert "cortex-mcp" in res_html.text

    # SSE requested on /mcp
    res_sse = client.get("/mcp", headers={"Accept": "text/event-stream"})
    assert res_sse.status_code == 200
    assert "text/event-stream" in res_sse.headers["content-type"]
    assert "event: endpoint" in res_sse.text
