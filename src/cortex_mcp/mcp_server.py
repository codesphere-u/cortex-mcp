"""MCP Server module re-exporting `CortexMCPServer` and `cortex_audit_contradictions`."""

from cortex_mcp.server import (
    INVALID_PARAMS,
    INVALID_REQUEST,
    MCP_PROTOCOL_VERSION,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    SERVER_NAME,
    SERVER_VERSION,
    CortexMCPServer,
)

__all__ = [
    "INVALID_PARAMS",
    "INVALID_REQUEST",
    "MCP_PROTOCOL_VERSION",
    "METHOD_NOT_FOUND",
    "PARSE_ERROR",
    "SERVER_NAME",
    "SERVER_VERSION",
    "CortexMCPServer",
]
