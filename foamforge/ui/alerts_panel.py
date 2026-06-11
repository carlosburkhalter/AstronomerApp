"""Panneau d'alertes : résultats des contrôles de sécurité.

Liste colorée (rouge bloquant / orange recommandation / vert valide).
Cliquer sur une alerte sélectionne les formes concernées dans le canvas.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget

from foamforge.core.validation import Issue, Severity

_PREFIX = {
    Severity.ERROR: "⛔",
    Severity.WARNING: "⚠️",
    Severity.OK: "✅",
}


class AlertsPanel(QListWidget):
    """Liste des alertes de validation."""

    issue_activated = Signal(list)  # ids des formes concernées

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.itemClicked.connect(self._on_item_clicked)

    def set_issues(self, issues: list[Issue]) -> None:
        self.clear()
        # Erreurs d'abord, puis avertissements, puis OK.
        order = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.OK: 2}
        for issue in sorted(issues, key=lambda i: order[i.severity]):
            item = QListWidgetItem(
                f"{_PREFIX[issue.severity]} {issue.message}"
            )
            item.setForeground(QColor(issue.severity.color))
            item.setData(0x0100, issue.shape_ids)  # Qt.UserRole
            self.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        shape_ids = item.data(0x0100) or []
        if shape_ids:
            self.issue_activated.emit(shape_ids)
