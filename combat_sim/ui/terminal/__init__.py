"""Terminal Frontend for the Vogelfrei combat UI.

Stdlib only — ``input``/``print``. No curses, no third-party deps.
The Frontend Protocol lives in ``..frontend``; this package provides
one concrete implementation. Future React (or textual, or whatever)
frontends sit alongside it without touching anything else.
"""

from .frontend import TerminalFrontend
from .live import LiveTerminalFrontend

__all__ = ["TerminalFrontend", "LiveTerminalFrontend"]
