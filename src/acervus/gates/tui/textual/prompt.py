"""The modal that asks for a name."""

from typing import TYPE_CHECKING, ClassVar

from textual.screen import ModalScreen
from textual.widgets import Input, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.binding import BindingType


class NamePrompt(ModalScreen[str | None]):
    """Asks for a name, returning it or ``None`` if the user backs out.

    What the name is for is the caller's business: the wording comes in as the
    prompt, so marks and stacks ask the same way.
    """

    BINDINGS: ClassVar[list[BindingType]] = [("escape", "cancel", "Cancel")]

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self._prompt = prompt

    def compose(self) -> ComposeResult:
        yield Static(self._prompt, id="prompt")
        yield Input(id="name")

    def on_mount(self) -> None:
        self.query_one("#name", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Hand the typed name back to whoever opened the prompt."""
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        """Back out without naming anything."""
        self.dismiss(None)
