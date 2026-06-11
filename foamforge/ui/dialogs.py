"""Dialogues : paramètres du projet (création/édition), choix de nesting."""

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
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from foamforge.core.nesting import NestingProposal
from foamforge.core.project import (
    DEFAULT_FOAM_THICKNESSES,
    FOAM_TYPES,
    FoamSheet,
    Project,
)


def _mm_spin(value: float, maximum: float = 3000.0) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(1.0, maximum)
    spin.setDecimals(1)
    spin.setSuffix(" mm")
    spin.setKeyboardTracking(False)
    spin.setValue(value)
    return spin


def _parse_thicknesses(text: str) -> list[float]:
    """Analyse « 10, 20, 30 » en liste d'épaisseurs (mm), erreurs ignorées."""
    values: list[float] = []
    for token in text.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        try:
            value = float(token)
        except ValueError:
            continue
        if value > 0:
            values.append(value)
    return sorted(set(values))


class _ColorButton(QPushButton):
    """Bouton de choix de couleur affichant la couleur courante."""

    def __init__(self, initial: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = initial
        self.clicked.connect(self._pick)
        self._refresh()

    def color(self) -> str:
        return self._color

    def set_color(self, color: str) -> None:
        self._color = color
        self._refresh()

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


class ProjectSettingsDialog(QDialog):
    """Création OU édition des paramètres du projet.

    La surface de travail du canvas représente l'intérieur utile de la
    valise : la plaque de mousse reprend les dimensions intérieures
    saisies ici.
    """

    def __init__(
        self, project: Project | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._editing = project is not None
        self.setWindowTitle(
            "Paramètres du projet" if self._editing
            else "Nouveau projet FoamForge"
        )
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Dimensions INTÉRIEURES de la valise, en millimètres.\n"
            "Le plan de travail représente la surface intérieure utile."
        ))

        form = QFormLayout()
        layout.addLayout(form)

        self.name_edit = QLineEdit("Ma valise")
        form.addRow("Nom du projet", self.name_edit)
        self.case_name_edit = QLineEdit()
        self.case_name_edit.setPlaceholderText("ex. Nanuk 935, Peli 1510…")
        form.addRow("Modèle de valise", self.case_name_edit)

        self.case_width = _mm_spin(420)
        form.addRow("Largeur intérieure", self.case_width)
        self.case_height = _mm_spin(320)
        form.addRow("Hauteur intérieure (plan)", self.case_height)
        self.case_depth = _mm_spin(160, maximum=500)
        self.case_depth.setToolTip(
            "Profondeur intérieure (couvercle fermé) : détermine "
            "l'empilement de couches de mousse."
        )
        form.addRow("Profondeur intérieure", self.case_depth)

        self.border_margin = _mm_spin(12, maximum=100)
        self.border_margin.setToolTip(
            "Marge de sécurité minimale entre les découpes et le bord."
        )
        form.addRow("Marge de sécurité bords", self.border_margin)

        self.thicknesses_edit = QLineEdit(
            ", ".join(f"{t:.0f}" for t in DEFAULT_FOAM_THICKNESSES)
        )
        self.thicknesses_edit.setToolTip(
            "Épaisseurs de plaques de mousse disponibles, séparées par "
            "des virgules (mm)."
        )
        form.addRow("Mousses disponibles", self.thicknesses_edit)

        self.min_floor = _mm_spin(10, maximum=100)
        self.min_floor.setToolTip(
            "Épaisseur de mousse intacte souhaitée sous les poches."
        )
        form.addRow("Fond minimum restant", self.min_floor)

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

        self.notes_edit = QLineEdit()
        form.addRow("Notes", self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if project is not None:
            self._load(project)

    # ------------------------------------------------------------------ #
    def _load(self, project: Project) -> None:
        self.name_edit.setText(project.name)
        self.case_name_edit.setText(project.case_name)
        self.case_width.setValue(project.case_width_mm)
        self.case_height.setValue(project.case_height_mm)
        self.case_depth.setValue(project.case_depth_mm)
        self.border_margin.setValue(project.min_border_mm)
        self.thicknesses_edit.setText(
            ", ".join(f"{t:g}" for t in project.available_foam_thicknesses_mm)
        )
        self.min_floor.setValue(project.min_bottom_floor_mm)
        index = self.foam_type.findText(project.foam_type)
        if index >= 0:
            self.foam_type.setCurrentIndex(index)
        self.foam_color.set_color(project.foam_color)
        self.background_color.set_color(project.background_color)
        self.notes_edit.setText(project.notes)

    def _validate_and_accept(self) -> None:
        if not _parse_thicknesses(self.thicknesses_edit.text()):
            QMessageBox.warning(
                self, "Épaisseurs invalides",
                "Indiquez au moins une épaisseur de mousse valide, "
                "par exemple : 10, 20, 30, 40, 50",
            )
            return
        self.accept()

    # ------------------------------------------------------------------ #
    def apply_to(self, project: Project) -> None:
        """Applique les valeurs saisies à un projet (création ou édition).

        La plaque de mousse (surface de travail) suit les dimensions
        intérieures ; son épaisseur reste pilotée par l'empilement de
        couches (ou la profondeur intérieure en mono-plaque).
        """
        project.name = self.name_edit.text() or "Projet"
        project.case_name = self.case_name_edit.text()
        project.case_width_mm = self.case_width.value()
        project.case_height_mm = self.case_height.value()
        project.case_depth_mm = self.case_depth.value()
        project.min_border_mm = self.border_margin.value()
        project.available_foam_thicknesses_mm = _parse_thicknesses(
            self.thicknesses_edit.text()
        )
        project.min_bottom_floor_mm = self.min_floor.value()
        project.foam_type = self.foam_type.currentText()
        project.foam_color = self.foam_color.color()
        project.background_color = self.background_color.color()
        project.notes = self.notes_edit.text()
        # Surface de travail = intérieur utile de la valise.
        project.sheet = FoamSheet(
            width_mm=self.case_width.value(),
            height_mm=self.case_height.value(),
            thickness_mm=(
                project.cuttable_depth_mm()
                if project.foam_layers
                else self.case_depth.value()
            ),
        )

    def build_project(self) -> Project:
        """Construit un nouveau projet depuis les valeurs saisies."""
        project = Project()
        self.apply_to(project)
        return project


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
