"""Panneau « Couches de mousse » : calcul et affichage de l'empilement.

Pilote le :mod:`foamforge.core.layers` (FoamLayerPlanner) : à partir de
la profondeur intérieure de la valise, des épaisseurs disponibles et des
poches du projet, propose un empilement exact et l'applique au projet.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from foamforge.core.layers import LayerRole, plan_layers
from foamforge.core.project import Project

_ROLE_ICONS = {
    LayerRole.BOTTOM: "▂",
    LayerRole.SPACER: "▄",
    LayerRole.CUTOUT: "▣",
    LayerRole.LID: "▔",
}


class LayersPanel(QWidget):
    """Panneau de gestion de l'empilement de couches."""

    layers_changed = Signal()  # l'empilement du projet a été modifié

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project: Project | None = None

        layout = QVBoxLayout(self)
        self._summary = QLabel("Aucun empilement calculé.")
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)

        self._list = QListWidget()
        self._list.setToolTip(
            "Empilement du fond (haut de la liste inversé : première ligne "
            "= couche du dessus) vers le fond de la valise."
        )
        layout.addWidget(self._list)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Couches souhaitées :"))
        self.preferred_count = QSpinBox()
        self.preferred_count.setRange(0, 12)
        self.preferred_count.setSpecialValueText("auto")
        self.preferred_count.setToolTip(
            "0 = automatique (le moins de couches possible)."
        )
        controls.addWidget(self.preferred_count)
        controls.addStretch()
        layout.addLayout(controls)

        self.compute_button = QPushButton("Calculer les couches")
        self.compute_button.clicked.connect(self.compute)
        layout.addWidget(self.compute_button)

        self._messages = QLabel("")
        self._messages.setWordWrap(True)
        layout.addWidget(self._messages)
        layout.addStretch()

    # ------------------------------------------------------------------ #
    def set_project(self, project: Project) -> None:
        self._project = project
        self.refresh()

    def refresh(self) -> None:
        """Réaffiche l'empilement courant du projet."""
        self._list.clear()
        project = self._project
        if project is None or not project.foam_layers:
            self._summary.setText(
                "Aucun empilement calculé : la mousse est traitée comme une "
                "plaque unique. Cliquez sur « Calculer les couches »."
            )
            return
        total = sum(layer.thickness_mm for layer in project.foam_layers)
        cuttable = project.cuttable_depth_mm()
        self._summary.setText(
            f"{len(project.foam_layers)} couches — total {total:.0f} mm "
            f"pour {project.case_depth_mm:.0f} mm intérieurs — "
            f"{cuttable:.0f} mm découpables."
        )
        # Affichage du HAUT (couvercle) vers le BAS (fond), comme une coupe.
        for index, layer in reversed(list(enumerate(project.foam_layers, 1))):
            item = QListWidgetItem(
                f"{_ROLE_ICONS[layer.role]}  Couche {index} — "
                f"{layer.thickness_mm:.0f} mm — {layer.role.label}"
            )
            if layer.role is LayerRole.CUTOUT:
                item.setForeground(QColor("#90caf9"))
            self._list.addItem(item)

    # ------------------------------------------------------------------ #
    def compute(self) -> None:
        """Calcule l'empilement et l'applique au projet si possible."""
        project = self._project
        if project is None:
            return
        preferred = self.preferred_count.value() or None
        plan = plan_layers(
            case_depth_mm=project.case_depth_mm,
            available_foam_thicknesses_mm=project.available_foam_thicknesses_mm,
            max_pocket_depth_mm=project.max_pocket_depth_mm(),
            max_object_height_mm=project.max_object_height_mm(),
            min_bottom_floor_mm=project.min_bottom_floor_mm,
            preferred_layer_count=preferred,
        )
        if not plan.feasible:
            self._messages.setStyleSheet("color: #d32f2f;")
            self._messages.setText("⛔ " + " ".join(plan.errors))
            return
        project.foam_layers = plan.layers
        project.layer_count = len(plan.layers)
        # L'épaisseur de la plaque de travail = profondeur découpable.
        project.sheet.thickness_mm = plan.cuttable_mm()
        if plan.warnings:
            self._messages.setStyleSheet("color: #ef6c00;")
            self._messages.setText("⚠️ " + " ".join(plan.warnings))
        else:
            self._messages.setStyleSheet("color: #2e7d32;")
            self._messages.setText(
                "✅ Empilement calculé : il remplit exactement la valise."
            )
        self.refresh()
        self.layers_changed.emit()
