"""Validation, reconciliation and entity-resolution primitives.

Standard library only, deliberately.
"""
from .contract import Field, Max, Min, NotBlank, OneOf, Pattern, Range, RowContract, ValidationResult
from .entities import ResolutionOutcome, resolve
from .reconcile import Assertion, Outcome, Reconcile

__version__ = "0.1.0"

__all__ = [
    "Field", "RowContract", "ValidationResult",
    "Min", "Max", "Range", "Pattern", "OneOf", "NotBlank",
    "Assertion", "Reconcile", "Outcome",
    "resolve", "ResolutionOutcome",
]
