"""
cortex_mcp.grounding_export
===========================
Grounded Citation Bundle Exporter for `truthgate` (`export_truthgate_sources`).

Exports compiled context packets (or active bi-temporal graph items) as a
`TruthGate`-compatible `SourceDocument` JSON bundle:
  `{"source_id": fact_id, "title": ..., "content": ..., "metadata": {...}}`
including temporal provenance (`valid_from`, `valid_until`, `is_active`,
`content_hash`) and the SHA-256 Merkle root of the graph (`graph_merkle_digest`)
so `codesphere-u/truthgate` can deterministically verify that an agent's
`[fact_id]` / `[ep_id]` citations match active bi-temporal memory with zero
stale-fact leakage!
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from cortex_mcp.compiler import CompiledContextBundle, ContextCompiler
from cortex_mcp.graph import BiTemporalMemoryGraph, Episode, Entity, TemporalFact, compute_sha256


@dataclass(frozen=True)
class GroundedSourceDocument:
    """TruthGate-compatible SourceDocument record with bi-temporal provenance metadata."""

    source_id: str
    title: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "content": self.content,
            "metadata": dict(self.metadata),
        }


def _fact_to_source_document(
    fact: TemporalFact,
    graph_merkle_digest: str,
    score: Optional[float] = None,
) -> GroundedSourceDocument:
    pred_phrase = fact.predicate.replace("_", " ")
    natural_sentence = (
        f"{fact.subject_id} {fact.predicate} ({pred_phrase}) is {fact.target_display}."
    )
    meta: Dict[str, Any] = {
        "item_type": "fact",
        "fact_id": fact.id,
        "subject_id": fact.subject_id,
        "predicate": fact.predicate,
        "object_id": fact.object_id,
        "object_value": fact.object_value,
        "confidence": fact.confidence,
        "source_episode_id": fact.source_episode_id,
        "valid_from": fact.valid_from,
        "valid_until": fact.valid_until,
        "superseded_by": fact.superseded_by,
        "is_active": fact.is_active_at(None),
        "content_hash": fact.content_hash,
        "graph_merkle_digest": graph_merkle_digest,
    }
    if score is not None:
        meta["compiler_score"] = score
    return GroundedSourceDocument(
        source_id=fact.id,
        title=f"Bi-Temporal Fact {fact.id}: {fact.subject_id}.{fact.predicate}",
        content=natural_sentence,
        metadata=meta,
    )


def _episode_to_source_document(
    ep: Episode,
    graph_merkle_digest: str,
    score: Optional[float] = None,
) -> GroundedSourceDocument:
    meta: Dict[str, Any] = {
        "item_type": "episode",
        "episode_id": ep.id,
        "category": ep.category,
        "files_touched": list(ep.files_touched),
        "entities_mentioned": list(ep.entities_mentioned),
        "timestamp": ep.timestamp,
        "is_active": True,
        "content_hash": ep.sha256,
        "graph_merkle_digest": graph_merkle_digest,
    }
    if score is not None:
        meta["compiler_score"] = score
    return GroundedSourceDocument(
        source_id=ep.id,
        title=f"{ep.category.upper()}: {ep.title}",
        content=f"{ep.title}. {ep.content}",
        metadata=meta,
    )


def _entity_to_source_document(
    ent: Entity,
    graph_merkle_digest: str,
    score: Optional[float] = None,
) -> GroundedSourceDocument:
    ent_hash = compute_sha256(ent.to_dict())
    meta: Dict[str, Any] = {
        "item_type": "entity",
        "entity_id": ent.id,
        "entity_type": ent.entity_type,
        "created_at": ent.created_at,
        "is_active": True,
        "content_hash": ent_hash,
        "graph_merkle_digest": graph_merkle_digest,
    }
    if score is not None:
        meta["compiler_score"] = score
    return GroundedSourceDocument(
        source_id=ent.id,
        title=f"Entity {ent.name} ({ent.entity_type})",
        content=f"{ent.id} ({ent.name}) is a {ent.entity_type}. {ent.summary}".strip(),
        metadata=meta,
    )


def export_truthgate_sources(
    graph: BiTemporalMemoryGraph,
    *,
    query: Optional[str] = None,
    bundle: Optional[CompiledContextBundle] = None,
    max_tokens: int = 1200,
    include_superseded: bool = False,
    include_episodes: bool = True,
    as_of: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """
    Export active facts (and optionally episodes/entities) or a compiled context
    packet as a `TruthGate`-compatible `SourceDocument` JSON list.

    If `bundle` or `query` is provided, exports the items selected by
    `ContextCompiler.compile_context(...)`. Otherwise, exports all active
    `TemporalFacts` (and `Episodes` if `include_episodes=True`) in the graph.
    """
    integrity = graph.verify_integrity()
    merkle_digest = integrity["graph_merkle_digest"]
    documents: List[GroundedSourceDocument] = []

    if bundle is None and query is not None:
        compiler = ContextCompiler(graph)
        bundle = compiler.compile_context(
            query=query,
            max_tokens=max_tokens,
            include_superseded=include_superseded,
            as_of=as_of,
        )

    if bundle is not None:
        for item in bundle.items:
            if item.is_superseded and not include_superseded:
                continue
            if item.item_type == "fact" and item.item_id in graph.facts:
                fact = graph.facts[item.item_id]
                documents.append(_fact_to_source_document(fact, merkle_digest, score=item.score))
            elif item.item_type == "episode" and include_episodes and item.item_id in graph.episodes:
                ep = graph.episodes[item.item_id]
                documents.append(_episode_to_source_document(ep, merkle_digest, score=item.score))
            elif item.item_type == "entity" and item.item_id in graph.entities:
                ent = graph.entities[item.item_id]
                documents.append(_entity_to_source_document(ent, merkle_digest, score=item.score))
    else:
        facts = graph.get_facts(as_of=as_of, include_superseded=include_superseded)
        facts.sort(key=lambda f: f.id)
        for fact in facts:
            documents.append(_fact_to_source_document(fact, merkle_digest))

        if include_episodes:
            for ep_id in sorted(graph.episodes.keys()):
                ep = graph.episodes[ep_id]
                documents.append(_episode_to_source_document(ep, merkle_digest))

    serialized = [doc.to_dict() for doc in documents]
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(serialized, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return serialized
