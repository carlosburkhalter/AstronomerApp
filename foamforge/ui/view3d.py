"""Vue 3D isométrique de l'empilement de mousse (QPainter pur).

Rendu volontairement simple et robuste : projection isométrique dessinée
avec QPainter, sans dépendance Qt3D/OpenGL. Montre l'empilement des
couches, les poches (avec leur profondeur), les découpes traversantes
(fond coloré visible) et l'épaisseur totale.

Projection : iso(x, y, z) =
    écran_x = (x − y) · cos(30°)
    écran_y = (x + y) · sin(30°) − z
avec z vers le haut (z = 0 au bas de la pile de mousse).
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QWidget
from shapely.geometry import Polygon

from foamforge.core.geometry import CutType, ShapeKind
from foamforge.core.layers import LayerRole
from foamforge.core.project import Project

_COS30 = math.cos(math.radians(30))
_SIN30 = math.sin(math.radians(30))

# Couleurs des rôles de couche (parois latérales).
_ROLE_COLORS = {
    LayerRole.BOTTOM: "#4a4a4a",
    LayerRole.SPACER: "#5a5a5a",
    LayerRole.CUTOUT: "#3a3a3a",
    LayerRole.SUPPORT: "#5f5f5f",
}


def _iso(x: float, y: float, z: float) -> QPointF:
    """Projette un point 3D (mm) dans le plan écran isométrique (mm)."""
    return QPointF((x - y) * _COS30, (x + y) * _SIN30 - z)


class FoamView3D(QWidget):
    """Widget de visualisation isométrique de la mousse."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project: Project | None = None
        self.setMinimumSize(400, 300)

    def set_project(self, project: Project) -> None:
        self._project = project
        self.update()

    def refresh(self) -> None:
        """À appeler après toute modification du projet."""
        self.update()

    # ------------------------------------------------------------------ #
    # Géométrie de l'empilement
    # ------------------------------------------------------------------ #
    def _stack(self) -> list[tuple[float, float, LayerRole]]:
        """Couches (z_bas, épaisseur, rôle) du fond vers le haut.

        Sans empilement défini : une couche unique CUTOUT de l'épaisseur
        de la plaque.
        """
        project = self._project
        assert project is not None
        if project.foam_layers:
            stack = []
            z = 0.0
            for layer in project.foam_layers:
                stack.append((z, layer.thickness_mm, layer.role))
                z += layer.thickness_mm
            return stack
        return [(0.0, project.sheet.thickness_mm, LayerRole.CUTOUT)]

    def _cut_surface_top_mm(self) -> float:
        """Altitude (z) de la surface où les poches commencent : sommet de
        la pile découpable (sous le couvercle éventuel)."""
        top = 0.0
        for z, thickness, role in self._stack():
            if role is LayerRole.CUTOUT:
                top = max(top, z + thickness)
        return top

    # ------------------------------------------------------------------ #
    # Rendu
    # ------------------------------------------------------------------ #
    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#202020"))
        project = self._project
        if project is None:
            painter.end()
            return

        sheet = project.sheet
        stack = self._stack()
        total_height = sum(t for _, t, _ in stack)

        # Cadrage : projeter les 8 coins du bloc pour calculer l'échelle.
        corners = [
            _iso(x, y, z)
            for x in (0.0, sheet.width_mm)
            for y in (0.0, sheet.height_mm)
            for z in (0.0, total_height)
        ]
        min_x = min(p.x() for p in corners)
        max_x = max(p.x() for p in corners)
        min_y = min(p.y() for p in corners)
        max_y = max(p.y() for p in corners)
        margin = 30
        scale = min(
            (self.width() - 2 * margin) / max(max_x - min_x, 1.0),
            (self.height() - 2 * margin) / max(max_y - min_y, 1.0),
        )
        painter.translate(
            margin + (self.width() - 2 * margin - (max_x - min_x) * scale) / 2
            - min_x * scale,
            margin + (self.height() - 2 * margin - (max_y - min_y) * scale) / 2
            - min_y * scale,
        )
        painter.scale(scale, scale)

        self._paint_block(painter, project, stack, total_height)
        painter.resetTransform()
        self._paint_legend(painter, project, stack, total_height)
        painter.end()

    def _paint_block(
        self,
        painter: QPainter,
        project: Project,
        stack: list[tuple[float, float, LayerRole]],
        total_height: float,
    ) -> None:
        sheet = project.sheet
        w, h = sheet.width_mm, sheet.height_mm
        pen = QPen(QColor("#111111"), 0.5)
        pen.setCosmetic(True)

        # Parois latérales, couche par couche (du fond vers le haut ;
        # les faces visibles en projection iso sont x = w et y = h).
        for z, thickness, role in stack:
            color = QColor(_ROLE_COLORS[role])
            z_top = z + thickness
            front = QPolygonF([
                _iso(0, h, z), _iso(w, h, z),
                _iso(w, h, z_top), _iso(0, h, z_top),
            ])
            side = QPolygonF([
                _iso(w, h, z), _iso(w, 0, z),
                _iso(w, 0, z_top), _iso(w, h, z_top),
            ])
            painter.setPen(pen)
            painter.setBrush(color)
            painter.drawPolygon(front)
            painter.setBrush(color.darker(125))
            painter.drawPolygon(side)

        # Face supérieure : mousse, puis poches en creux.
        top_z = total_height
        painter.setBrush(QColor(project.foam_color).lighter(140))
        painter.setPen(pen)
        painter.drawPolygon(QPolygonF([
            _iso(0, 0, top_z), _iso(w, 0, top_z),
            _iso(w, h, top_z), _iso(0, h, top_z),
        ]))

        cut_top = self._cut_surface_top_mm()
        cuttable = project.cuttable_depth_mm()
        shapes = sorted(
            (s for s in project.shapes if s.kind is not ShapeKind.TEXT),
            key=lambda s: (s.y_mm, s.x_mm),
        )
        for shape in shapes:
            polygon = shape.cut_polygon()
            if shape.spec.cut_type == CutType.ENGRAVE:
                depth = min(shape.spec.depth_mm, 2.0)
            elif shape.spec.cut_type == CutType.FULL:
                depth = cuttable
            else:
                depth = min(shape.spec.depth_mm, cuttable)
            floor_z = cut_top - depth
            is_through = shape.spec.cut_type == CutType.FULL

            # Si un couvercle recouvre la zone découpable, les poches
            # restent dessinées sur la face visible (lisibilité avant tout).
            self._paint_pocket(
                painter, polygon, top_z, floor_z,
                floor_color=(
                    QColor(project.background_color) if is_through
                    else QColor(project.foam_color).lighter(190)
                ),
            )
            # Étiquette de profondeur au centre du logement.
            center = _iso(shape.x_mm, shape.y_mm, floor_z)
            painter.setPen(QPen(QColor("#ffffff")))
            font = painter.font()
            font.setPointSizeF(max(polygon.bounds[2] - polygon.bounds[0], 20) / 8)
            painter.setFont(font)
            label = (
                "traversante" if is_through
                else f"{shape.spec.depth_mm:.0f} mm"
            )
            painter.drawText(center, f"{shape.spec.name} · {label}")

    def _paint_pocket(
        self,
        painter: QPainter,
        polygon: Polygon,
        top_z: float,
        floor_z: float,
        floor_color: QColor,
    ) -> None:
        """Dessine une poche : parois (assombries) puis fond projeté."""
        coords = list(polygon.exterior.coords)
        wall_pen = QPen(QColor("#161616"), 0.3)
        wall_pen.setCosmetic(True)
        painter.setPen(wall_pen)
        # Parois : un quadrilatère par arête du contour. L'ordre de dessin
        # (arêtes « arrière » d'abord) suffit pour une lecture correcte.
        walls = []
        for (x1, y1), (x2, y2) in zip(coords, coords[1:]):
            depth_key = (x1 + y1 + x2 + y2) / 2  # tri arrière → avant
            walls.append((depth_key, QPolygonF([
                _iso(x1, y1, top_z), _iso(x2, y2, top_z),
                _iso(x2, y2, floor_z), _iso(x1, y1, floor_z),
            ])))
        painter.setBrush(QColor(30, 30, 30, 200))
        for _, wall in sorted(walls, key=lambda item: item[0]):
            painter.drawPolygon(wall)
        # Fond de la poche.
        floor_path = QPainterPath()
        first = _iso(*coords[0], floor_z)
        floor_path.moveTo(first)
        for x, y in coords[1:]:
            floor_path.lineTo(_iso(x, y, floor_z))
        floor_path.closeSubpath()
        painter.setBrush(floor_color)
        painter.drawPath(floor_path)

    def _paint_legend(
        self,
        painter: QPainter,
        project: Project,
        stack: list[tuple[float, float, LayerRole]],
        total_height: float,
    ) -> None:
        painter.setPen(QPen(QColor("#dddddd")))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        lines = [
            f"{project.name} — {project.sheet.width_mm:.0f} × "
            f"{project.sheet.height_mm:.0f} mm, "
            f"épaisseur totale {total_height:.0f} mm",
        ]
        if project.foam_layers:
            stack_text = " + ".join(
                f"{t:.0f} ({role.label})" for _, t, role in stack
            )
            lines.append(f"Empilement (fond → haut) : {stack_text}")
        else:
            lines.append("Plaque unique (aucun empilement calculé)")
        for i, line in enumerate(lines):
            painter.drawText(12, 20 + i * 18, line)
