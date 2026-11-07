"""MCP Server module re-exporting `CortexMCPServer` and `cortex_audit_contradictions`."""

from cortex_mcp.server import (
    CortexMCPServer,
    INVALID_PARAMS,
    INVALID_REQUEST,
    MCP_PROTOCOL_VERSION,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    SERVER_NAME,
    SERVER_VERSION,
)

__all__ = [
    "CortexMCPServer",
    "MCP_PROTOCOL_VERSION",
    "SERVER_NAME",
    "SERVER_VERSION",
    "PARSE_ERROR",
    "INVALID_REQUEST",
    "METHOD_NOT_FOUND",
    "INVALID_PARAMS",
]
