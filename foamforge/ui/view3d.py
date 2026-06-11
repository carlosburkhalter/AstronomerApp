"""Vue 3D interactive de la mousse (QPainter pur, sans OpenGL).

Visualiseur de travail, pas seulement décoratif :

- **rotation** : clic gauche + déplacement (orbite azimut/élévation) ;
- **zoom** : molette ; **pan** : clic milieu ou droit + déplacement ;
- **sélection** : clic gauche (sans déplacement) sur un logement
  sélectionne l'objet, synchronisé avec la vue 2D ;
- **couches** : effeuillage depuis le dessus (les couches masquées
  révèlent les découpes des couches inférieures) ;
- fiche de l'objet sélectionné : dimensions, profondeur de poche,
  hauteur réelle, couches traversées.

Choix d'implémentation : projection orthographique + algorithme du
peintre en QPainter pur. Aucune dépendance OpenGL/Qt3D : c'est notre
« fallback » permanent — il fonctionne partout, y compris en rendu
offscreen et sur machines sans accélération. La géométrie vient de
Shapely (mêmes polygones que l'export : la 3D est fidèle à la découpe).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QWidget
from shapely.geometry import Polygon
from shapely.ops import unary_union

from foamforge.core.geometry import CutType, Shape, ShapeKind
from foamforge.core.layers import LayerRole
from foamforge.core.project import Project

# Couleurs des rôles de couche (parois latérales).
_ROLE_COLORS = {
    LayerRole.BOTTOM: "#4a4a4a",
    LayerRole.SPACER: "#5a5a5a",
    LayerRole.CUTOUT: "#3a3a3a",
    LayerRole.SUPPORT: "#5f5f5f",
}

# Tolérance de clic : en dessous de ce déplacement (px), un drag est un clic.
_CLICK_TOLERANCE_PX = 4


@dataclass
class _Face:
    """Face 3D prête au rendu (algorithme du peintre)."""

    points: QPolygonF            # points projetés à l'écran
    depth: float                 # profondeur caméra moyenne (tri)
    fill: QColor
    path: QPainterPath | None = None   # pour les faces à trous
    shape_id: str | None = None        # face cliquable d'un logement
    outline: QColor | None = None


@dataclass
class _SceneGeometry:
    """Géométrie 3D reconstruite à chaque rendu."""

    faces: list[_Face] = field(default_factory=list)
    # Polygones écran des ouvertures de logements, pour le picking.
    pick_zones: list[tuple[QPolygonF, str]] = field(default_factory=list)


class FoamView3D(QWidget):
    """Visualiseur 3D orbital de la mousse."""

    shape_clicked = Signal(str)  # id de la forme cliquée dans la vue 3D

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project: Project | None = None
        self.setMinimumSize(400, 300)
        self.setMouseTracking(False)

        # Caméra orbitale.
        self._azimuth_deg = 35.0     # rotation autour de l'axe vertical
        self._elevation_deg = 55.0   # 90 = vue de dessus
        self._zoom = 1.0
        self._pan = QPointF(0.0, 0.0)

        # Interaction en cours.
        self._drag_button: Qt.MouseButton | None = None
        self._drag_origin = QPointF()
        self._drag_last = QPointF()
        self._drag_moved = False

        # État d'affichage.
        self._selected_ids: set[str] = set()
        self._visible_layer_count: int | None = None  # None = toutes
        self._show_labels = True
        self._geometry = _SceneGeometry()

    # ------------------------------------------------------------------ #
    # API
    # ------------------------------------------------------------------ #
    def set_project(self, project: Project) -> None:
        self._project = project
        self._visible_layer_count = None
        self.update()

    def refresh(self) -> None:
        """À appeler après toute modification du projet."""
        self.update()

    def set_selected_ids(self, shape_ids: list[str]) -> None:
        """Synchronise la surbrillance avec la sélection de la vue 2D."""
        new_ids = set(shape_ids)
        if new_ids != self._selected_ids:
            self._selected_ids = new_ids
            self.update()

    def set_visible_layer_count(self, count: int | None) -> None:
        """Effeuillage : nombre de couches visibles depuis le fond.

        ``None`` ou un nombre ≥ total = pile complète. Masquer les couches
        du dessus révèle les découpes des couches restantes (la surface
        visible descend, les profondeurs sont re-référencées).
        """
        self._visible_layer_count = count
        self.update()

    def set_show_labels(self, show: bool) -> None:
        self._show_labels = show
        self.update()

    def reset_camera(self) -> None:
        self._azimuth_deg, self._elevation_deg = 35.0, 55.0
        self._zoom, self._pan = 1.0, QPointF(0.0, 0.0)
        self.update()

    # ------------------------------------------------------------------ #
    # Pile de couches visible (effeuillage)
    # ------------------------------------------------------------------ #
    def _stack(self) -> list[tuple[float, float, LayerRole]]:
        """Couches visibles (z_bas, épaisseur, rôle), du fond vers le haut.

        Sans empilement défini : une couche unique CUTOUT de l'épaisseur
        de la plaque.
        """
        project = self._project
        assert project is not None
        if project.foam_layers:
            layers = list(project.foam_layers)
        else:
            from foamforge.core.layers import FoamLayer

            layers = [FoamLayer(project.sheet.thickness_mm, LayerRole.CUTOUT)]
        if self._visible_layer_count is not None:
            layers = layers[: max(self._visible_layer_count, 1)]
        stack = []
        z = 0.0
        for layer in layers:
            stack.append((z, layer.thickness_mm, layer.role))
            z += layer.thickness_mm
        return stack

    def _hidden_top_mm(self) -> float:
        """Épaisseur découpable masquée par l'effeuillage (depuis le haut)."""
        project = self._project
        assert project is not None
        if not project.foam_layers or self._visible_layer_count is None:
            return 0.0
        hidden = project.foam_layers[max(self._visible_layer_count, 1):]
        return sum(
            layer.thickness_mm for layer in hidden
            if layer.role is LayerRole.CUTOUT
        )

    # ------------------------------------------------------------------ #
    # Projection caméra
    # ------------------------------------------------------------------ #
    def _project_point(self, x: float, y: float, z: float) -> tuple[QPointF, float]:
        """Projette un point modèle (mm, z vers le haut) en coordonnées
        écran (avant cadrage), et retourne sa profondeur caméra."""
        az = math.radians(self._azimuth_deg)
        el = math.radians(self._elevation_deg)
        # Rotation azimut autour de Z.
        rx = x * math.cos(az) - y * math.sin(az)
        ry = x * math.sin(az) + y * math.cos(az)
        # Élévation : bascule de la caméra.
        screen_x = rx
        screen_y = ry * math.sin(el) - z * math.cos(el)
        depth = ry * math.cos(el) + z * math.sin(el)
        return QPointF(screen_x, screen_y), depth

    # ------------------------------------------------------------------ #
    # Construction de la scène
    # ------------------------------------------------------------------ #
    def _shape_visual(self, shape: Shape, cut_top: float, cuttable: float):
        """(polygone, profondeur effective, traversante, gravure) ou None
        si la forme est entièrement dans les couches masquées."""
        hidden = self._hidden_top_mm()
        if shape.spec.cut_type == CutType.ENGRAVE:
            depth = min(shape.spec.depth_mm, 2.0)
            if hidden > 0:
                return None  # la gravure de surface est masquée avec sa couche
            return shape.cut_polygon(), depth, False, True
        if shape.spec.cut_type == CutType.FULL:
            return shape.cut_polygon(), cuttable, True, False
        depth = min(shape.spec.depth_mm, cuttable + hidden) - hidden
        if depth <= 0:
            return None
        return shape.cut_polygon(), depth, False, False

    def _build_scene(self) -> _SceneGeometry:
        scene = _SceneGeometry()
        project = self._project
        assert project is not None
        sheet = project.sheet
        w, h = sheet.width_mm, sheet.height_mm
        stack = self._stack()
        top_z = sum(t for _, t, _ in stack)
        # Surface où commencent les poches : sommet des couches CUTOUT
        # visibles (les couches pleines au-dessus n'existent pas : la
        # couche supérieure d'un plan est toujours découpée).
        cut_top = max(
            (z + t for z, t, role in stack if role is LayerRole.CUTOUT),
            default=top_z,
        )
        cuttable = sum(t for _, t, role in stack if role is LayerRole.CUTOUT)

        def face(points_3d, fill, shape_id=None, outline=None):
            projected = []
            depth_sum = 0.0
            for x, y, z in points_3d:
                point, depth = self._project_point(x, y, z)
                projected.append(point)
                depth_sum += depth
            scene.faces.append(_Face(
                points=QPolygonF(projected),
                depth=depth_sum / len(points_3d),
                fill=fill,
                shape_id=shape_id,
                outline=outline,
            ))

        # --- Parois latérales du bloc, couche par couche ---------------- #
        for z, thickness, role in stack:
            color = QColor(_ROLE_COLORS[role])
            zt = z + thickness
            face([(0, 0, z), (w, 0, z), (w, 0, zt), (0, 0, zt)], color)
            face([(0, h, z), (w, h, z), (w, h, zt), (0, h, zt)], color)
            face([(0, 0, z), (0, h, z), (0, h, zt), (0, 0, zt)],
                 color.darker(120))
            face([(w, 0, z), (w, h, z), (w, h, zt), (w, 0, zt)],
                 color.darker(120))
        # Dessous du bloc.
        face([(0, 0, 0), (w, 0, 0), (w, h, 0), (0, h, 0)],
             QColor("#2b2b2b"))

        # --- Logements --------------------------------------------------- #
        shapes = [s for s in project.shapes if s.kind is not ShapeKind.TEXT]
        visuals: list[tuple[Shape, Polygon, float, bool, bool]] = []
        for shape in shapes:
            visual = self._shape_visual(shape, cut_top, cuttable)
            if visual is not None:
                polygon, depth, through, engrave = visual
                visuals.append((shape, polygon, depth, through, engrave))

        # --- Face supérieure : plaque moins les ouvertures --------------- #
        top_color = QColor(project.foam_color).lighter(150)
        openings = [
            polygon for _, polygon, _, _, engrave in visuals if not engrave
        ]
        top_surface = sheet.polygon().difference(
            unary_union(openings) if openings else Polygon()
        )
        top_geoms = (
            list(top_surface.geoms)
            if top_surface.geom_type == "MultiPolygon" else [top_surface]
        )
        for geometry in top_geoms:
            if geometry.is_empty:
                continue
            path = QPainterPath()
            depth_total, count = 0.0, 0
            for ring in [geometry.exterior, *geometry.interiors]:
                first = True
                for x, y in ring.coords:
                    point, depth = self._project_point(x, y, top_z)
                    depth_total += depth
                    count += 1
                    if first:
                        path.moveTo(point)
                        first = False
                    else:
                        path.lineTo(point)
                path.closeSubpath()
            scene.faces.append(_Face(
                points=QPolygonF(), depth=depth_total / max(count, 1),
                fill=top_color, path=path,
            ))

        # --- Poches : parois + fonds ------------------------------------- #
        for shape, polygon, depth, through, engrave in visuals:
            selected = shape.id in self._selected_ids
            floor_z = top_z - depth
            coords = list(polygon.exterior.coords)
            if engrave:
                # Gravure : simple trait sur la surface.
                pts = []
                depth_sum = 0.0
                for x, y in coords:
                    point, d = self._project_point(x, y, top_z + 0.1)
                    pts.append(point)
                    depth_sum += d
                scene.faces.append(_Face(
                    points=QPolygonF(pts), depth=depth_sum / len(coords),
                    fill=QColor(0, 0, 0, 0),
                    outline=QColor("#80cbc4"), shape_id=shape.id,
                ))
                continue
            # Parois intérieures (triées arrière → avant par la profondeur).
            wall_color = QColor("#262626")
            if selected:
                wall_color = QColor("#1e3a5f")
            for (x1, y1), (x2, y2) in zip(coords, coords[1:]):
                face(
                    [(x1, y1, top_z), (x2, y2, top_z),
                     (x2, y2, floor_z), (x1, y1, floor_z)],
                    wall_color, shape_id=shape.id,
                )
            # Fond de poche (ou fond de valise si traversante).
            floor_color = (
                QColor(project.background_color) if through
                else QColor(project.foam_color).lighter(200)
            )
            if selected:
                floor_color = floor_color.lighter(130)
            pts = []
            depth_sum = 0.0
            for x, y in coords:
                point, d = self._project_point(x, y, floor_z)
                pts.append(point)
                depth_sum += d
            floor_face = _Face(
                points=QPolygonF(pts),
                depth=depth_sum / len(coords),
                fill=floor_color,
                shape_id=shape.id,
                outline=QColor("#42a5f5") if selected else None,
            )
            scene.faces.append(floor_face)
            # Zone de picking : l'OUVERTURE en surface (plus naturelle à
            # cliquer que le fond, et toujours face caméra en vue plongée).
            opening = []
            for x, y in coords:
                point, _ = self._project_point(x, y, top_z)
                opening.append(point)
            scene.pick_zones.append((QPolygonF(opening), shape.id))

        scene.faces.sort(key=lambda f: f.depth)
        return scene

    # ------------------------------------------------------------------ #
    # Rendu
    # ------------------------------------------------------------------ #
    def _view_transform(self) -> tuple[float, QPointF]:
        """Échelle et décalage écran pour cadrer le bloc projeté."""
        project = self._project
        assert project is not None
        sheet = project.sheet
        stack = self._stack()
        top_z = sum(t for _, t, _ in stack)
        xs, ys = [], []
        for x in (0.0, sheet.width_mm):
            for y in (0.0, sheet.height_mm):
                for z in (0.0, top_z):
                    point, _ = self._project_point(x, y, z)
                    xs.append(point.x())
                    ys.append(point.y())
        span_x = max(xs) - min(xs) or 1.0
        span_y = max(ys) - min(ys) or 1.0
        margin = 40
        scale = min(
            (self.width() - 2 * margin) / span_x,
            (self.height() - 2 * margin) / span_y,
        ) * self._zoom
        center = QPointF(
            (max(xs) + min(xs)) / 2 * scale,
            (max(ys) + min(ys)) / 2 * scale,
        )
        offset = (
            QPointF(self.width() / 2, self.height() / 2) - center + self._pan
        )
        return scale, offset

    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#202020"))
        if self._project is None:
            painter.end()
            return

        self._geometry = self._build_scene()
        scale, offset = self._view_transform()
        pen = QPen(QColor("#141414"), 0.7)
        pen.setCosmetic(True)

        painter.save()
        painter.translate(offset)
        painter.scale(scale, scale)
        for face in self._geometry.faces:
            outline_pen = pen
            if face.outline is not None:
                outline_pen = QPen(face.outline, 2.0 / scale)
            painter.setPen(outline_pen)
            painter.setBrush(face.fill)
            if face.path is not None:
                painter.drawPath(face.path)
            elif not face.points.isEmpty():
                painter.drawPolygon(face.points)
        painter.restore()

        if self._show_labels:
            self._paint_labels(painter, scale, offset)
        self._paint_hud(painter)
        painter.end()

    def _paint_labels(
        self, painter: QPainter, scale: float, offset: QPointF
    ) -> None:
        """Noms des logements, dessinés en sur-impression écran."""
        project = self._project
        assert project is not None
        stack = self._stack()
        top_z = sum(t for _, t, _ in stack)
        painter.setPen(QPen(QColor("#eceff1")))
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        for shape in project.shapes:
            if shape.kind is ShapeKind.TEXT:
                continue
            point, _ = self._project_point(shape.x_mm, shape.y_mm, top_z)
            screen = point * scale + offset
            label = shape.spec.name
            if shape.id in self._selected_ids:
                label = f"▶ {label}"
            painter.drawText(screen, label)

    def _paint_hud(self, painter: QPainter) -> None:
        """Légende + fiche de l'objet sélectionné."""
        project = self._project
        assert project is not None
        painter.setPen(QPen(QColor("#dddddd")))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        stack = self._stack()
        total = sum(t for _, t, _ in stack)
        lines = [
            f"{project.name} — {project.sheet.width_mm:.0f} × "
            f"{project.sheet.height_mm:.0f} mm — visible : {total:.0f} mm "
            f"({len(stack)} couche(s))",
            "Glisser : tourner · molette : zoom · clic milieu/droit : "
            "déplacer · clic : sélectionner",
        ]
        for i, line in enumerate(lines):
            painter.drawText(12, 20 + i * 17, line)

        # Fiche de l'objet sélectionné (outil de travail, pas décoration).
        selected = [
            s for s in project.shapes if s.id in self._selected_ids
            and s.kind is not ShapeKind.TEXT
        ]
        if len(selected) != 1:
            return
        shape = selected[0]
        minx, miny, maxx, maxy = shape.cut_polygon().bounds
        crossed = self._layers_crossed(shape)
        info = [
            f"▶ {shape.spec.name}",
            f"Empreinte : {maxx - minx:.1f} × {maxy - miny:.1f} mm",
            f"Profondeur de poche : {shape.spec.depth_mm:.1f} mm"
            + (" (traversante)" if shape.spec.cut_type == CutType.FULL else ""),
        ]
        if shape.spec.object_height_mm > 0:
            info.append(
                f"Hauteur réelle de l'objet : "
                f"{shape.spec.object_height_mm:.1f} mm"
            )
        info.append(f"Couches traversées : {crossed or '—'}")
        metrics = painter.fontMetrics()
        box_width = max(metrics.horizontalAdvance(t) for t in info) + 24
        box_height = len(info) * 18 + 14
        x0 = self.width() - box_width - 12
        y0 = 12
        painter.setBrush(QColor(20, 20, 20, 215))
        painter.setPen(QPen(QColor("#42a5f5")))
        painter.drawRoundedRect(x0, y0, box_width, box_height, 6, 6)
        painter.setPen(QPen(QColor("#eceff1")))
        for i, line in enumerate(info):
            painter.drawText(x0 + 12, y0 + 22 + i * 18, line)

    def _layers_crossed(self, shape: Shape) -> str:
        """Description des couches que la forme découpe (ex. « 3, 4 »)."""
        project = self._project
        assert project is not None
        if not project.foam_layers:
            return "plaque unique"
        crossed = [
            str(assignment.index)
            for assignment in project.layer_assignments()
            if any(c.shape_id == shape.id for c in assignment.cuts)
        ]
        return ", ".join(crossed)

    # ------------------------------------------------------------------ #
    # Interaction souris
    # ------------------------------------------------------------------ #
    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._drag_button = event.button()
        self._drag_origin = event.position()
        self._drag_last = event.position()
        self._drag_moved = False

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_button is None:
            return
        delta = event.position() - self._drag_last
        self._drag_last = event.position()
        if (event.position() - self._drag_origin).manhattanLength() \
                > _CLICK_TOLERANCE_PX:
            self._drag_moved = True
        if self._drag_button == Qt.MouseButton.LeftButton:
            self._azimuth_deg = (self._azimuth_deg + delta.x() * 0.5) % 360
            self._elevation_deg = min(
                89.0, max(10.0, self._elevation_deg + delta.y() * 0.5)
            )
            self.update()
        elif self._drag_button in (
            Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton
        ):
            self._pan += delta
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        button = self._drag_button
        self._drag_button = None
        if (
            button == Qt.MouseButton.LeftButton
            and not self._drag_moved
        ):
            self._pick(event.position())

    def wheelEvent(self, event) -> None:  # noqa: N802
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom = min(8.0, max(0.2, self._zoom * factor))
        self.update()

    def _pick(self, position: QPointF) -> None:
        """Sélectionne le logement sous le curseur (ouvertures projetées)."""
        scale, offset = self._view_transform()
        model_point = (position - offset) / scale
        # Zones testées de la plus « proche caméra » à la plus lointaine :
        # les pick_zones sont déjà dans l'ordre des faces, on parcourt à
        # l'envers pour privilégier ce qui est dessiné au-dessus.
        for polygon, shape_id in reversed(self._geometry.pick_zones):
            if polygon.containsPoint(model_point, Qt.FillRule.OddEvenFill):
                self.shape_clicked.emit(shape_id)
                return
