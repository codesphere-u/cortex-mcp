"""Bi-Temporal Entity-Relationship & Episodic Memory Graph.

Provides deterministic storage, conflict detection, automatic temporal supersession,
point-in-time historical queries, K-hop ego-graph traversal, and cryptographic SHA-256
integrity verification without external cloud dependencies.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def parse_iso_timestamp(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp string into a timezone-aware UTC datetime."""
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_sha256(payload: dict[str, Any]) -> str:
    """Compute a canonical SHA-256 hex digest over a JSON-serializable dict."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class Entity:
    """Represents a canonical node in the engineering knowledge graph."""

    id: str
    name: str
    entity_type: str
    summary: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Entity:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            entity_type=str(data["entity_type"]),
            summary=str(data.get("summary", "")),
            attributes=dict(data.get("attributes", {})),
            created_at=str(data.get("created_at") or utc_now_iso()),
        )


@dataclass
class TemporalFact:
    """Represents a bi-temporal directed fact `(subject_id, predicate, object)`."""

    id: str
    subject_id: str
    predicate: str
    object_id: str | None = None
    object_value: str | None = None
    singular: bool = True
    confidence: float = 1.0
    source_episode_id: str | None = None
    valid_from: str = field(default_factory=utc_now_iso)
    valid_until: str | None = None
    superseded_by: str | None = None
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.object_id and self.object_value is None:
            raise ValueError("TemporalFact requires either object_id or object_value.")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("TemporalFact confidence must be between 0.0 and 1.0.")
        if not self.content_hash:
            self.content_hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Compute canonical SHA-256 hash over immutable core fact fields."""
        return compute_sha256(
            {
                "id": self.id,
                "subject_id": self.subject_id,
                "predicate": self.predicate,
                "object_id": self.object_id,
                "object_value": self.object_value,
                "singular": self.singular,
                "confidence": round(float(self.confidence), 6),
                "source_episode_id": self.source_episode_id,
                "valid_from": self.valid_from,
            }
        )

    @property
    def target_display(self) -> str:
        """Return human-readable object representation."""
        return self.object_id if self.object_id is not None else str(self.object_value)

    def is_active_at(self, as_of: str | datetime | None = None) -> bool:
        """Return True if the fact is active at `as_of` (or currently active if `as_of` is None)."""
        if as_of is None:
            return self.valid_until is None and self.superseded_by is None
        target_dt = parse_iso_timestamp(as_of) if isinstance(as_of, str) else as_of.astimezone(timezone.utc)
        start_dt = parse_iso_timestamp(self.valid_from)
        if target_dt < start_dt:
            return False
        if self.valid_until is not None:
            end_dt = parse_iso_timestamp(self.valid_until)
            if target_dt >= end_dt:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TemporalFact:
        return cls(
            id=str(data["id"]),
            subject_id=str(data["subject_id"]),
            predicate=str(data["predicate"]),
            object_id=data.get("object_id"),
            object_value=data.get("object_value"),
            singular=bool(data.get("singular", True)),
            confidence=float(data.get("confidence", 1.0)),
            source_episode_id=data.get("source_episode_id"),
            valid_from=str(data.get("valid_from") or utc_now_iso()),
            valid_until=data.get("valid_until"),
            superseded_by=data.get("superseded_by"),
            content_hash=str(data.get("content_hash", "")),
        )


VALID_EPISODE_CATEGORIES = frozenset(
    {"adr", "bug_root_cause", "invariant", "session_note", "migration", "incident"}
)


