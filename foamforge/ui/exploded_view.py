"""Vue « couches éclatées » : comprendre ce que chaque couche découpe.

Chaque couche de l'empilement est dessinée séparément, en perspective
isométrique fixe, avec uniquement les découpes qui la concernent
(calculées objet par objet par :func:`compute_layer_assignments`) :

- découpe traversante → ouverture sur la couleur de fond ;
- poche partielle → fond de poche éclairci + profondeur entamée ;
- gravures/textes → uniquement sur la couche découpée supérieure.

Une case à cocher par couche permet de la masquer ; cliquer sur une
couche la sélectionne (épaisseur, rôle et contenu en surbrillance).
La vue est exportable en PNG pour documentation atelier.
"""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from foamforge.core.layers import LayerAssignment, LayerRole
from foamforge.core.project import Project
from foamforge.ui.view3d import _ROLE_COLORS

_COS30 = math.cos(math.radians(30))
_SIN30 = math.sin(math.radians(30))
# Écart vertical entre couches éclatées, en mm de scène.
_GAP_MM = 26.0


def _iso(x: float, y: float, lift: float) -> QPointF:
    """Projection isométrique fixe ; ``lift`` = élévation écran (mm)."""
    return QPointF((x - y) * _COS30, (x + y) * _SIN30 - lift)


class ExplodedDiagram(QWidget):
    """Zone de dessin de l'éclaté (sans les contrôles)."""

    layer_clicked = Signal(int)  # index de pile (1 = fond)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project: Project | None = None
        self._hidden: set[int] = set()
        self._selected: int | None = None
        # Zones cliquables : (polygone écran, index de pile).
        self._hit_zones: list[tuple[QPolygonF, int]] = []
        self.setMinimumSize(420, 320)

    # ------------------------------------------------------------------ #
    def set_project(self, project: Project) -> None:
        self._project = project
        self._selected = None
        self.update()

    def set_hidden(self, hidden: set[int]) -> None:
        self._hidden = set(hidden)
        self.update()

    def set_selected(self, index: int | None) -> None:
        self._selected = index
        self.update()

    def refresh(self) -> None:
        self.update()

    def export_png(self, path: str | Path) -> Path:
        """Capture PNG de la vue éclatée (documentation atelier)."""
        image = QImage(self.size(), QImage.Format.Format_RGB32)
        self.render(image)
        path = Path(path)
        image.save(str(path), "PNG")
        return path

    # ------------------------------------------------------------------ #
    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#202020"))
        self._hit_zones = []
        project = self._project
        if project is None:
            painter.end()
            return
        assignments = project.layer_assignments()
        if not assignments:
            painter.setPen(QPen(QColor("#cccccc")))
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter,
                "Aucun empilement : cliquez sur « Calculer les couches ».",
            )
            painter.end()
            return

        visible = [a for a in assignments if a.index not in self._hidden]
        if not visible:
            painter.end()
            return

        sheet = project.sheet
        w, h = sheet.width_mm, sheet.height_mm
        # Élévation de chaque couche visible : bandes d'écran DISJOINTES
        # (l'emprise projetée d'une face est (w+h)·sin30 : on sépare d'au
        # moins cette hauteur pour qu'aucune couche n'en masque une autre —
        # chaque couche doit montrer TOUTES ses découpes).
        face_height = (w + h) * _SIN30
        lifts: dict[int, float] = {}
        lift = 0.0
        for assignment in visible:
            lifts[assignment.index] = lift
            lift += face_height + assignment.layer.thickness_mm + _GAP_MM

        # Cadrage : étendue projetée de l'ensemble.
        xs, ys = [], []
        for assignment in visible:
            base = lifts[assignment.index]
            for x in (0.0, w):
                for y in (0.0, h):
                    for z in (base, base + assignment.layer.thickness_mm):
                        point = _iso(x, y, z)
                        xs.append(point.x())
                        ys.append(point.y())
        span_x = (max(xs) - min(xs)) or 1.0
        span_y = (max(ys) - min(ys)) or 1.0
        margin = 40
        label_gutter = 190  # colonne de droite pour les étiquettes
        scale = min(
            (self.width() - 2 * margin - label_gutter) / span_x,
            (self.height() - 2 * margin) / span_y,
        )
        offset = QPointF(
            margin - min(xs) * scale,
            margin - min(ys) * scale,
        )

        def to_screen(x: float, y: float, z: float) -> QPointF:
            return _iso(x, y, z) * scale + offset

        # Dessin du fond vers le haut (les couches hautes par-dessus).
        for assignment in visible:
            self._paint_layer(
                painter, project, assignment, lifts[assignment.index],
                to_screen,
            )
        painter.end()

    # ------------------------------------------------------------------ #
    def _paint_layer(
        self,
        painter: QPainter,
        project: Project,
        assignment: LayerAssignment,
        base_lift: float,
        to_screen,
    ) -> None:
        sheet = project.sheet
        w, h = sheet.width_mm, sheet.height_mm
        thickness = assignment.layer.thickness_mm
        top = base_lift + thickness
        selected = self._selected == assignment.index

        edge = QPen(QColor("#42a5f5") if selected else QColor("#141414"), 1.2)
        side_color = QColor(_ROLE_COLORS[assignment.layer.role])
        painter.setPen(edge)

        # Parois visibles (faces y = h et x = w en projection iso fixe).
        painter.setBrush(side_color)
        painter.drawPolygon(QPolygonF([
            to_screen(0, h, base_lift), to_screen(w, h, base_lift),
            to_screen(w, h, top), to_screen(0, h, top),
        ]))
        painter.setBrush(side_color.darker(125))
        painter.drawPolygon(QPolygonF([
            to_screen(w, h, base_lift), to_screen(w, 0, base_lift),
            to_screen(w, 0, top), to_screen(w, h, top),
        ]))

        # Face supérieure de la couche.
        top_face = QPolygonF([
            to_screen(0, 0, top), to_screen(w, 0, top),
            to_screen(w, h, top), to_screen(0, h, top),
        ])
        painter.setBrush(QColor(project.foam_color).lighter(
            165 if selected else 150
        ))
        painter.drawPolygon(top_face)
        self._hit_zones.append((top_face, assignment.index))

        # Découpes de cette couche uniquement.
        shapes_by_id = {s.id: s for s in project.shapes}
        cut_pen = QPen(QColor("#111111"), 0.8)
        for cut in assignment.cuts:
            shape = shapes_by_id.get(cut.shape_id)
            if shape is None:
                continue
            polygon = shape.cut_polygon()
            path = QPainterPath()
            for ring in [polygon.exterior, *polygon.interiors]:
                first = True
                for x, y in ring.coords:
                    point = to_screen(x, y, top)
                    if first:
                        path.moveTo(point)
                        first = False
                    else:
                        path.lineTo(point)
                path.closeSubpath()
            if cut.is_surface:
                painter.setPen(QPen(QColor("#80cbc4"), 1.0))
                painter.setBrush(Qt.BrushStyle.NoBrush)
            elif cut.through:
                painter.setPen(cut_pen)
                painter.setBrush(QColor(project.background_color))
            else:
                painter.setPen(cut_pen)
                painter.setBrush(QColor(project.foam_color).lighter(205))
            painter.drawPath(path)
            # Profondeur entamée pour les poches partielles.
            if not cut.through and not cut.is_surface:
                center = to_screen(shape.x_mm, shape.y_mm, top)
                painter.setPen(QPen(QColor("#0d0d0d")))
                painter.drawText(
                    center, f"{cut.depth_in_layer_mm:.0f} mm"
                )

        # Étiquette de couche, dans la marge droite.
        anchor = to_screen(w, 0, top)
        painter.setPen(QPen(QColor("#42a5f5") if selected else QColor("#dddddd")))
        font = painter.font()
        font.setPointSize(10)
        font.setBold(selected)
        painter.setFont(font)
        n_cuts = len([c for c in assignment.cuts if not c.is_surface])
        painter.drawText(
            QPointF(anchor.x() + 16, anchor.y()),
            f"C{assignment.index} · {thickness:.0f} mm · "
            f"{assignment.layer.role.label} · {n_cuts} découpe(s)",
        )
        font.setBold(False)
        painter.setFont(font)

    # ------------------------------------------------------------------ #
    def mousePressEvent(self, event) -> None:  # noqa: N802
        position = event.position()
        # Les zones sont empilées du fond vers le haut : tester à l'envers
        # pour sélectionner la couche dessinée au-dessus.
        for polygon, index in reversed(self._hit_zones):
            if polygon.containsPoint(position, Qt.FillRule.OddEvenFill):
                self._selected = None if self._selected == index else index
                self.layer_clicked.emit(index)
                self.update()
                return


