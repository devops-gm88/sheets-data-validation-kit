"""Validation, reconciliation and entity-resolution primitives.

Standard library only, deliberately.
"""
from .contract import Field, RowContract, ValidationResult, Min, Max, Range, Pattern, OneOf, NotBlank
from .reconcile import Assertion, Reconcile, Outcome
from .entities import resolve, ResolutionOutcome

__version__ = "0.1.0"

__all__ = [
    "Field", "RowContract", "ValidationResult",
    "Min", "Max", "Range", "Pattern", "OneOf", "NotBlank",
    "Assertion", "Reconcile", "Outcome",
    "resolve", "ResolutionOutcome",
]
