"""Arithmetic reconciliation.

Field-level validation asks "does this value look right?".
Reconciliation asks "are these values consistent with each other?".

It is a genuinely independent check: it needs no model, no confidence score and no
reference data, only arithmetic that must hold. If a statement extracts cleanly and the
arithmetic does not close, the extraction failed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Sequence


@dataclass
class Outcome:
    name: str
    passed: bool
    left: float
    right: float
    difference: float
    tolerance: float
    note: str = ""

    def __str__(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        detail = f"{self.left:,.2f} vs {self.right:,.2f} (diff {self.difference:,.4f}, tol {self.tolerance})"
        return f"[{mark}] {self.name}: {detail}" + (f"  -- {self.note}" if self.note else "")


@dataclass
class Assertion:
    """One equation that must hold for a record.

    left and right are callables taking the record and returning a number, so the
    assertion reads like the equation it tests:

        Assertion("assets = liabilities + equity",
                  lambda r: r["total_assets"],
                  lambda r: r["total_liabilities"] + r["total_equity"])
    """

    name: str
    left: Callable[[Dict[str, Any]], float]
    right: Callable[[Dict[str, Any]], float]
    tolerance: float = 0.01
    note: str = ""


class Reconcile:
    def __init__(self, assertions: Sequence[Assertion]):
        self.assertions = list(assertions)

    def check(self, record: Dict[str, Any]) -> List[Outcome]:
        outcomes: List[Outcome] = []
        for assertion in self.assertions:
            try:
                left = float(assertion.left(record))
                right = float(assertion.right(record))
            except (KeyError, TypeError, ValueError) as exc:
                outcomes.append(Outcome(assertion.name, False, float("nan"), float("nan"),
                                        float("nan"), assertion.tolerance,
                                        note=f"cannot evaluate: {exc}"))
                continue
            difference = abs(left - right)
            outcomes.append(Outcome(assertion.name, difference <= assertion.tolerance,
                                    left, right, difference, assertion.tolerance, assertion.note))
        return outcomes

    def all_pass(self, record: Dict[str, Any]) -> bool:
        return all(o.passed for o in self.check(record))

    def failures(self, record: Dict[str, Any]) -> List[Outcome]:
        return [o for o in self.check(record) if not o.passed]


def closing_balance_check(opening: str, inflow: str, outflow: str, closing: str,
                          tolerance: float = 0.01) -> Assertion:
    """closing == opening + inflow - outflow."""
    return Assertion(
        "closing = opening + inflow - outflow",
        lambda r: r[closing],
        lambda r: r[opening] + r[inflow] - r[outflow],
        tolerance=tolerance,
    )


def rollforward_check(opening: str, additions: str, reductions: str, closing: str,
                      tolerance: float = 0.01) -> Assertion:
    """closing == opening + additions - reductions. Used for inventory, PP&E, capital assets."""
    return Assertion(
        "closing = opening + additions - reductions",
        lambda r: r[closing],
        lambda r: r[opening] + r[additions] - r[reductions],
        tolerance=tolerance,
    )
