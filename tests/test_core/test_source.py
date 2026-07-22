"""Tests for source positions and end-exclusive spans."""

import pytest

from c_analyzer import SourcePosition, SourceSpan


def position(
    offset: int,
    *,
    file: str = "example.c",
    line: int = 1,
    column: int | None = None,
) -> SourcePosition:
    """Build a convenient one-line source position for tests."""
    actual_column = offset + 1 if column is None else column
    return SourcePosition(
        file=file,
        line=line,
        column=actual_column,
        offset=offset,
    )


def test_source_position_accepts_valid_values() -> None:
    source_position = SourcePosition(
        file="main.c",
        line=2,
        column=4,
        offset=12,
    )

    assert source_position.file == "main.c"
    assert source_position.line == 2
    assert source_position.column == 4
    assert source_position.offset == 12


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("line", 0),
        ("line", -1),
        ("column", 0),
        ("column", -1),
        ("offset", -1),
    ],
)
def test_source_position_rejects_out_of_range_values(
    field: str,
    value: int,
) -> None:
    values = {"file": "main.c", "line": 1, "column": 1, "offset": 0}
    values[field] = value

    with pytest.raises(ValueError):
        SourcePosition(**values)


def test_source_position_rejects_empty_file() -> None:
    with pytest.raises(ValueError, match="file must not be empty"):
        SourcePosition(file=" ", line=1, column=1, offset=0)


def test_source_span_accepts_valid_positions_and_calculates_length() -> None:
    span = SourceSpan(start=position(2), end=position(7))

    assert span.start.offset == 2
    assert span.end.offset == 7
    assert span.length == 5


def test_source_span_rejects_reversed_offsets() -> None:
    with pytest.raises(ValueError, match="before span start"):
        SourceSpan(start=position(5), end=position(2))


def test_source_span_rejects_positions_from_different_files() -> None:
    with pytest.raises(ValueError, match="same file"):
        SourceSpan(
            start=position(0, file="first.c"),
            end=position(1, file="second.c"),
        )


def test_source_span_is_end_exclusive() -> None:
    span = SourceSpan(start=position(2), end=position(5))

    assert span.contains(position(2))
    assert span.contains(position(4))
    assert not span.contains(position(5))


def test_source_span_rejects_reversed_display_position() -> None:
    start = position(2, line=2, column=3)
    end = position(3, line=1, column=4)

    with pytest.raises(ValueError, match="display position"):
        SourceSpan(start=start, end=end)

