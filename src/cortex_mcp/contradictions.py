"""
cortex_mcp.contradictions
=========================
Semantic & Polarity Contradiction Auditor (`ContradictionAuditor`, `audit_contradictions`).

Scans active facts in a `BiTemporalMemoryGraph` to detect unresolved logical
contradictions:
1. Negation Polarity Conflicts: Two active facts on the same subject sharing a
   canonical predicate where one predicate or object carries negation (`does_not_use`,
   `never_allows`, `not enabled`) while the other is affirmative (`uses`, `allows`, `enabled`).
2. Antonym Object Conflicts: Two active facts on the same subject & canonical predicate
   whose object values are opposing technical antonyms (`enabled` vs `disabled`,
   `stateful` vs `stateless`, `synchronous` vs `asynchronous`, `encrypted` vs `plaintext`,
   `mutable` vs `immutable`, `public` vs `private`, `allowed` vs `forbidden`, etc.).
3. Predicate Alias Collisions: Two active facts on the same subject inserted under
   different surface predicate strings that normalize to the same canonical concept
   (e.g., `uses_token_format` vs `token_format`, `requires_isolation` vs `isolation_level`,
   `depends_on` vs `requires_service`) with conflicting objects.
4. Unsuperseded Multi-Value Singular Drift: Two active facts on the same subject and
   predicate with divergent object values that bypassed automatic supersession (e.g.,
   inserted with `singular=False` across concurrent agent sessions).

Also supports `auto_resolve=True` to deterministically supersede the older or
lower-confidence conflicting fact in place.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Dict, List, Literal, Optional, Sequence, Set, Tuple

from cortex_mcp.graph import BiTemporalMemoryGraph, TemporalFact, parse_iso_timestamp

ConflictSeverity = Literal["CRITICAL", "HIGH", "MEDIUM"]
ConflictKind = Literal[
    "negation_polarity_conflict",
    "antonym_object_conflict",
    "predicate_alias_conflict",
    "unsuperseded_value_conflict",
]

NEGATION_PREFIXES: Tuple[str, ...] = (
    "does_not_",
    "do_not_",
    "must_not_",
    "should_not_",
    "cannot_",
    "never_",
    "not_",
    "no_",
    "non_",
    "disallows_",
    "forbids_",
    "prohibits_",
)

NEGATION_TOKENS: Set[str] = {
    "not",
    "never",
    "no",
    "none",
    "cannot",
    "false",
    "disabled",
    "disallow",
    "disallowed",
    "forbid",
    "forbidden",
    "prohibit",
    "prohibited",
    "without",
}

ANTONYM_PAIRS: Tuple[Tuple[str, str], ...] = (
    ("enabled", "disabled"),
    ("enable", "disable"),
    ("true", "false"),
    ("yes", "no"),
    ("allowed", "forbidden"),
    ("allowed", "prohibited"),
    ("allowed", "disallowed"),
    ("allow", "forbid"),
    ("allow", "prohibit"),
    ("allow", "disallow"),
    ("stateful", "stateless"),
    ("synchronous", "asynchronous"),
    ("sync", "async"),
    ("encrypted", "plaintext"),
    ("encrypted", "unencrypted"),
    ("mutable", "immutable"),
    ("public", "private"),
    ("active", "inactive"),
    ("online", "offline"),
    ("required", "optional"),
    ("mandatory", "optional"),
    ("blocking", "nonblocking"),
    ("strict", "permissive"),
    ("safe", "unsafe"),
    ("secure", "insecure"),
)

PREDICATE_VERB_PREFIXES: Tuple[str, ...] = (
    "uses_",
    "use_",
    "has_",
    "have_",
    "is_",
    "requires_",
    "require_",
    "enforces_",
    "enforce_",
    "configured_with_",
    "configured_",
    "set_to_",
    "supports_",
    "support_",
    "allows_",
    "allow_",
)

PREDICATE_SYNONYM_MAP: Dict[str, str] = {
    "auth_token": "token_format",
    "token_type": "token_format",
    "session_token": "token_format",
    "isolation": "isolation_level",
    "tx_isolation": "isolation_level",
    "db_engine": "database_engine",
    "storage_engine": "database_engine",
    "signing_key": "signing_primitive",
    "signature_algorithm": "signing_primitive",
    "signing_algorithm": "signing_primitive",
}


def normalize_predicate(predicate: str) -> Tuple[str, bool]:
    """
    Normalize a predicate into `(canonical_predicate, is_negated)`.

    Examples:
      - `uses_token_format` -> `('token_format', False)`
      - `does_not_use_token_format` -> `('token_format', True)`
      - `token_format` -> `('token_format', False)`
      - `never_allows_plaintext` -> `('plaintext', True)`
    """
    raw = predicate.strip().lower()
    raw = re.sub(r"[\s\-]+", "_", raw)
    is_negated = False

    for neg_pref in NEGATION_PREFIXES:
        if raw.startswith(neg_pref):
            is_negated = True
            raw = raw[len(neg_pref) :]
            break

    # Strip leading verb prefixes so aliases like `uses_token_format` and `token_format` match
    changed = True
    while changed:
        changed = False
        for verb_pref in PREDICATE_VERB_PREFIXES:
            if raw.startswith(verb_pref) and len(raw) > len(verb_pref):
                raw = raw[len(verb_pref) :]
                changed = True
                break

    canonical = PREDICATE_SYNONYM_MAP.get(raw, raw)
    return canonical, is_negated


def _extract_tokens(text: str) -> Set[str]:
    return {t.lower() for t in re.findall(r"[a-zA-Z0-9]+", text.lower()) if t}


def _check_object_antonym_or_negation(val_a: str, val_b: str) -> Tuple[bool, Optional[str]]:
    """
    Check if two object strings exhibit opposite negation polarity or antonym opposition.
    Returns `(is_opposing, reason_detail)`.
    """
    toks_a = _extract_tokens(val_a)
    toks_b = _extract_tokens(val_b)

    # Check antonym pairs
    for pos_w, neg_w in ANTONYM_PAIRS:
        if (pos_w in toks_a and neg_w in toks_b) or (neg_w in toks_a and pos_w in toks_b):
            return True, f"Opposing antonym values '{val_a}' vs '{val_b}' ({pos_w} <-> {neg_w})"

    # Check explicit negation token flip on otherwise overlapping content
    neg_a = bool(toks_a & NEGATION_TOKENS)
    neg_b = bool(toks_b & NEGATION_TOKENS)
    if neg_a != neg_b:
        return True, f"Negation polarity inversion between '{val_a}' and '{val_b}'"

    return False, None


def _pick_winner_and_loser(fact_a: TemporalFact, fact_b: TemporalFact) -> Tuple[TemporalFact, TemporalFact, str]:
    """
    Determine which conflicting fact should be retained (`winner`) and which should
    be superseded (`loser`), based on confidence first, then `valid_from` recency.
    """
    if abs(fact_a.confidence - fact_b.confidence) > 1e-6:
        if fact_a.confidence > fact_b.confidence:
            return (
                fact_a,
                fact_b,
                f"Retain `{fact_a.id}` (higher confidence {fact_a.confidence:.2f} > {fact_b.confidence:.2f}) "
                f"and supersede `{fact_b.id}`.",
            )
        return (
            fact_b,
            fact_a,
            f"Retain `{fact_b.id}` (higher confidence {fact_b.confidence:.2f} > {fact_a.confidence:.2f}) "
            f"and supersede `{fact_a.id}`.",
        )

    dt_a = parse_iso_timestamp(fact_a.valid_from)
    dt_b = parse_iso_timestamp(fact_b.valid_from)
    if dt_b >= dt_a:
        return (
            fact_b,
            fact_a,
            f"Supersede older fact `{fact_a.id}` (valid_from={fact_a.valid_from}) with newer fact `{fact_b.id}` (valid_from={fact_b.valid_from}).",
        )
    return (
        fact_a,
        fact_b,
        f"Supersede older fact `{fact_b.id}` (valid_from={fact_b.valid_from}) with newer fact `{fact_a.id}` (valid_from={fact_a.valid_from}).",
    )


@dataclass(frozen=True)
class ContradictionFinding:
    """Represents a single unresolved contradiction between two active TemporalFacts."""

    conflict_id: str
    kind: ConflictKind
    severity: ConflictSeverity
    subject_id: str
    canonical_predicate: str
    fact_a_id: str
    fact_b_id: str
    fact_a_summary: str
    fact_b_summary: str
    explanation: str
    recommended_winner_id: str
    recommended_supersede_id: str
    recommended_resolution: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContradictionAuditReport:
    """Structured report emitted by `ContradictionAuditor.audit`."""

    active_facts_scanned: int
    contradiction_count: int
    critical_count: int
    high_count: int
    medium_count: int
    clean: bool
    conflicts: List[ContradictionFinding] = field(default_factory=list)
    resolved_fact_ids: List[str] = field(default_factory=list)
    summary_markdown: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_facts_scanned": self.active_facts_scanned,
            "contradiction_count": self.contradiction_count,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "clean": self.clean,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "resolved_fact_ids": list(self.resolved_fact_ids),
            "summary_markdown": self.summary_markdown,
        }


class ContradictionAuditor:
    """
    Semantic & Polarity Contradiction Auditor for `BiTemporalMemoryGraph`.
    """

    def __init__(self, graph: BiTemporalMemoryGraph) -> None:
        self.graph = graph

    def audit(
        self,
        *,
        as_of: Optional[str] = None,
        auto_resolve: bool = False,
    ) -> ContradictionAuditReport:
        """
        Scan all active facts in the graph (optionally at `as_of`) and detect logical
        contradictions across negation polarity, antonym objects, predicate aliases,
        and unsuperseded multi-value drift.
        """
        active_facts = [
            f for f in self.graph.facts.values() if f.is_active_at(as_of)
        ]
        active_facts.sort(key=lambda f: (f.subject_id, f.predicate, f.id))

        # Group active facts by (subject_id, canonical_predicate)
        groups: Dict[Tuple[str, str], List[Tuple[TemporalFact, bool]]] = {}
        for fact in active_facts:
            canon_pred, is_neg_pred = normalize_predicate(fact.predicate)
            groups.setdefault((fact.subject_id, canon_pred), []).append((fact, is_neg_pred))

        findings: List[ContradictionFinding] = []
        resolved_ids: List[str] = []
        conflict_seq = 0

        for (subj_id, canon_pred), items in sorted(groups.items()):
            if len(items) < 2:
                continue

            for i in range(len(items)):
                fact_a, neg_pred_a = items[i]
                for j in range(i + 1, len(items)):
                    fact_b, neg_pred_b = items[j]
                    val_a = fact_a.target_display
                    val_b = fact_b.target_display

                    is_obj_opposing, obj_reason = _check_object_antonym_or_negation(val_a, val_b)

                    kind: Optional[ConflictKind] = None
                    severity: ConflictSeverity = "HIGH"
                    explanation = ""

                    # Case 1: Predicate negation polarity flip on same or overlapping target
                    if neg_pred_a != neg_pred_b and (
                        val_a.lower() == val_b.lower() or not is_obj_opposing
                    ):
                        kind = "negation_polarity_conflict"
                        severity = "CRITICAL"
                        explanation = (
                            f"Active facts `{fact_a.id}` ({fact_a.predicate}={val_a}) and "
                            f"`{fact_b.id}` ({fact_b.predicate}={val_b}) on `{subj_id}` have "
                            f"opposite predicate negation polarity on `{canon_pred}`."
                        )

                    # Case 2: Antonym or negation polarity flip in object values
                    elif is_obj_opposing and neg_pred_a == neg_pred_b:
                        kind = "antonym_object_conflict"
                        severity = "CRITICAL"
                        explanation = (
                            f"Active facts `{fact_a.id}` and `{fact_b.id}` on `{subj_id}` "
                            f"({canon_pred}) assert contradictory object polarity: {obj_reason}."
                        )

                    # Case 3: Predicate alias collision with divergent values
                    elif fact_a.predicate != fact_b.predicate and val_a.lower() != val_b.lower():
                        kind = "predicate_alias_conflict"
                        severity = "HIGH"
                        explanation = (
                            f"Active facts `{fact_a.id}` (predicate `{fact_a.predicate}` -> `{val_a}`) "
                            f"and `{fact_b.id}` (predicate `{fact_b.predicate}` -> `{val_b}`) on `{subj_id}` "
                            f"normalize to the same canonical concept `{canon_pred}` with conflicting values."
                        )

                    # Case 4: Same predicate, different values left active simultaneously
                    elif (
                        fact_a.predicate == fact_b.predicate
                        and val_a.lower() != val_b.lower()
                        and (fact_a.singular or fact_b.singular or not fact_a.object_id)
                    ):
                        kind = "unsuperseded_value_conflict"
                        severity = "MEDIUM"
                        explanation = (
                            f"Active facts `{fact_a.id}` (`{val_a}`) and `{fact_b.id}` (`{val_b}`) "
                            f"on `{subj_id}.{fact_a.predicate}` hold divergent values without supersession."
                        )

                    if kind is None:
                        continue

                    conflict_seq += 1
                    winner, loser, resolution_text = _pick_winner_and_loser(fact_a, fact_b)
                    finding = ContradictionFinding(
                        conflict_id=f"conflict_{conflict_seq:03d}",
                        kind=kind,
                        severity=severity,
                        subject_id=subj_id,
                        canonical_predicate=canon_pred,
                        fact_a_id=fact_a.id,
                        fact_b_id=fact_b.id,
                        fact_a_summary=f"{fact_a.subject_id} --({fact_a.predicate})--> {val_a}",
                        fact_b_summary=f"{fact_b.subject_id} --({fact_b.predicate})--> {val_b}",
                        explanation=explanation,
                        recommended_winner_id=winner.id,
                        recommended_supersede_id=loser.id,
                        recommended_resolution=resolution_text,
                    )
                    findings.append(finding)

                    if auto_resolve and loser.is_active_at(None):
                        loser.valid_until = winner.valid_from
                        loser.superseded_by = winner.id
                        if loser.id not in resolved_ids:
                            resolved_ids.append(loser.id)

        if resolved_ids and self.graph.storage_path:
            self.graph.save(self.graph.storage_path)

        crit = sum(1 for f in findings if f.severity == "CRITICAL")
        high = sum(1 for f in findings if f.severity == "HIGH")
        med = sum(1 for f in findings if f.severity == "MEDIUM")
        clean = len(findings) == 0

        md_lines = [
            "## Cortex-MCP Bi-Temporal Contradiction Audit Report",
            f"- **Active Facts Scanned**: `{len(active_facts)}`",
            f"- **Contradictions Detected**: `{len(findings)}` (`CRITICAL`: {crit}, `HIGH`: {high}, `MEDIUM`: {med})",
            f"- **Graph Status**: **{'CLEAN (0 CONTRADICTIONS)' if clean else 'CONTRADICTIONS FOUND'}**",
        ]
        if resolved_ids:
            md_lines.append(f"- **Auto-Superseded Facts**: `{resolved_ids}`")
        if findings:
            md_lines.append("\n### Detected Conflict Pairs")
            for f in findings:
                md_lines.append(
                    f"- **[{f.severity}] `{f.conflict_id}` ({f.kind})** on `{f.subject_id}` (`{f.canonical_predicate}`):\n"
                    f"  - Fact A (`{f.fact_a_id}`): `{f.fact_a_summary}`\n"
                    f"  - Fact B (`{f.fact_b_id}`): `{f.fact_b_summary}`\n"
                    f"  - Resolution: {f.recommended_resolution}"
                )

        return ContradictionAuditReport(
            active_facts_scanned=len(active_facts),
            contradiction_count=len(findings),
            critical_count=crit,
            high_count=high,
            medium_count=med,
            clean=clean,
            conflicts=findings,
            resolved_fact_ids=resolved_ids,
            summary_markdown="\n".join(md_lines),
        )


def audit_contradictions(
    graph: BiTemporalMemoryGraph,
    *,
    as_of: Optional[str] = None,
    auto_resolve: bool = False,
) -> ContradictionAuditReport:
    """Convenience function to run `ContradictionAuditor(graph).audit(...)`."""
    return ContradictionAuditor(graph).audit(as_of=as_of, auto_resolve=auto_resolve)
