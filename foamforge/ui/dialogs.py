"""Dialogues : nouveau projet, choix de proposition de nesting."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from foamforge.core.nesting import NestingProposal
from foamforge.core.project import FOAM_TYPES, FoamSheet, Project


def _mm_spin(value: float, maximum: float = 3000.0) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(1.0, maximum)
    spin.setDecimals(1)
    spin.setSuffix(" mm")
    spin.setValue(value)
    return spin


class _ColorButton(QPushButton):
    """Bouton de choix de couleur affichant la couleur courante."""

    def __init__(self, initial: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = initial
        self.clicked.connect(self._pick)
        self._refresh()

    def color(self) -> str:
        return self._color

    def _refresh(self) -> None:
        self.setText(self._color)
        self.setStyleSheet(
            f"background-color: {self._color}; color: white; padding: 4px;"
        )

    def _pick(self) -> None:
        chosen = QColorDialog.getColor()
        if chosen.isValid():
            self._color = chosen.name()
            self._refresh()


class NewProjectDialog(QDialog):
    """Assistant de création de projet (étape unique, champs guidés)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nouveau projet FoamForge")
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Décrivez votre valise et la plaque de mousse à découper.\n"
            "Toutes les dimensions sont en millimètres."
        )
        layout.addWidget(intro)

        form = QFormLayout()
        layout.addLayout(form)

        self.name_edit = QLineEdit("Ma valise")
        form.addRow("Nom du projet", self.name_edit)

        self.case_width = _mm_spin(420)
        form.addRow("Valise — largeur", self.case_width)
        self.case_height = _mm_spin(320)
        form.addRow("Valise — profondeur", self.case_height)
        self.case_depth = _mm_spin(160)
        form.addRow("Valise — hauteur", self.case_depth)

        self.sheet_width = _mm_spin(400)
        form.addRow("Mousse — largeur", self.sheet_width)
        self.sheet_height = _mm_spin(300)
        form.addRow("Mousse — hauteur", self.sheet_height)
        self.sheet_thickness = _mm_spin(50, maximum=300)
        form.addRow("Mousse — épaisseur", self.sheet_thickness)

        self.layer_count = QSpinBox()
        self.layer_count.setRange(1, 10)
        form.addRow("Nombre de couches", self.layer_count)

        self.foam_type = QComboBox()
        self.foam_type.addItems(FOAM_TYPES)
        form.addRow("Type de mousse", self.foam_type)

        self.foam_color = _ColorButton("#1a1a1a")
        form.addRow("Couleur de la mousse", self.foam_color)
        self.background_color = _ColorButton("#b3261e")
        self.background_color.setToolTip(
            "Couleur visible au fond des découpes : un fond contrasté "
            "révèle immédiatement les objets manquants."
        )
        form.addRow("Couleur du fond", self.background_color)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def build_project(self) -> Project:
        """Construit le projet depuis les valeurs saisies."""
        return Project(
            name=self.name_edit.text() or "Projet",
            case_width_mm=self.case_width.value(),
            case_height_mm=self.case_height.value(),
            case_depth_mm=self.case_depth.value(),
            sheet=FoamSheet(
                width_mm=self.sheet_width.value(),
                height_mm=self.sheet_height.value(),
                thickness_mm=self.sheet_thickness.value(),
            ),
            layer_count=self.layer_count.value(),
            foam_type=self.foam_type.currentText(),
            foam_color=self.foam_color.color(),
            background_color=self.background_color.color(),
        )


class NestingDialog(QDialog):
    """Choix parmi les propositions de placement automatique."""

    def __init__(
        self,
        proposals: list[NestingProposal],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Placement automatique")
        self._proposals = proposals
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Choisissez une proposition de placement. Les distances "
            "minimales du projet sont respectées."
        ))
        self._list = QListWidget()
        labels = {
            "area_desc": "Compacité (grandes pièces d'abord)",
            "longest_side_desc": "Pièces longues d'abord",
            "weight_desc": "Répartition du poids (lourds au centre)",
        }
        for proposal in proposals:
            placed = len(proposal.placements)
            missing = len(proposal.unplaced_ids)
            status = "complet" if proposal.complete else f"{missing} non placé(s)"
            self._list.addItem(
                f"{labels.get(proposal.strategy, proposal.strategy)} — "
                f"{placed} placé(s), {status}"
            )
        if proposals:
            self._list.setCurrentRow(0)
        layout.addWidget(self._list)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(
            QDialogButtonBox.StandardButton.Apply
        ).clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_proposal(self) -> NestingProposal | None:
        row = self._list.currentRow()
        if 0 <= row < len(self._proposals):
            return self._proposals[row]
        return None
