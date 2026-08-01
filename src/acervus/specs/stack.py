"""Invariants a stack name must hold."""

from __future__ import annotations

from acervus.pacts.stack import InvalidStackNameError

MAX_NAME_LENGTH = 255


def clean_stack_name(name: str) -> str:
    """Return the name a stack should be stored under.

    Runs of whitespace collapse to single spaces and the ends are trimmed, so
    ``" Summer   2026 "`` and ``"Summer 2026"`` are the same stack rather than
    two that look alike. Spaces are otherwise allowed: a file sits in at most
    one stack, so a stack name is never packed alongside others in a list and
    never has to survive being split apart again.

    Returns:
        The collapsed, trimmed name.

    Raises:
        InvalidStackNameError: The name is blank once trimmed, or too long to
            store.
    """
    if not (cleaned := " ".join(name.split())):
        message = "A stack name cannot be blank."
        raise InvalidStackNameError(message)
    if len(cleaned) > MAX_NAME_LENGTH:
        message = f"A stack name cannot exceed {MAX_NAME_LENGTH} characters."
        raise InvalidStackNameError(message)
    return cleaned
