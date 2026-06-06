"""Live-screen plumbing for the terminal frontend — stdlib only.

Two tiny helpers, no third-party deps:

``LiveScreen`` drives the terminal's *alternate screen buffer* (the
same mode ``less`` and ``vim`` use). While active, every full redraw
homes the cursor and clears downward, so the combat view updates in
place instead of scrolling — the whole fight stays on one screen. On
stop the original scrollback is restored untouched.

``LogFile`` is the other half of the deal: everything that used to
flood the terminal (every round-start board, every resolved move) is
appended here instead, so there's a complete play-by-play to read
after the fight without the live view ever scrolling.
"""

from __future__ import annotations
import sys
from typing import TYPE_CHECKING, Optional, TextIO

if TYPE_CHECKING:
    from ...combat import CombatContext


# ANSI control sequences. Kept here so the escape-code vocabulary lives
# in one place (mirrors render.py keeping the visual language in one).
_ENTER_ALT = "\033[?1049h"   # switch to the alternate screen buffer
_EXIT_ALT = "\033[?1049l"    # restore the normal buffer + scrollback
_HOME_CLEAR = "\033[H\033[J"  # cursor to top-left, then clear to end


class LiveScreen:
    """Owns the alternate screen buffer and in-place redraws.

    The cursor is left *visible* — unlike a pure progress bar, this view
    has to host an ``input()`` prompt at the bottom of the frame, and a
    hidden cursor there is disorienting.
    """

    def __init__(self, stream: Optional[TextIO] = None) -> None:
        self.stream: TextIO = stream if stream is not None else sys.stdout
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def start(self) -> None:
        if self._active:
            return
        self.stream.write(_ENTER_ALT)
        self.stream.flush()
        self._active = True

    def stop(self) -> None:
        if not self._active:
            return
        self.stream.write(_EXIT_ALT)
        self.stream.flush()
        self._active = False

    def redraw(self, frame: str) -> None:
        """Clear the screen and draw ``frame`` from the top-left.

        No-op-safe if the screen isn't active (falls back to a plain
        print so callers don't have to branch).
        """
        if not self._active:
            self.stream.write(frame.rstrip("\n") + "\n")
            self.stream.flush()
            return
        self.stream.write(_HOME_CLEAR)
        self.stream.write(frame.rstrip("\n") + "\n")
        self.stream.flush()

    def __enter__(self) -> "LiveScreen":
        self.start()
        return self

    def __exit__(self, *exc: object) -> bool:
        self.stop()
        return False


class LogFile:
    """Append-only sink for the textual play-by-play.

    ``flush_round`` / ``write_event`` push narration lines; ``flush_log``
    drains any new entries the sim itself appended to ``ctx.log`` (none
    today, but the seam is here so a future narration system lands in the
    file automatically).
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._fh: TextIO = open(path, "w", encoding="utf-8")
        self._ctx_log_flushed = 0

    def write(self, line: str) -> None:
        self._fh.write(line + "\n")
        self._fh.flush()

    def write_block(self, block: str) -> None:
        self._fh.write(block.rstrip("\n") + "\n\n")
        self._fh.flush()

    def flush_log(self, ctx: "CombatContext") -> None:
        """Append any ``ctx.log`` lines not yet written to the file."""
        new = ctx.log[self._ctx_log_flushed:]
        for line in new:
            self._fh.write(line + "\n")
        if new:
            self._fh.flush()
        self._ctx_log_flushed = len(ctx.log)

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.close()
