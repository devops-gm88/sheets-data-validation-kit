# sheets-data-validation-kit

[![CI](https://github.com/devops-gm88/sheets-data-validation-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/devops-gm88/sheets-data-validation-kit/actions/workflows/ci.yml)
[![Python versions](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-black.svg)](LICENSE)

Validation, reconciliation and entity-resolution primitives for spreadsheet and CSV pipelines.

Most data pipelines fail quietly. A row lands, a number looks plausible, and nobody notices it is wrong
until it has been reported to someone. This kit exists to make that failure mode loud.

It is deliberately **standard-library only** — no dependencies, nothing to install, nothing to upgrade.
Copy the `src/validation_kit` folder into your project, or install the package in one line:

```bash
pip install git+https://github.com/devops-gm88/sheets-data-validation-kit.git
```

Not on PyPI yet - the GitHub URL above is the install. From a clone:
`pip install -e .`.

## The three ideas

**1. Rows pass or they are quarantined. They are never silently dropped.**
A row that fails a contract goes to quarantine with the reasons attached. You can always answer
"where did this record go?" — which is the question that kills trust in a pipeline.

**2. Arithmetic is a second, independent check.**
Field-level validation confirms each value looks right. Reconciliation confirms the values are
*consistent with each other*. An extracted balance sheet must balance; a cash flow statement must tie to
the change in cash. If the arithmetic does not close, the extraction failed regardless of how confident
each individual field was. This catches the failure nobody sees: clean extraction, quietly wrong numbers.

**3. Exact match or human review. Never a fuzzy merge.**
Duplicates are detected on a canonical key. Suspected duplicates are queued for a person, because a
silent merge corrupts counts invisibly and is very hard to unpick later.

## Quick start

```python
from validation_kit import RowContract, Field, Min, Range, Pattern, Reconcile, Assertion
from validation_kit.entities import resolve

contract = RowContract([
    Field("account_id", required=True),
    Field("amount", rules=[Min(0)], coerce=float,
          on_fail="quarantine"),
    Field("period", rules=[Pattern(r"^\d{4}-Q[1-4]$")]),
])

result = contract.validate_rows(rows)
print(result.summary())
for row, reasons in result.quarantined:
    print(row.get("account_id"), reasons)
```

```python
# Arithmetic self-consistency: the check that does not depend on the model
suite = Reconcile([
    Assertion("balance_sheet_balances",
              lambda r: r["total_assets"], lambda r: r["total_liabilities"] + r["total_equity"],
              tolerance=0.01),
])

for outcome in suite.check(parsed_statement):
    print(outcome)   # PASS / FAIL with both sides of the equation printed
```

```python
# Entity resolution: exact key, review queue, no auto-merge
outcome = resolve(records, key="child_id")
print(outcome.unique_count, len(outcome.duplicate_candidates))
```

## What this is not

- It is not a data-quality *scoring* tool. There is no 0-100 number and no dashboard.
- It does not fix your source data. It tells you which records are untrustworthy and why.
- It will not merge duplicates for you. That is the point.

## Why it exists

Built from repeatedly solving the same problem on real reporting systems: a monthly pack that was
*almost* right, and no way to prove which numbers were which. These are the primitives that were
written more than once, extracted so they are not written again.

## Tests

Install first, then run:

```bash
pip install -e .
python3 -m unittest discover -s tests -v
```

Or without installing anything:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Both give **24 tests, OK**. Running `unittest` from a fresh clone without one of
those two steps fails to import the package — that is a packaging path, not a
test failure.

## License

MIT
