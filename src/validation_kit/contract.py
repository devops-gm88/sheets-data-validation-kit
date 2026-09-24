"""Field-level contracts.

A row either satisfies its contract or it is quarantined with the reasons attached.
Quarantine is the default failure mode: nothing is ever silently dropped.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple


class Rule:
    """Base class for a single field rule."""

    name = "rule"

    def check(self, value: Any) -> Optional[str]:
        """Return None if the value passes, else a human-readable reason."""
        raise NotImplementedError


@dataclass
class Min(Rule):
    bound: float
    name = "min"

    def check(self, value):
        try:
            return None if float(value) >= self.bound else f"below minimum {self.bound}"
        except (TypeError, ValueError):
            return f"not numeric, cannot compare to minimum {self.bound}"


@dataclass
class Max(Rule):
    bound: float
    name = "max"

    def check(self, value):
        try:
            return None if float(value) <= self.bound else f"above maximum {self.bound}"
        except (TypeError, ValueError):
            return f"not numeric, cannot compare to maximum {self.bound}"


@dataclass
class Range(Rule):
    low: float
    high: float
    name = "range"

    def check(self, value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return f"not numeric, cannot range-check {self.low}..{self.high}"
        if number < self.low or number > self.high:
            return f"{number} outside plausible range {self.low}..{self.high}"
        return None


@dataclass
class Pattern(Rule):
    regex: str
    name = "pattern"

    def check(self, value):
        import re

        return None if re.match(self.regex, str(value)) else f"does not match {self.regex}"


@dataclass
class OneOf(Rule):
    allowed: Sequence[Any]
    name = "one_of"

    def check(self, value):
        return None if value in self.allowed else f"{value!r} not one of {list(self.allowed)}"


class NotBlank(Rule):
    name = "not_blank"

    def check(self, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            return "blank"
        return None


@dataclass
class Field:
    """One column in a row contract.

    on_fail:
        "quarantine" (default) - hold the whole row back for review.
        "flag"                 - record the problem but keep the row.
    """

    name: str
    required: bool = False
    rules: List[Rule] = field(default_factory=list)
    coerce: Optional[Callable[[Any], Any]] = None
    on_fail: str = "quarantine"


@dataclass
class ValidationResult:
    accepted: List[Dict[str, Any]] = field(default_factory=list)
    quarantined: List[Tuple[Dict[str, Any], List[str]]] = field(default_factory=list)
    flagged: List[Tuple[Dict[str, Any], List[str]]] = field(default_factory=list)
    field_error_counts: Dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.accepted) + len(self.quarantined)

    @property
    def pass_rate(self) -> float:
        return 0.0 if self.total == 0 else len(self.accepted) / self.total

    def summary(self) -> str:
        lines = [
            f"rows in        : {self.total}",
            f"accepted       : {len(self.accepted)}  ({self.pass_rate:.1%})",
            f"quarantined    : {len(self.quarantined)}",
            f"flagged        : {len(self.flagged)}",
        ]
        if self.field_error_counts:
            lines.append("errors by field:")
            for name, count in sorted(self.field_error_counts.items(), key=lambda kv: -kv[1]):
                lines.append(f"  {name:<24} {count}")
        return "\n".join(lines)


class RowContract:
    """A set of field rules applied to every row.

    Rows that fail a quarantine field are held back. Rows that fail a flag field are
    kept, with the problem recorded, so a pipeline can decide for itself how strict to be
    on fields it does not depend on.
    """

    def __init__(self, fields: Sequence[Field]):
        self.fields = list(fields)

    def validate_row(self, row: Dict[str, Any]):
        """Returns (cleaned_row, reasons, verdict) where verdict is pass|quarantine|flag."""
        cleaned: Dict[str, Any] = dict(row)
        reasons: List[str] = []
        severity = "pass"

        for spec in self.fields:
            value = row.get(spec.name)

            if spec.required and (value is None or (isinstance(value, str) and not value.strip())):
                reasons.append(f"{spec.name}: required but blank")
                severity = "quarantine"
                continue

            if value is None or (isinstance(value, str) and not value.strip()):
                continue

            if spec.coerce is not None:
                try:
                    value = spec.coerce(value)
                    cleaned[spec.name] = value
                except (TypeError, ValueError) as exc:
                    reasons.append(f"{spec.name}: cannot coerce ({exc})")
                    severity = "quarantine" if spec.on_fail == "quarantine" else "flag"
                    continue

            for rule in spec.rules:
                problem = rule.check(value)
                if problem:
                    reasons.append(f"{spec.name}: {problem}")
                    if spec.on_fail == "quarantine":
                        severity = "quarantine"
                    elif severity == "pass":
                        severity = "flag"

        return cleaned, reasons, severity

    def validate_rows(self, rows: Iterable[Dict[str, Any]]) -> ValidationResult:
        result = ValidationResult()
        for row in rows:
            cleaned, reasons, verdict = self.validate_row(row)
            if verdict == "pass":
                result.accepted.append(cleaned)
            elif verdict == "quarantine":
                result.quarantined.append((cleaned, reasons))
                _bump(result.field_error_counts, reasons)
            else:
                result.flagged.append((cleaned, reasons))
                _bump(result.field_error_counts, reasons)
        return result


def _bump(counter: Dict[str, int], reasons: Sequence[str]) -> None:
    for reason in reasons:
        counter[reason.split(":", 1)[0]] = counter.get(reason.split(":", 1)[0], 0) + 1
