"""Isometric pygame frontend for the Vogelfrei combat UI.

A third concrete ``Frontend`` (alongside the terminal frontends) that
renders combat as an isometric board with clickable tokens and action
buttons. The sim runs on a worker thread; pygame owns the main thread.
See ``frontend.py`` for the thread bridge and ``app.py`` for the loop.
"""

from .frontend import IsoFrontend
from .app import run_iso_game, IsoApp

__all__ = ["IsoFrontend", "run_iso_game", "IsoApp"]
