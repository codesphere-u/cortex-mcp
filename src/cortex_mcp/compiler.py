"""Hybrid BM25 + Graph Spreading Activation & Token-Budgeted Context Compiler.

Ranks active TemporalFacts, architectural decision records (ADRs), bug root causes,
and file invariants using BM25 + identifier boosting + graph neighbor activation,
then deterministically packs the highest-utility context within a strict token budget.
"""

from __future__ import annotations

import dataclasses
import math
import re
from dataclasses import dataclass, field
from typing import Any

from cortex_mcp.graph import BiTemporalMemoryGraph, Entity, Episode, TemporalFact

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_./:-]+")
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def tokenize(text: str) -> list[str]:
    """Tokenize code/engineering text while preserving compound identifiers and sub-tokens."""
    if not text:
        return []
    raw_tokens = _TOKEN_PATTERN.findall(text)
    expanded: list[str] = []
    for tok in raw_tokens:
        lower = tok.lower()
        expanded.append(lower)
        # Split snake_case, path segments, and CamelCase into sub-parts as well
        parts = re.split(r"[_./:-]+", tok)
        for part in parts:
            if not part:
                continue
            p_lower = part.lower()
            if p_lower != lower:
                expanded.append(p_lower)
            camel_parts = _CAMEL_BOUNDARY.split(part)
            if len(camel_parts) > 1:
                for cp in camel_parts:
                    cp_lower = cp.lower()
                    if cp_lower and cp_lower != p_lower:
                        expanded.append(cp_lower)
    return expanded


def estimate_tokens(text: str) -> int:
    """Deterministic token count estimator calibrated for LLM code/prose tokenizers."""
    if not text:
        return 0
    words = len(text.split())
    chars = len(text)
    return max(1, max(words, math.ceil(chars / 3.8)))


@dataclass
class CompiledContextItem:
    """A single ranked and packed memory item inside a CompiledContextBundle."""

    item_id: str
    item_type: str  # "fact" | "episode" | "entity"
    category: str
    score: float
    token_count: int
    formatted_text: str
    citation: str
    entities_involved: list[str] = field(default_factory=list)
    is_superseded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class CompiledContextBundle:
    """Structured output of `ContextCompiler.compile_context`."""

    query: str
    max_tokens: int
    used_tokens: int
    utilization_ratio: float
    items: list[CompiledContextItem]
    excluded_stale_fact_count: int
    excluded_budget_item_count: int
    provenance_citations: list[str]
    activated_entities: list[str]
    rendered_markdown: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "max_tokens": self.max_tokens,
            "used_tokens": self.used_tokens,
            "utilization_ratio": round(self.utilization_ratio, 4),
            "item_count": len(self.items),
            "excluded_stale_fact_count": self.excluded_stale_fact_count,
            "excluded_budget_item_count": self.excluded_budget_item_count,
            "provenance_citations": list(self.provenance_citations),
            "activated_entities": list(self.activated_entities),
            "items": [item.to_dict() for item in self.items],
            "rendered_markdown": self.rendered_markdown,
        }


CATEGORY_PRIORITY_WEIGHTS: dict[str, float] = {
    "invariant": 1.35,
    "adr": 1.25,
    "bug_root_cause": 1.20,
    "migration": 1.15,
    "incident": 1.10,
    "fact": 1.15,
    "session_note": 1.00,
    "entity": 0.90,
}


