"""Source location models shared by all compiler phases."""

from dataclasses import dataclass


def _validate_integer(name: str, value: int, minimum: int) -> None:
    """Validate an integer field without accepting booleans."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")


@dataclass(frozen=True, slots=True)
class SourcePosition:
    """A single position in a source file."""

    file: str
    line: int
    column: int
    offset: int

    def __post_init__(self) -> None:
        if not isinstance(self.file, str):
            raise TypeError("file must be a string")
        if not self.file.strip():
            raise ValueError("file must not be empty")

        _validate_integer("line", self.line, 1)
        _validate_integer("column", self.column, 1)
        _validate_integer("offset", self.offset, 0)


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """An end-exclusive range between two positions in one file."""

    start: SourcePosition
    end: SourcePosition

    def __post_init__(self) -> None:
        if not isinstance(self.start, SourcePosition):
            raise TypeError("start must be a SourcePosition")
        if not isinstance(self.end, SourcePosition):
            raise TypeError("end must be a SourcePosition")
        if self.start.file != self.end.file:
            raise ValueError("span positions must belong to the same file")
        if self.end.offset < self.start.offset:
            raise ValueError("span end must not be before span start")

        start_display = (self.start.line, self.start.column)
        end_display = (self.end.line, self.end.column)
        if end_display < start_display:
            raise ValueError("span end display position must not be before start")
        if self.end.offset == self.start.offset and end_display != start_display:
            raise ValueError("equal offsets must have equal display positions")

    @property
    def length(self) -> int:
        """Return the number of source characters covered by the span."""
        return self.end.offset - self.start.offset

    def contains(self, position: SourcePosition) -> bool:
        """Return whether a position is inside the end-exclusive span."""
        if not isinstance(position, SourcePosition):
            raise TypeError("position must be a SourcePosition")
        return (
            position.file == self.start.file
            and self.start.offset <= position.offset < self.end.offset
        )

