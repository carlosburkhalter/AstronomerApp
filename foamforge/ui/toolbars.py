"""Barre d'outils verticale gauche : outils de dessin et actions rapides."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QToolBar

from foamforge.ui.canvas import FoamCanvas, Tool

# (libellé, info-bulle, outil)
_TOOL_DEFS: list[tuple[str, str, Tool]] = [
    ("Sélection", "Sélectionner et déplacer les formes (S)", Tool.SELECT),
    ("Rectangle", "Tracer un logement rectangulaire (R)", Tool.RECT),
    ("Cercle", "Tracer un logement circulaire (C)", Tool.CIRCLE),
    ("Ellipse", "Tracer un logement elliptique (E)", Tool.ELLIPSE),
    ("Texte", "Ajouter un texte gravé (T)", Tool.TEXT),
]

_SHORTCUTS = {Tool.SELECT: "S", Tool.RECT: "R", Tool.CIRCLE: "C",
              Tool.ELLIPSE: "E", Tool.TEXT: "T"}


def build_tool_toolbar(canvas: FoamCanvas) -> QToolBar:
    """Crée la barre d'outils de dessin liée au canvas."""
    toolbar = QToolBar("Outils")
    toolbar.setOrientation(Qt.Orientation.Vertical)
    toolbar.setMovable(False)
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)

    group = QActionGroup(toolbar)
    group.setExclusive(True)
    for label, tooltip, tool in _TOOL_DEFS:
        action = QAction(label, toolbar)
        action.setToolTip(tooltip)
        action.setCheckable(True)
        action.setShortcut(_SHORTCUTS[tool])
        action.setData(tool)
        action.triggered.connect(
            lambda checked=False, t=tool: canvas.set_tool(t)
        )
        group.addAction(action)
        toolbar.addAction(action)
        if tool is Tool.SELECT:
            action.setChecked(True)

    toolbar.addSeparator()

    duplicate = QAction("Dupliquer", toolbar)
    duplicate.setShortcut("Ctrl+D")
    duplicate.setToolTip("Dupliquer la sélection (Ctrl+D)")
    duplicate.triggered.connect(canvas.duplicate_selection)
    toolbar.addAction(duplicate)

    delete = QAction("Supprimer", toolbar)
    delete.setShortcut(Qt.Key.Key_Delete)
    delete.setToolTip("Supprimer la sélection (Suppr)")
    delete.triggered.connect(canvas.delete_selection)
    toolbar.addAction(delete)

    toolbar.addSeparator()

    fit = QAction("Ajuster", toolbar)
    fit.setShortcut("F")
    fit.setToolTip("Ajuster le zoom à la plaque (F)")
    fit.triggered.connect(canvas.fit_sheet)
    toolbar.addAction(fit)

    return toolbar
