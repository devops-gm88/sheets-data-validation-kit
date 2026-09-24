"""Exact-match entity resolution with a human review queue.

The rule this module enforces: **never merge automatically.**

Name-based and fuzzy matching is the usual cause of inflated counts in reporting
pipelines, because common names collide and re-registrations create a second record.
Suspects are surfaced for a person to decide, not resolved by a heuristic.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass
class DuplicateCandidate:
    """Two or more records that look like the same real entity but carry different keys."""

    reason: str
    records: List[Dict[str, Any]]

    def keys(self) -> List[Any]:
        return [r.get("_key") for r in self.records]


@dataclass
class ResolutionOutcome:
    unique: List[Dict[str, Any]] = field(default_factory=list)
    duplicate_keys: List[Tuple[Any, int]] = field(default_factory=list)
    duplicate_candidates: List[DuplicateCandidate] = field(default_factory=list)
    blank_keys: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def unique_count(self) -> int:
        return len(self.unique)

    @property
    def input_count(self) -> int:
        return self.unique_count + sum(count - 1 for _, count in self.duplicate_keys)

    @property
    def inflation(self) -> int:
        """How many phantom entities a naive row count would have reported."""
        return sum(count - 1 for _, count in self.duplicate_keys)

    def summary(self) -> str:
        return (
            f"records in            : {self.input_count}\n"
            f"distinct entities     : {self.unique_count}\n"
            f"phantom entities      : {self.inflation}\n"
            f"blank keys held back  : {len(self.blank_keys)}\n"
            f"suspects for review   : {len(self.duplicate_candidates)}"
        )


def resolve(records: Iterable[Dict[str, Any]],
            key: str,
            signature: Optional[Sequence[str]] = None,
            normalise: Optional[Callable[[Any], Any]] = None) -> ResolutionOutcome:
    """Resolve records to distinct entities on an exact key.

    key        the canonical identifier. Rows without one are held back, never counted.
    signature  optional tuple of fields used only to *suggest* duplicates. Suggestions
               are queued for review; they are never merged.
    normalise  optional callable applied to the key (strip/casefold and similar).
    """
    outcome = ResolutionOutcome()
    norm = normalise or (lambda v: str(v).strip().casefold() if v is not None else None)

    buckets: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        raw = record.get(key)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            outcome.blank_keys.append(record)
            continue
        record = dict(record)
        record["_key"] = norm(raw)
        buckets[record["_key"]].append(record)

    for entity_key, group in buckets.items():
        group_sorted = sorted(group, key=lambda r: str(r.get("_source", "")))
        outcome.unique.append(group_sorted[0])
        if len(group) > 1:
            outcome.duplicate_keys.append((entity_key, len(group)))

    outcome.duplicate_keys.sort(key=lambda kv: -kv[1])

    if signature:
        seen: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = defaultdict(list)
        for record in outcome.unique:
            token = tuple(norm(record.get(f)) for f in signature)
            if any(part is None for part in token):
                continue
            seen[token].append(record)
        for token, group in seen.items():
            if len(group) > 1:
                outcome.duplicate_candidates.append(
                    DuplicateCandidate(
                        reason=f"same {'/'.join(signature)}: {token}",
                        records=group,
                    )
                )
        outcome.duplicate_candidates.sort(key=lambda c: -len(c.records))

    return outcome


def count_distinct(records: Iterable[Dict[str, Any]], key: str) -> int:
    """Distinct entity count. Blank keys are excluded rather than counted as one entity."""
    values = {str(r.get(key)).strip().casefold() for r in records
              if r.get(key) is not None and str(r.get(key)).strip()}
    return len(values)