@dataclass
class Episode:
    """Represents an immutable engineering episode (ADR, bug root cause, invariant, etc.)."""

    id: str
    title: str
    category: str
    content: str
    files_touched: list[str] = field(default_factory=list)
    entities_mentioned: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=utc_now_iso)
    sha256: str = ""

    def __post_init__(self) -> None:
        if self.category not in VALID_EPISODE_CATEGORIES:
            raise ValueError(
                f"Invalid episode category '{self.category}'. Must be one of {sorted(VALID_EPISODE_CATEGORIES)}."
            )
        if not self.sha256:
            self.sha256 = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Compute canonical SHA-256 hash over episode fields."""
        return compute_sha256(
            {
                "id": self.id,
                "title": self.title,
                "category": self.category,
                "content": self.content,
                "files_touched": list(self.files_touched),
                "entities_mentioned": list(self.entities_mentioned),
                "timestamp": self.timestamp,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Episode:
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            category=str(data["category"]),
            content=str(data["content"]),
            files_touched=list(data.get("files_touched", [])),
            entities_mentioned=list(data.get("entities_mentioned", [])),
            timestamp=str(data.get("timestamp") or utc_now_iso()),
            sha256=str(data.get("sha256", "")),
        )


class BiTemporalMemoryGraph:
    """Local-first bi-temporal entity-relationship and episodic memory graph."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self.storage_path: Path | None = Path(storage_path) if storage_path else None
        self.entities: dict[str, Entity] = {}
        self.facts: dict[str, TemporalFact] = {}
        self.episodes: dict[str, Episode] = {}
        self._subject_index: dict[str, list[str]] = {}
        self._object_index: dict[str, list[str]] = {}
        self._on_change_callbacks: list[Callable[[], None]] = []

        if self.storage_path and self.storage_path.exists():
            self.load(self.storage_path)

    def register_on_change(self, callback: Callable[[], None]) -> None:
        """Register a listener notified whenever entities, facts, or episodes change."""
        self._on_change_callbacks.append(callback)

    def _notify_change(self) -> None:
        for cb in self._on_change_callbacks:
            cb()
        if self.storage_path:
            self.save(self.storage_path)

    def _index_fact(self, fact: TemporalFact) -> None:
        subj_list = self._subject_index.setdefault(fact.subject_id, [])
        if fact.id not in subj_list:
            subj_list.append(fact.id)
        if fact.object_id:
            obj_list = self._object_index.setdefault(fact.object_id, [])
            if fact.id not in obj_list:
                obj_list.append(fact.id)

    def upsert_entity(
        self,
        entity_id: str,
        name: str | None = None,
        entity_type: str = "component",
        summary: str = "",
        attributes: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> Entity:
        """Create or update an entity node in the graph."""
        entity_id = entity_id.strip()
        if not entity_id:
            raise ValueError("entity_id cannot be empty.")
        existing = self.entities.get(entity_id)
        if existing:
            if name:
                existing.name = name
            if entity_type and existing.entity_type == "component":
                existing.entity_type = entity_type
            if summary:
                existing.summary = summary
            if attributes:
                existing.attributes.update(attributes)
            self._notify_change()
            return existing

        entity = Entity(
            id=entity_id,
            name=name or entity_id,
            entity_type=entity_type,
            summary=summary,
            attributes=dict(attributes) if attributes else {},
            created_at=created_at or utc_now_iso(),
        )
        self.entities[entity_id] = entity
        self._notify_change()
        return entity

    def record_episode(
        self,
        title: str,
        category: str,
        content: str,
        files_touched: list[str] | None = None,
        entities_mentioned: list[str] | None = None,
        episode_id: str | None = None,
        timestamp: str | None = None,
    ) -> Episode:
        """Record an immutable engineering episode and ensure mentioned entities exist."""
        ep_id = episode_id or f"ep_{uuid.uuid4().hex[:10]}"
        ts = timestamp or utc_now_iso()
        mentioned = list(entities_mentioned or [])
        for ent_id in mentioned:
            if ent_id not in self.entities:
                self.entities[ent_id] = Entity(
                    id=ent_id,
                    name=ent_id,
                    entity_type="component",
                    summary=f"Referenced in episode {ep_id}: {title}",
                    created_at=ts,
                )

        episode = Episode(
            id=ep_id,
            title=title,
            category=category,
            content=content,
            files_touched=list(files_touched or []),
            entities_mentioned=mentioned,
            timestamp=ts,
        )
        self.episodes[ep_id] = episode
        self._notify_change()
        return episode

    def upsert_fact(
        self,
        subject_id: str,
        predicate: str,
        object_id: str | None = None,
        object_value: str | None = None,
        singular: bool = True,
        confidence: float = 1.0,
        source_episode_id: str | None = None,
        valid_from: str | None = None,
        fact_id: str | None = None,
        subject_type: str = "component",
        object_type: str = "component",
    ) -> tuple[TemporalFact, list[TemporalFact]]:
        """Insert a fact with automatic bi-temporal conflict detection and supersession.

        If an active fact already exists with the exact same `(subject_id, predicate, object)`,
        returns that existing fact without duplicating it.
        If `singular=True` and an active fact exists with the same `(subject_id, predicate)`
        but a different target object/value, automatically marks the prior active fact(s)
        as superseded (`valid_until = now`, `superseded_by = new_fact.id`).

        Returns:
            Tuple of `(active_fact, superseded_facts)`.
        """
        subject_id = subject_id.strip()
        predicate = predicate.strip()
        if not subject_id or not predicate:
            raise ValueError("subject_id and predicate must be non-empty.")

        ts = valid_from or utc_now_iso()
        if subject_id not in self.entities:
            self.entities[subject_id] = Entity(
                id=subject_id,
                name=subject_id,
                entity_type=subject_type,
                created_at=ts,
            )
        if object_id and object_id not in self.entities:
            self.entities[object_id] = Entity(
                id=object_id,
                name=object_id,
                entity_type=object_type,
                created_at=ts,
            )

        existing_fact_ids = self._subject_index.get(subject_id, [])
        superseded: list[TemporalFact] = []

        for fid in existing_fact_ids:
            candidate = self.facts[fid]
            if not candidate.is_active_at(None):
                continue
            if candidate.predicate != predicate:
                continue
            # Idempotent check: identical target is already active
            if candidate.object_id == object_id and candidate.object_value == object_value:
                if confidence > candidate.confidence:
                    candidate.confidence = confidence
                    candidate.content_hash = candidate.calculate_hash()
                    self._notify_change()
                return candidate, []

            if singular or candidate.singular:
                superseded.append(candidate)

        new_id = fact_id or f"fact_{uuid.uuid4().hex[:10]}"
        new_fact = TemporalFact(
            id=new_id,
            subject_id=subject_id,
            predicate=predicate,
            object_id=object_id,
            object_value=object_value,
            singular=singular,
            confidence=confidence,
            source_episode_id=source_episode_id,
            valid_from=ts,
        )

        for old_fact in superseded:
            old_fact.valid_until = ts
            old_fact.superseded_by = new_fact.id

        self.facts[new_fact.id] = new_fact
        self._index_fact(new_fact)
        self._notify_change()
        return new_fact, superseded

    def get_facts(
        self,
        subject_id: str | None = None,
        predicate: str | None = None,
        object_id: str | None = None,
        as_of: str | datetime | None = None,
        include_superseded: bool = False,
    ) -> list[TemporalFact]:
        """Query facts filtered by subject, predicate, object, and temporal state."""
        if subject_id is not None:
            candidate_ids = self._subject_index.get(subject_id, [])
            candidates: Iterable[TemporalFact] = (self.facts[fid] for fid in candidate_ids)
        elif object_id is not None:
            candidate_ids = self._object_index.get(object_id, [])
            candidates = (self.facts[fid] for fid in candidate_ids)
        else:
            candidates = self.facts.values()

        results: list[TemporalFact] = []
        for fact in candidates:
            if subject_id is not None and fact.subject_id != subject_id:
                continue
            if predicate is not None and fact.predicate != predicate:
                continue
            if object_id is not None and fact.object_id != object_id:
                continue

            if as_of is not None:
                if not fact.is_active_at(as_of):
                    continue
            elif not include_superseded and not fact.is_active_at(None):
                continue

            results.append(fact)

        return results

    def query_entity(
        self,
        entity_id: str,
        include_superseded: bool = True,
        max_hops: int = 1,
    ) -> dict[str, Any]:
        """Inspect an entity's profile, active facts, superseded history, and K-hop neighborhood."""
        entity = self.entities.get(entity_id)
        outgoing_all = self.get_facts(subject_id=entity_id, include_superseded=True)
        incoming_all = self.get_facts(object_id=entity_id, include_superseded=True)

        active_outgoing = [f.to_dict() for f in outgoing_all if f.is_active_at(None)]
        superseded_outgoing = [f.to_dict() for f in outgoing_all if not f.is_active_at(None)]
        active_incoming = [f.to_dict() for f in incoming_all if f.is_active_at(None)]
        superseded_incoming = [f.to_dict() for f in incoming_all if not f.is_active_at(None)]

        subgraph = self.traverse_subgraph(entity_id, max_hops=max_hops) if max_hops > 0 else {}
        related_episodes = [
            ep.to_dict()
            for ep in self.episodes.values()
            if entity_id in ep.entities_mentioned
            or any(f.source_episode_id == ep.id for f in outgoing_all + incoming_all)
        ]

        result: dict[str, Any] = {
            "exists": entity is not None,
            "entity": entity.to_dict() if entity else {"id": entity_id, "name": entity_id, "entity_type": "unknown"},
            "active_outgoing_facts": active_outgoing,
            "active_incoming_facts": active_incoming,
            "related_episodes": related_episodes,
            "subgraph": subgraph,
        }
        if include_superseded:
            result["superseded_outgoing_facts"] = superseded_outgoing
            result["superseded_incoming_facts"] = superseded_incoming
        return result

    def traverse_subgraph(
        self,
        seed_entity_ids: str | Iterable[str],
        max_hops: int = 2,
        as_of: str | datetime | None = None,
    ) -> dict[str, Any]:
        """Perform a breadth-first K-hop ego-graph traversal over temporally active edges."""
        if isinstance(seed_entity_ids, str):
            seeds = [seed_entity_ids]
        else:
            seeds = list(seed_entity_ids)

        visited_entities: dict[str, int] = {}
        traversed_facts: dict[str, TemporalFact] = {}
        frontier: list[tuple[str, int]] = []

        for seed in seeds:
            if seed in self.entities or seed in self._subject_index or seed in self._object_index:
                visited_entities[seed] = 0
                frontier.append((seed, 0))

        head = 0
        while head < len(frontier):
            current_id, hop = frontier[head]
            head += 1
            if hop >= max_hops:
                continue

            # Outgoing edges
            for fid in self._subject_index.get(current_id, []):
                fact = self.facts[fid]
                if not fact.is_active_at(as_of):
                    continue
                traversed_facts[fact.id] = fact
                if fact.object_id and fact.object_id not in visited_entities:
                    visited_entities[fact.object_id] = hop + 1
                    frontier.append((fact.object_id, hop + 1))

            # Incoming edges
            for fid in self._object_index.get(current_id, []):
                fact = self.facts[fid]
                if not fact.is_active_at(as_of):
                    continue
                traversed_facts[fact.id] = fact
                if fact.subject_id not in visited_entities:
                    visited_entities[fact.subject_id] = hop + 1
                    frontier.append((fact.subject_id, hop + 1))

        return {
            "seed_entities": seeds,
            "max_hops": max_hops,
            "as_of": as_of.isoformat() if isinstance(as_of, datetime) else as_of,
            "entities": [
                {
                    **(self.entities[eid].to_dict() if eid in self.entities else {"id": eid, "name": eid}),
                    "hop_distance": dist,
                }
                for eid, dist in sorted(visited_entities.items(), key=lambda item: (item[1], item[0]))
            ],
            "facts": [f.to_dict() for f in traversed_facts.values()],
        }

    def snapshot_as_of(self, as_of: str | datetime) -> dict[str, Any]:
        """Return a complete time-travel snapshot of the knowledge graph as of `as_of`."""
        target_dt = parse_iso_timestamp(as_of) if isinstance(as_of, str) else as_of.astimezone(timezone.utc)
        target_iso = target_dt.isoformat()

        active_entities = [
            ent.to_dict()
            for ent in self.entities.values()
            if parse_iso_timestamp(ent.created_at) <= target_dt
        ]
        active_facts = [
            fact.to_dict()
            for fact in self.facts.values()
            if fact.is_active_at(target_dt)
        ]
        superseded_by_then = [
            fact.to_dict()
            for fact in self.facts.values()
            if parse_iso_timestamp(fact.valid_from) <= target_dt
            and fact.valid_until is not None
            and parse_iso_timestamp(fact.valid_until) <= target_dt
        ]
        episodes_up_to_then = [
            ep.to_dict()
            for ep in self.episodes.values()
            if parse_iso_timestamp(ep.timestamp) <= target_dt
        ]

        return {
            "as_of": target_iso,
            "entity_count": len(active_entities),
            "active_fact_count": len(active_facts),
            "historical_superseded_count": len(superseded_by_then),
            "episode_count": len(episodes_up_to_then),
            "entities": active_entities,
            "active_facts": active_facts,
            "episodes": episodes_up_to_then,
        }

    def verify_integrity(self) -> dict[str, Any]:
        """Verify cryptographic SHA-256 hashes of all episodes and facts."""
        corrupted_facts: list[str] = []
        corrupted_episodes: list[str] = []

        for fid, fact in self.facts.items():
            expected = fact.calculate_hash()
            if fact.content_hash != expected:
                corrupted_facts.append(fid)

        for eid, ep in self.episodes.items():
            expected = ep.calculate_hash()
            if ep.sha256 != expected:
                corrupted_episodes.append(eid)

        state_digest = compute_sha256(
            {
                "entities": sorted(self.entities.keys()),
                "fact_hashes": {fid: self.facts[fid].content_hash for fid in sorted(self.facts.keys())},
                "episode_hashes": {eid: self.episodes[eid].sha256 for eid in sorted(self.episodes.keys())},
            }
        )

        valid = len(corrupted_facts) == 0 and len(corrupted_episodes) == 0
        return {
            "valid": valid,
            "total_entities": len(self.entities),
            "total_facts": len(self.facts),
            "active_facts": sum(1 for f in self.facts.values() if f.is_active_at(None)),
            "superseded_facts": sum(1 for f in self.facts.values() if not f.is_active_at(None)),
            "total_episodes": len(self.episodes),
            "corrupted_facts": corrupted_facts,
            "corrupted_episodes": corrupted_episodes,
            "graph_merkle_digest": state_digest,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize the complete graph state to a dictionary."""
        return {
            "schema_version": "1.0.0",
            "entities": [e.to_dict() for e in self.entities.values()],
            "facts": [f.to_dict() for f in self.facts.values()],
            "episodes": [ep.to_dict() for ep in self.episodes.values()],
        }

    def save(self, path: str | Path | None = None) -> Path:
        """Atomically persist the knowledge graph to a JSON file."""
        target = Path(path) if path else self.storage_path
        if target is None:
            raise ValueError("No storage_path specified for saving.")
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target.with_suffix(target.suffix + ".tmp")
        payload = self.to_dict()
        payload["integrity"] = self.verify_integrity()
        tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(target)
        return target

    def load(self, path: str | Path | None = None) -> None:
        """Load the knowledge graph state from a persisted JSON file."""
        target = Path(path) if path else self.storage_path
        if target is None or not target.exists():
            raise FileNotFoundError(f"Storage file not found: {target}")
        raw = json.loads(target.read_text(encoding="utf-8"))
        self.entities.clear()
        self.facts.clear()
        self.episodes.clear()
        self._subject_index.clear()
        self._object_index.clear()

        for ent_data in raw.get("entities", []):
            ent = Entity.from_dict(ent_data)
            self.entities[ent.id] = ent

        for fact_data in raw.get("facts", []):
            fact = TemporalFact.from_dict(fact_data)
            self.facts[fact.id] = fact
            self._index_fact(fact)

        for ep_data in raw.get("episodes", []):
            ep = Episode.from_dict(ep_data)
            self.episodes[ep.id] = ep
