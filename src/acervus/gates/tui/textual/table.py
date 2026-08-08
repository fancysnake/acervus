"""Shared table handling for the Textual screens."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from textual.widgets import DataTable


def fill_table(
    table: DataTable[str], *, columns: Sequence[str], rows: Iterable[Sequence[str]]
) -> None:
    """Set a table up for row selection, head it, and put these rows in it.

    Whatever the table held is cleared first, so filling it again after the
    data has moved reads the same as filling it for the first time.
    """
    table.cursor_type = "row"
    table.clear(columns=True)
    table.add_columns(*columns)
    for row in rows:
        table.add_row(*row)
