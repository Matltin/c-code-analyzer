"""Safe source refactoring APIs."""

from c_analyzer.refactor.rename import (
    RenameResult,
    TextEdit,
    atomic_apply,
    plan_rename,
)

__all__ = ["RenameResult", "TextEdit", "atomic_apply", "plan_rename"]

