"""Tests for Cortex-MCP HTTP and SSE remote transport server."""

import json
import threading
import time
import urllib.request

import pytest

from cortex_mcp.graph import BiTemporalMemoryGraph
from cortex_mcp.http_server import run_http_server
from cortex_mcp.server import CortexMCPServer


@pytest.fixture
def http_server():
    graph = BiTemporalMemoryGraph()
    server = CortexMCPServer(graph=graph)
    # Bind to port 0 (dynamic port) on localhost
    httpd = run_http_server(server, host="127.0.0.1", port=0)
    port = httpd.server_port
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def test_health_check(http_server):
    req = urllib.request.Request(f"{http_server}/health")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["status"] == "healthy"
        assert data["server"] == "cortex-mcp"
        assert "http" in data["transport"]


def test_json_rpc_tools_list_over_http(http_server):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    }
    req = urllib.request.Request(
        f"{http_server}/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        tools = data["result"]["tools"]
        assert len(tools) == 7
        tool_names = [t["name"] for t in tools]
        assert "memory_record_episode" in tool_names
        assert "memory_compile_context" in tool_names


def test_cors_options(http_server):
    req = urllib.request.Request(f"{http_server}/messages", method="OPTIONS")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 204
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"