class ContextCompiler:
    """Hybrid BM25 + Graph Spreading Activation Context Compiler."""

    def __init__(
        self,
        graph: BiTemporalMemoryGraph,
        k1: float = 1.5,
        b: float = 0.75,
        spreading_decay: float = 0.45,
    ) -> None:
        self.graph = graph
        self.k1 = k1
        self.b = b
        self.spreading_decay = spreading_decay

    def _compute_bm25_scores(
        self,
        query_tokens: list[str],
        docs: dict[str, list[str]],
    ) -> dict[str, float]:
        """Compute Okapi BM25 scores for a collection of tokenized documents."""
        if not query_tokens or not docs:
            return {doc_id: 0.0 for doc_id in docs}

        num_docs = len(docs)
        avgdl = sum(len(tokens) for tokens in docs.values()) / max(1, num_docs)

        # Document frequencies
        df: dict[str, int] = {}
        doc_term_counts: dict[str, dict[str, int]] = {}
        for doc_id, tokens in docs.items():
            counts: dict[str, int] = {}
            for t in tokens:
                counts[t] = counts.get(t, 0) + 1
            doc_term_counts[doc_id] = counts
            for t in counts:
                df[t] = df.get(t, 0) + 1

        scores: dict[str, float] = {}
        unique_query_terms = list(dict.fromkeys(query_tokens))

        for doc_id, tokens in docs.items():
            dl = len(tokens)
            counts = doc_term_counts[doc_id]
            score = 0.0
            for q_term in unique_query_terms:
                tf = counts.get(q_term, 0)
                if tf == 0:
                    continue
                n_q = df.get(q_term, 0)
                idf = math.log(1.0 + (num_docs - n_q + 0.5) / (n_q + 0.5))
                denom = tf + self.k1 * (1.0 - self.b + self.b * (dl / max(1.0, avgdl)))
                score += idf * ((tf * (self.k1 + 1.0)) / denom)
            scores[doc_id] = score

        return scores

    def _format_fact_line(self, fact: TemporalFact) -> str:
        status = "SUPERSEDED" if not fact.is_active_at(None) else "ACTIVE"
        src = f", src={fact.source_episode_id}" if fact.source_episode_id else ""
        if status == "SUPERSEDED":
            return (
                f"- [FACT:{fact.id} | SUPERSEDED by {fact.superseded_by}] "
                f"`{fact.subject_id}` --({fact.predicate})--> `{fact.target_display}` "
                f"(valid {fact.valid_from} .. {fact.valid_until}{src})"
            )
        return (
            f"- [FACT:{fact.id}] `{fact.subject_id}` --({fact.predicate})--> "
            f"`{fact.target_display}` (valid_from={fact.valid_from}{src})"
        )

    def _format_episode_line(self, ep: Episode) -> str:
        files_str = f" | files: {', '.join(ep.files_touched)}" if ep.files_touched else ""
        return (
            f"- [{ep.category.upper()}:{ep.id}] **{ep.title}**{files_str}\n"
            f"  {ep.content}"
        )

    def _format_entity_line(self, ent: Entity) -> str:
        summary_str = f": {ent.summary}" if ent.summary else ""
        return f"- [ENTITY:{ent.id}] `{ent.name}` ({ent.entity_type}){summary_str}"

    def compile_context(
        self,
        query: str,
        max_tokens: int = 1200,
        include_superseded: bool = False,
        as_of: str | None = None,
    ) -> CompiledContextBundle:
        """Compile a token-budgeted, provenance-cited context bundle for `query`."""
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive.")

        query_lower = query.lower()
        query_tokens = tokenize(query)

        # 1. Separate active vs stale facts
        all_facts = list(self.graph.facts.values())
        candidate_facts: list[TemporalFact] = []
        excluded_stale_count = 0

        for raw_fact in all_facts:
            is_active = raw_fact.is_active_at(as_of)
            if is_active:
                candidate_facts.append(raw_fact)
            else:
                if include_superseded and as_of is None:
                    candidate_facts.append(raw_fact)
                else:
                    # Check if this stale fact shares subject/predicate/object tokens with query
                    fact_text = f"{raw_fact.subject_id} {raw_fact.predicate} {raw_fact.target_display}".lower()
                    if any(qt in fact_text for qt in query_tokens) or not query_tokens:
                        excluded_stale_count += 1

        # 2. Filter episodes up to `as_of` if time-traveling
        candidate_episodes: list[Episode] = []
        for raw_ep in self.graph.episodes.values():
            if as_of is not None:
                from cortex_mcp.graph import parse_iso_timestamp

                if parse_iso_timestamp(raw_ep.timestamp) > parse_iso_timestamp(as_of):
                    continue
            candidate_episodes.append(raw_ep)

        # 3. Build document corpus for BM25
        docs: dict[str, list[str]] = {}
        item_lookup: dict[str, tuple[str, Any]] = {}

        for cand_fact in candidate_facts:
            key = f"fact:{cand_fact.id}"
            text = f"{cand_fact.subject_id} {cand_fact.predicate} {cand_fact.target_display}"
            docs[key] = tokenize(text)
            item_lookup[key] = ("fact", cand_fact)

        for cand_ep in candidate_episodes:
            key = f"episode:{cand_ep.id}"
            text = f"{cand_ep.title} {cand_ep.category} {cand_ep.content} {' '.join(cand_ep.files_touched)} {' '.join(cand_ep.entities_mentioned)}"
            docs[key] = tokenize(text)
            item_lookup[key] = ("episode", cand_ep)

        for raw_ent in self.graph.entities.values():
            if as_of is not None:
                from cortex_mcp.graph import parse_iso_timestamp

                if parse_iso_timestamp(raw_ent.created_at) > parse_iso_timestamp(as_of):
                    continue
            key = f"entity:{raw_ent.id}"
            text = f"{raw_ent.id} {raw_ent.name} {raw_ent.entity_type} {raw_ent.summary}"
            docs[key] = tokenize(text)
            item_lookup[key] = ("entity", raw_ent)

        bm25_scores = self._compute_bm25_scores(query_tokens, docs)

        # 4. Compute exact identifier boosts and initial entity activations
        entity_activation: dict[str, float] = {}
        for ent_id, ent_obj in self.graph.entities.items():
            act = bm25_scores.get(f"entity:{ent_id}", 0.0)
            if ent_id.lower() in query_lower or ent_obj.name.lower() in query_lower:
                act += 4.0
            if act > 0:
                entity_activation[ent_id] = act

        # Also seed entity activation from high-scoring facts and episodes
        for key, score in bm25_scores.items():
            if score <= 0:
                continue
            kind, obj = item_lookup[key]
            if kind == "fact":
                entity_activation[obj.subject_id] = max(
                    entity_activation.get(obj.subject_id, 0.0), score * 0.8
                )
                if obj.object_id:
                    entity_activation[obj.object_id] = max(
                        entity_activation.get(obj.object_id, 0.0), score * 0.8
                    )
            elif kind == "episode":
                for eid in obj.entities_mentioned:
                    entity_activation[eid] = max(entity_activation.get(eid, 0.0), score * 0.6)

        # 5. 2-Hop Graph Spreading Activation over active edges
        for _hop in range(2):
            next_activation = dict(entity_activation)
            for active_fact in candidate_facts:
                if not active_fact.is_active_at(as_of):
                    continue
                s_act = entity_activation.get(active_fact.subject_id, 0.0)
                if active_fact.object_id:
                    o_act = entity_activation.get(active_fact.object_id, 0.0)
                    if s_act > 0:
                        propagated = s_act * self.spreading_decay * active_fact.confidence
                        if propagated > next_activation.get(active_fact.object_id, 0.0):
                            next_activation[active_fact.object_id] = propagated
                    if o_act > 0:
                        propagated = o_act * self.spreading_decay * active_fact.confidence
                        if propagated > next_activation.get(active_fact.subject_id, 0.0):
                            next_activation[active_fact.subject_id] = propagated
            entity_activation = next_activation

        # 6. Score and build candidate CompiledContextItems
        scored_candidates: list[CompiledContextItem] = []

        for key, (kind, obj) in item_lookup.items():
            base_bm25 = bm25_scores.get(key, 0.0)
            if kind == "fact":
                fact: TemporalFact = obj
                graph_boost = entity_activation.get(fact.subject_id, 0.0)
                if fact.object_id:
                    graph_boost = max(graph_boost, entity_activation.get(fact.object_id, 0.0))
                exact_boost = 0.0
                if fact.subject_id.lower() in query_lower:
                    exact_boost += 2.5
                if fact.predicate.lower() in query_lower:
                    exact_boost += 1.5
                if fact.target_display.lower() in query_lower:
                    exact_boost += 2.0

                raw_score = (base_bm25 + graph_boost * 0.65 + exact_boost) * fact.confidence
                raw_score *= CATEGORY_PRIORITY_WEIGHTS["fact"]
                is_sup = not fact.is_active_at(as_of)
                if is_sup:
                    raw_score *= 0.35

                if raw_score <= 0.01 and query_tokens:
                    continue

                formatted = self._format_fact_line(fact)
                involved = [fact.subject_id] + ([fact.object_id] if fact.object_id else [])
                citation = f"fact:{fact.id}@sha256:{fact.content_hash[:12]}"
                scored_candidates.append(
                    CompiledContextItem(
                        item_id=fact.id,
                        item_type="fact",
                        category="fact",
                        score=round(raw_score, 4),
                        token_count=estimate_tokens(formatted),
                        formatted_text=formatted,
                        citation=citation,
                        entities_involved=involved,
                        is_superseded=is_sup,
                    )
                )

            elif kind == "episode":
                ep: Episode = obj
                graph_boost = max(
                    (entity_activation.get(eid, 0.0) for eid in ep.entities_mentioned),
                    default=0.0,
                )
                file_boost = sum(
                    2.5 for fpath in ep.files_touched if fpath.lower() in query_lower
                )
                cat_weight = CATEGORY_PRIORITY_WEIGHTS.get(ep.category, 1.0)
                raw_score = (base_bm25 + graph_boost * 0.55 + file_boost) * cat_weight

                if raw_score <= 0.01 and query_tokens:
                    continue

                formatted = self._format_episode_line(ep)
                citation = f"episode:{ep.id}@sha256:{ep.sha256[:12]}"
                scored_candidates.append(
                    CompiledContextItem(
                        item_id=ep.id,
                        item_type="episode",
                        category=ep.category,
                        score=round(raw_score, 4),
                        token_count=estimate_tokens(formatted),
                        formatted_text=formatted,
                        citation=citation,
                        entities_involved=list(ep.entities_mentioned),
                        is_superseded=False,
                    )
                )

            elif kind == "entity":
                ent: Entity = obj
                if not ent.summary:
                    continue
                graph_boost = entity_activation.get(ent.id, 0.0)
                raw_score = (base_bm25 + graph_boost * 0.4) * CATEGORY_PRIORITY_WEIGHTS["entity"]
                if raw_score <= 0.01 and query_tokens:
                    continue

                formatted = self._format_entity_line(ent)
                citation = f"entity:{ent.id}"
                scored_candidates.append(
                    CompiledContextItem(
                        item_id=ent.id,
                        item_type="entity",
                        category=ent.entity_type,
                        score=round(raw_score, 4),
                        token_count=estimate_tokens(formatted),
                        formatted_text=formatted,
                        citation=citation,
                        entities_involved=[ent.id],
                        is_superseded=False,
                    )
                )

        # Sort deterministically by descending score, then utility density (score/tokens), then item_id
        scored_candidates.sort(
            key=lambda item: (
                -item.score,
                -(item.score / max(1, item.token_count)),
                item.item_id,
            )
        )

        # 7. Pack within strict `max_tokens` budget
        header_lines = [
            f"## Cortex-MCP Compiled Context (query: `{query}`)",
        ]
        header_tokens = estimate_tokens("\n".join(header_lines))
        used_tokens = min(header_tokens, max_tokens)

        packed_items: list[CompiledContextItem] = []
        excluded_budget_count = 0
        citations: list[str] = []
        activated_entities_set: set[str] = set()

        for candidate in scored_candidates:
            if used_tokens + candidate.token_count <= max_tokens:
                packed_items.append(candidate)
                used_tokens += candidate.token_count
                citations.append(candidate.citation)
                for eid in candidate.entities_involved:
                    activated_entities_set.add(eid)
            else:
                excluded_budget_count += 1

        body_lines = list(header_lines)
        for item in packed_items:
            body_lines.append(item.formatted_text)
        rendered_markdown = "\n".join(body_lines)

        return CompiledContextBundle(
            query=query,
            max_tokens=max_tokens,
            used_tokens=used_tokens,
            utilization_ratio=used_tokens / max(1, max_tokens),
            items=packed_items,
            excluded_stale_fact_count=excluded_stale_count,
            excluded_budget_item_count=excluded_budget_count,
            provenance_citations=citations,
            activated_entities=sorted(activated_entities_set),
            rendered_markdown=rendered_markdown,
        )
