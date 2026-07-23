"""Immutable type models shared by semantic analysis and IDE features."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CType:
    """Base class for every type in the documented C subset."""


@dataclass(frozen=True, slots=True)
class PrimitiveType(CType):
    """One of the five primitive types supported by the project."""

    name: str

    def __post_init__(self) -> None:
        if self.name not in {"char", "int", "float", "double", "void"}:
            raise ValueError(f"unsupported primitive type: {self.name}")

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True, slots=True)
class PointerType(CType):
    """A one-level pointer to another supported type."""

    pointee: CType

    def __str__(self) -> str:
        return f"{self.pointee} *"


@dataclass(frozen=True, slots=True)
class ArrayType(CType):
    """A one-dimensional fixed-size array."""

    element_type: CType
    size: int | None

    def __post_init__(self) -> None:
        if self.size is not None and self.size < 0:
            raise ValueError("array size must not be negative")

    def __str__(self) -> str:
        size = "" if self.size is None else str(self.size)
        return f"{self.element_type}[{size}]"


@dataclass(frozen=True, slots=True)
class StructType(CType):
    """A named struct tag, optionally linked to its symbol."""

    name: str
    symbol_id: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("struct name must not be empty")

    def __str__(self) -> str:
        return f"struct {self.name}"


@dataclass(frozen=True, slots=True)
class FunctionType(CType):
    """Return and parameter types for a function or built-in."""

    return_type: CType
    parameter_types: tuple[CType, ...]
    variadic: bool = False

    def __str__(self) -> str:
        parameters = [str(item) for item in self.parameter_types]
        if self.variadic:
            parameters.append("...")
        return f"{self.return_type} ({', '.join(parameters)})"


@dataclass(frozen=True, slots=True)
class UnknownType(CType):
    """A type that cannot yet be determined without emitting an error."""

    def __str__(self) -> str:
        return "<unknown>"


@dataclass(frozen=True, slots=True)
class ErrorType(CType):
    """A poison type used to suppress cascading diagnostics."""

    def __str__(self) -> str:
        return "<error>"


CHAR = PrimitiveType("char")
INT = PrimitiveType("int")
FLOAT = PrimitiveType("float")
DOUBLE = PrimitiveType("double")
VOID = PrimitiveType("void")
UNKNOWN = UnknownType()
ERROR = ErrorType()

_NUMERIC_RANKS = {
    CHAR: 0,
    INT: 1,
    FLOAT: 2,
    DOUBLE: 3,
}


def primitive_type(name: str) -> PrimitiveType:
    """Return the canonical primitive type for a supported name."""
    return {
        "char": CHAR,
        "int": INT,
        "float": FLOAT,
        "double": DOUBLE,
        "void": VOID,
    }[name]


def is_numeric(type_: CType) -> bool:
    return type_ in _NUMERIC_RANKS


def numeric_rank(type_: CType) -> int:
    return _NUMERIC_RANKS[type_]


def common_numeric_type(left: CType, right: CType) -> CType:
    """Return the wider numeric type, or ERROR for non-numeric operands."""
    if not is_numeric(left) or not is_numeric(right):
        return ERROR
    return max((left, right), key=numeric_rank)
