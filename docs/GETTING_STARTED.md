# Getting Started with Cortex-MCP

`cortex-mcp` (`v1.2.0`) gives AI coding agents persistent, bi-temporal memory over Model Context Protocol (`stdio`, HTTP/SSE, and FastAPI Streamable HTTP).

## Installation

```bash
git clone https://github.com/codesphere-u/cortex-mcp.git
cd cortex-mcp
pip install -e ".[dev]"
```

## Run Local Demo & Benchmarks

```bash
cortex-mcp demo
cortex-mcp benchmark
```

Observed local benchmark output on 500 facts / 100 episodes / 60 entities:
- `upsert_fact` P50: `0.004 ms` (P95 `0.006 ms`)
- `compile_context` (800 tokens) P50: `5.750 ms` (P95 `7.410 ms`)
- `verify_integrity` (600 SHA-256 hashes + Merkle root): `1.756 ms`
- Stale-Fact Suppression: `100.0%` | Token-Budget Compliance: `100.0%`

## Connect MCP Clients

```bash
claude mcp add --transport http cortex-mcp https://cortex-mcp-steel.vercel.app/mcp
```

Or run locally with persistent JSON storage:

```bash
cortex-mcp serve-stdio --storage .cortex/memory.json --seed-demo
```
