"""End-to-end demonstration on synthetic data.

Run:  python3 examples/demo.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from validation_kit import Field, Min, Pattern, Reconcile, RowContract
from validation_kit.entities import resolve
from validation_kit.reconcile import rollforward_check

ROWS = [
    {"child_id": "C-1001", "period": "2026-Q1", "advocacy_hours": "12.5"},
    {"child_id": "C-1002", "period": "2026-Q1", "advocacy_hours": "8"},
    {"child_id": "c-1002", "period": "2026-Q1", "advocacy_hours": "8"},
    {"child_id": "C-1003", "period": "2026-Q1", "advocacy_hours": ""},
    {"child_id": "C-1004", "period": "Q1-2026", "advocacy_hours": "3"},
    {"child_id": "", "period": "2026-Q1", "advocacy_hours": "5"},
]

INVENTORY = {"opening": 1400.00, "additions": 620.50, "reductions": 985.25, "closing": 1035.25}


def main() -> None:
    print("=" * 68)
    print("1. FIELD CONTRACTS  -- rows pass or are quarantined, never dropped")
    print("=" * 68)
    contract = RowContract([
        Field("child_id", required=True),
        Field("period", rules=[Pattern(r"^\d{4}-Q[1-4]$")]),
        Field("advocacy_hours", rules=[Min(0)], coerce=float),
    ])
    result = contract.validate_rows(ROWS)
    print(result.summary())
    print()
    for row, reasons in result.quarantined:
        print(f"  held back: {row.get('child_id') or '(blank)'} -> {'; '.join(reasons)}")

    print()
    print("=" * 68)
    print("2. ENTITY RESOLUTION  -- exact keys, suspects queued for a human")
    print("=" * 68)
    outcome = resolve(result.accepted, key="child_id")
    print(outcome.summary())
    print()
    print(f"  'children served' reported honestly: {outcome.unique_count}")
    print(f"  a naive row count would have said:   {outcome.input_count}")

    print()
    print("=" * 68)
    print("3. ARITHMETIC RECONCILIATION  -- independent of any model")
    print("=" * 68)
    suite = Reconcile([rollforward_check("opening", "additions", "reductions", "closing")])
    for check in suite.check(INVENTORY):
        print("  " + str(check))
    print()
    print("  Now the same record with one field quietly wrong:")
    broken = dict(INVENTORY, closing=1035.00)
    for check in suite.check(broken):
        print("  " + str(check))
    print()
    print("  Field-level validation would have accepted every number above.")
    print("  The roll-forward is what catches it.")


if __name__ == "__main__":
    main()
