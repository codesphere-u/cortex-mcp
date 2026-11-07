"""Standards-Compliant Model Context Protocol (MCP) JSON-RPC 2.0 Server.

Implements MCP protocol specification (2024-11-05 / 2025-03-26) over stdio and
in-memory transports, exposing bi-temporal memory tools, resources, and prompts.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, IO, List, Optional, Union

from cortex_mcp.compiler import ContextCompiler
from cortex_mcp.graph import BiTemporalMemoryGraph, VALID_EPISODE_CATEGORIES

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "cortex-mcp"
SERVER_VERSION = "1.0.0"

# Standard JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class CortexMCPServer:
    """Model Context Protocol JSON-RPC 2.0 Server backed by BiTemporalMemoryGraph."""

    def __init__(
        self,
        graph: Optional[BiTemporalMemoryGraph] = None,
        storage_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.graph = graph or BiTemporalMemoryGraph(storage_path=storage_path)
        self.compiler = ContextCompiler(self.graph)
        self.initialized = False

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return the 6 MCP tool definitions with concise, strict JSON schemas."""
        return [
            {
                "name": "memory_record_episode",
                "description": (
                    "Record an immutable engineering episode (ADR, bug_root_cause, invariant, "
                    "session_note, migration, incident) with associated files and mentioned entities."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Short descriptive title of the episode."},
                        "category": {
                            "type": "string",
                            "enum": sorted(VALID_EPISODE_CATEGORIES),
                            "description": "Episode classification category.",
                        },
                        "content": {"type": "string", "description": "Detailed architectural or technical note."},
                        "files_touched": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Relative repository file paths involved.",
                        },
                        "entities_mentioned": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Canonical entity IDs referenced in this episode.",
                        },
                        "timestamp": {
                            "type": "string",
                            "description": "Optional ISO-8601 UTC timestamp.",
                        },
                    },
                    "required": ["title", "category", "content"],
                },
            },
            {
                "name": "memory_upsert_fact",
                "description": (
                    "Record a structured entity-relationship fact (subject_id, predicate, object) "
                    "with automatic bi-temporal conflict detection and supersession of stale facts."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "subject_id": {"type": "string", "description": "Source entity identifier."},
                        "predicate": {"type": "string", "description": "Relationship or attribute predicate."},
                        "object_id": {"type": "string", "description": "Target entity identifier (if relational)."},
                        "object_value": {"type": "string", "description": "Target literal value (if attribute)."},
                        "singular": {
                            "type": "boolean",
                            "default": True,
                            "description": "If true, supersedes any prior active fact with the same (subject_id, predicate).",
                        },
                        "confidence": {
                            "type": "number",
                            "default": 1.0,
                            "description": "Confidence score in [0.0, 1.0].",
                        },
                        "source_episode_id": {
                            "type": "string",
                            "description": "Optional episode ID that established this fact.",
                        },
                        "valid_from": {
                            "type": "string",
                            "description": "Optional ISO-8601 UTC timestamp when fact became true.",
                        },
                    },
                    "required": ["subject_id", "predicate"],
                },
            },
            {
                "name": "memory_compile_context",
                "description": (
                    "Compile a token-budgeted, provenance-cited context bundle for a coding query, "
                    "automatically suppressing superseded/stale facts."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Task description, symbol, or file query."},
                        "max_tokens": {
                            "type": "integer",
                            "default": 1200,
                            "description": "Strict maximum token budget for the compiled context.",
                        },
                        "include_superseded": {
                            "type": "boolean",
                            "default": False,
                            "description": "Whether to include historically superseded facts.",
                        },
                        "as_of": {
                            "type": "string",
                            "description": "Optional ISO-8601 timestamp for point-in-time compilation.",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "memory_query_entity",
                "description": (
                    "Inspect an entity's active facts, superseded historical facts, related episodes, "
                    "and K-hop ego-graph neighborhood."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string", "description": "Entity ID to inspect."},
                        "include_superseded": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include historical facts superseded by newer decisions.",
                        },
                        "max_hops": {
                            "type": "integer",
                            "default": 2,
                            "description": "Maximum hop distance for ego-graph traversal.",
                        },
                    },
                    "required": ["entity_id"],
                },
            },
            {
                "name": "memory_time_travel",
                "description": (
                    "Query the knowledge graph as of a specific ISO-8601 timestamp to inspect "
                    "historical architecture state."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "as_of": {
                            "type": "string",
                            "description": "ISO-8601 UTC timestamp to inspect.",
                        },
                    },
                    "required": ["as_of"],
                },
            },
            {
                "name": "memory_verify_integrity",
                "description": (
                    "Verify cryptographic SHA-256 hashes of all episodes and facts and compute "
                    "the graph Merkle digest."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def get_resource_definitions(self) -> List[Dict[str, Any]]:
        """Return MCP resource descriptors."""
        return [
            {
                "uri": "cortex://graph/summary",
                "name": "Bi-Temporal Knowledge Graph Summary",
                "description": "Overview of entities, active vs superseded facts, and episodes.",
                "mimeType": "application/json",
            },
            {
                "uri": "cortex://graph/integrity",
                "name": "Cryptographic Integrity Report",
                "description": "SHA-256 verification status and Merkle digest of the memory graph.",
                "mimeType": "application/json",
            },
            {
                "uri": "cortex://episodes/recent",
                "name": "Recent Engineering Episodes",
                "description": "Most recent ADRs, bug root causes, and invariants recorded.",
                "mimeType": "application/json",
            },
        ]

    def get_prompt_definitions(self) -> List[Dict[str, Any]]:
        """Return MCP prompt templates."""
        return [
            {
                "name": "architecture-briefing",
                "description": "Compile a token-budgeted architectural context briefing for a module or service.",
                "arguments": [
                    {
                        "name": "component",
                        "description": "Target component or service ID.",
                        "required": True,
                    },
                    {
                        "name": "max_tokens",
                        "description": "Maximum token budget (default 1000).",
                        "required": False,
                    },
                ],
            },
            {
                "name": "bug-investigation-context",
                "description": "Retrieve invariants, past bug root causes, and active dependencies for debugging.",
                "arguments": [
                    {
                        "name": "symptom",
                        "description": "Bug symptom, error message, or file path.",
                        "required": True,
                    }
                ],
            },
        ]

    def _call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch an MCP `tools/call` invocation."""
        if name == "memory_record_episode":
            episode = self.graph.record_episode(
                title=str(arguments["title"]),
                category=str(arguments["category"]),
                content=str(arguments["content"]),
                files_touched=arguments.get("files_touched"),
                entities_mentioned=arguments.get("entities_mentioned"),
                timestamp=arguments.get("timestamp"),
            )
            payload = {
                "status": "recorded",
                "episode": episode.to_dict(),
            }
            return self._tool_response(payload)

        if name == "memory_upsert_fact":
            active_fact, superseded = self.graph.upsert_fact(
                subject_id=str(arguments["subject_id"]),
                predicate=str(arguments["predicate"]),
                object_id=arguments.get("object_id"),
                object_value=arguments.get("object_value"),
                singular=bool(arguments.get("singular", True)),
                confidence=float(arguments.get("confidence", 1.0)),
                source_episode_id=arguments.get("source_episode_id"),
                valid_from=arguments.get("valid_from"),
            )
            payload = {
                "status": "upserted",
                "active_fact": active_fact.to_dict(),
                "superseded_count": len(superseded),
                "superseded_facts": [f.to_dict() for f in superseded],
            }
            return self._tool_response(payload)

        if name == "memory_compile_context":
            bundle = self.compiler.compile_context(
                query=str(arguments["query"]),
                max_tokens=int(arguments.get("max_tokens", 1200)),
                include_superseded=bool(arguments.get("include_superseded", False)),
                as_of=arguments.get("as_of"),
            )
            return self._tool_response(bundle.to_dict())

        if name == "memory_query_entity":
            result = self.graph.query_entity(
                entity_id=str(arguments["entity_id"]),
                include_superseded=bool(arguments.get("include_superseded", True)),
                max_hops=int(arguments.get("max_hops", 2)),
            )
            return self._tool_response(result)

        if name == "memory_time_travel":
            snapshot = self.graph.snapshot_as_of(as_of=str(arguments["as_of"]))
            return self._tool_response(snapshot)

        if name == "memory_verify_integrity":
            report = self.graph.verify_integrity()
            return self._tool_response(report)

        raise KeyError(f"Unknown tool: {name}")

    @staticmethod
    def _tool_response(payload: Dict[str, Any], is_error: bool = False) -> Dict[str, Any]:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, indent=2, sort_keys=True),
                }
            ],
            "structuredContent": payload,
            "isError": is_error,
        }

    def _read_resource(self, uri: str) -> Dict[str, Any]:
        if uri == "cortex://graph/summary":
            integrity = self.graph.verify_integrity()
            summary = {
                "server": SERVER_NAME,
                "version": SERVER_VERSION,
                "entities": len(self.graph.entities),
                "active_facts": integrity["active_facts"],
                "superseded_facts": integrity["superseded_facts"],
                "episodes": len(self.graph.episodes),
                "graph_merkle_digest": integrity["graph_merkle_digest"],
            }
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(summary, indent=2, sort_keys=True),
                    }
                ]
            }

        if uri == "cortex://graph/integrity":
            report = self.graph.verify_integrity()
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(report, indent=2, sort_keys=True),
                    }
                ]
            }

        if uri == "cortex://episodes/recent":
            episodes_sorted = sorted(
                self.graph.episodes.values(),
                key=lambda ep: ep.timestamp,
                reverse=True,
            )[:20]
            data = {"episodes": [ep.to_dict() for ep in episodes_sorted]}
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(data, indent=2, sort_keys=True),
                    }
                ]
            }

        raise KeyError(f"Resource URI not found: {uri}")

    def _get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = arguments or {}
        if name == "architecture-briefing":
            component = str(args.get("component", "")).strip()
            if not component:
                raise ValueError("Missing required prompt argument: 'component'")
            max_tokens = int(args.get("max_tokens", 1000))
            bundle = self.compiler.compile_context(query=component, max_tokens=max_tokens)
            return {
                "description": f"Architectural briefing for {component}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Review the following verified bi-temporal architecture context for `{component}` "
                                f"before proposing code changes:\n\n{bundle.rendered_markdown}"
                            ),
                        },
                    }
                ],
            }

        if name == "bug-investigation-context":
            symptom = str(args.get("symptom", "")).strip()
            if not symptom:
                raise ValueError("Missing required prompt argument: 'symptom'")
            bundle = self.compiler.compile_context(query=symptom, max_tokens=1200)
            return {
                "description": f"Bug investigation context for: {symptom}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Investigate `{symptom}` using the following active system invariants "
                                f"and historical root causes:\n\n{bundle.rendered_markdown}"
                            ),
                        },
                    }
                ],
            }

        raise KeyError(f"Unknown prompt: {name}")

    def handle_request(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single JSON-RPC 2.0 request or notification dictionary.

        Returns None for notifications (messages without an `id`).
        """
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return {
                "jsonrpc": "2.0",
                "id": message.get("id") if isinstance(message, dict) else None,
                "error": {"code": INVALID_REQUEST, "message": "Invalid JSON-RPC 2.0 request."},
            }

        method = message.get("method")
        msg_id = message.get("id")
        is_notification = "id" not in message
        params = message.get("params") or {}

        if not isinstance(method, str):
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": INVALID_REQUEST, "message": "Missing or non-string method name."},
            }

        # Notifications do not produce a response
        if is_notification:
            if method in ("notifications/initialized", "notifications/cancelled"):
                self.initialized = True
            return None

        try:
            if method == "initialize":
                self.initialized = True
                client_version = params.get("protocolVersion", MCP_PROTOCOL_VERSION)
                result = {
                    "protocolVersion": client_version if isinstance(client_version, str) else MCP_PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": SERVER_VERSION,
                    },
                }
                return {"jsonrpc": "2.0", "id": msg_id, "result": result}

            if method == "ping":
                return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

            if method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"tools": self.get_tool_definitions()},
                }

            if method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments") or {}
                if not tool_name or not isinstance(tool_name, str):
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {"code": INVALID_PARAMS, "message": "Missing tool 'name' in tools/call."},
                    }
                try:
                    tool_result = self._call_tool(tool_name, tool_args)
                    return {"jsonrpc": "2.0", "id": msg_id, "result": tool_result}
                except KeyError as exc:
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {"code": INVALID_PARAMS, "message": str(exc)},
                    }
                except (ValueError, TypeError) as exc:
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": self._tool_response({"error": str(exc)}, is_error=True),
                    }

            if method == "resources/list":
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"resources": self.get_resource_definitions()},
                }

            if method == "resources/read":
                uri = params.get("uri")
                if not uri or not isinstance(uri, str):
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {"code": INVALID_PARAMS, "message": "Missing 'uri' parameter."},
                    }
                try:
                    res = self._read_resource(uri)
                    return {"jsonrpc": "2.0", "id": msg_id, "result": res}
                except KeyError as exc:
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {"code": INVALID_PARAMS, "message": str(exc)},
                    }

            if method == "prompts/list":
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"prompts": self.get_prompt_definitions()},
                }

            if method == "prompts/get":
                prompt_name = params.get("name")
                prompt_args = params.get("arguments")
                if not prompt_name or not isinstance(prompt_name, str):
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {"code": INVALID_PARAMS, "message": "Missing prompt 'name'."},
                    }
                try:
                    prompt_res = self._get_prompt(prompt_name, prompt_args)
                    return {"jsonrpc": "2.0", "id": msg_id, "result": prompt_res}
                except (KeyError, ValueError) as exc:
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {"code": INVALID_PARAMS, "message": str(exc)},
                    }

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": METHOD_NOT_FOUND, "message": f"Method not found: {method}"},
            }
        except Exception as exc:  # pragma: no cover - defensive guard
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": INTERNAL_ERROR, "message": str(exc)},
            }

    def handle_raw_line(self, line: str) -> Optional[str]:
        """Parse a single line of JSON-RPC 2.0 input and return a JSON response line (or None)."""
        stripped = line.strip()
        if not stripped:
            return None
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": PARSE_ERROR, "message": f"Parse error: {exc}"},
            }
            return json.dumps(err)

        response = self.handle_request(payload)
        if response is None:
            return None
        return json.dumps(response)

    def serve_stdio(
        self,
        stdin: Optional[IO[str]] = None,
        stdout: Optional[IO[str]] = None,
    ) -> None:
        """Run the MCP server loop over line-delimited JSON-RPC 2.0 stdio."""
        in_stream = stdin or sys.stdin
        out_stream = stdout or sys.stdout
        for line in in_stream:
            resp_line = self.handle_raw_line(line)
            if resp_line is not None:
                out_stream.write(resp_line + "\n")
                out_stream.flush()