class ExplodedView(QWidget):
    """Vue éclatée complète : diagramme + visibilité des couches."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project: Project | None = None
        self._checkboxes: list[QCheckBox] = []

        layout = QHBoxLayout(self)
        self.diagram = ExplodedDiagram(self)
        layout.addWidget(self.diagram, stretch=1)

        side = QVBoxLayout()
        side.addWidget(QLabel("Couches visibles :"))
        self._checks_layout = QVBoxLayout()
        side.addLayout(self._checks_layout)
        side.addStretch()
        hint = QLabel(
            "Cliquez une couche dans le\nschéma pour la sélectionner."
        )
        hint.setStyleSheet("color: #888888;")
        side.addWidget(hint)
        layout.addLayout(side)

        self.diagram.layer_clicked.connect(lambda _i: None)

    # ------------------------------------------------------------------ #
    def set_project(self, project: Project) -> None:
        self._project = project
        self.diagram.set_project(project)
        self.rebuild_checkboxes()

    def refresh(self) -> None:
        """Après modification du modèle (profondeurs, couches...)."""
        if self._project is not None and (
            len(self._checkboxes) != len(self._project.foam_layers or [1])
        ):
            self.rebuild_checkboxes()
        self.diagram.refresh()

    def rebuild_checkboxes(self) -> None:
        for checkbox in self._checkboxes:
            checkbox.deleteLater()
        self._checkboxes = []
        project = self._project
        if project is None:
            return
        count = len(project.foam_layers) or 1
        # Du haut de la pile vers le fond, comme une coupe.
        for index in range(count, 0, -1):
            role = (
                project.foam_layers[index - 1].role.label
                if project.foam_layers else LayerRole.CUTOUT.label
            )
            checkbox = QCheckBox(f"Couche {index} ({role})")
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._on_visibility_changed)
            self._checks_layout.addWidget(checkbox)
            checkbox.setProperty("ff_layer_index", index)
            self._checkboxes.append(checkbox)

    def _on_visibility_changed(self) -> None:
        hidden = {
            checkbox.property("ff_layer_index")
            for checkbox in self._checkboxes
            if not checkbox.isChecked()
        }
        self.diagram.set_hidden(hidden)
