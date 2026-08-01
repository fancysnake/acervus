"""Invariants a mark name must hold."""

from __future__ import annotations

from acervus.pacts.mark import InvalidMarkNameError

MAX_NAME_LENGTH = 64
RESERVED_CHARACTERS = frozenset(":,")


def clean_mark_name(name: str) -> str:
    """Return the name a mark should be stored under.

    Surrounding whitespace is insignificant and gets trimmed. What is left
    must be non-empty, must fit the column, must not contain whitespace, and
    must avoid the characters that separate marks from one another and from a
    root alias when they are typed or displayed.

    Names keep their case: ``Invoice`` and ``invoice`` are two marks, in the
    same way two files can differ only by case.

    Returns:
        The trimmed name.

    Raises:
        InvalidMarkNameError: The name is empty, too long, or uses a
            character a mark name may not carry.
    """
    if not (cleaned := name.strip()):
        message = "A mark name cannot be blank."
        raise InvalidMarkNameError(message)
    if len(cleaned) > MAX_NAME_LENGTH:
        message = f"A mark name cannot exceed {MAX_NAME_LENGTH} characters."
        raise InvalidMarkNameError(message)
    if any(character.isspace() for character in cleaned):
        message = f"A mark name cannot contain whitespace: {cleaned!r}."
        raise InvalidMarkNameError(message)
    if found := RESERVED_CHARACTERS.intersection(cleaned):
        listed = "".join(sorted(found))
        message = f"A mark name cannot contain {listed!r}: {cleaned!r}."
        raise InvalidMarkNameError(message)
    return cleaned
