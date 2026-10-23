"""
VanaSetu Evals Package
======================
Historical test cases and evaluation harness.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vanasetu.evals.eval_harness import EvaluationHarness


def __getattr__(name: str):
    if name == "EvaluationHarness":
        from vanasetu.evals.eval_harness import EvaluationHarness
        return EvaluationHarness
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["EvaluationHarness"]
