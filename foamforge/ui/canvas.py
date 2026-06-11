"""Canvas d'édition 2D : grille millimétrique, zoom, sélection, dessin.

Convention : 1 unité de scène = 1 mm. L'origine (0, 0) est le coin
haut-gauche de la plaque de mousse, axe Y vers le bas (convention écran ;
l'export DXF rétablit l'axe machine).
"""

from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QTransform,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QInputDialog,
    QStyleOptionGraphicsItem,
    QWidget,
)
from shapely.geometry import Polygon

from foamforge.core.geometry import (
    CircleShape,
    CutoutSpec,
    CutType,
    EllipseShape,
    RectShape,
    Shape,
    ShapeKind,
    TextShape,
)
from foamforge.core.project import Project
from foamforge.core.units import snap
from foamforge.core.validation import Severity


class Tool(Enum):
    """Outil actif du canvas."""

    SELECT = auto()
    RECT = auto()
    CIRCLE = auto()
    ELLIPSE = auto()
    TEXT = auto()


def _polygon_to_path(polygon: Polygon, dx: float = 0.0, dy: float = 0.0) -> QPainterPath:
    """Convertit un polygone Shapely en chemin Qt (décalé en local)."""
    path = QPainterPath()
    rings = [polygon.exterior, *polygon.interiors]
    for ring in rings:
        coords = list(ring.coords)
        path.moveTo(coords[0][0] + dx, coords[0][1] + dy)
        for x, y in coords[1:]:
            path.lineTo(x + dx, y + dy)
        path.closeSubpath()
    return path


class ShapeItem(QGraphicsItem):
    """Élément graphique lié à une forme du modèle.

    La position de l'item correspond au centre (x_mm, y_mm) de la forme ;
    le chemin de découpe est dessiné en coordonnées locales.
    """

    def __init__(self, shape: Shape, canvas: "FoamCanvas") -> None:
        super().__init__()
        self.model = shape
        self._canvas = canvas
        self._severity: Severity | None = None
        self._syncing = False
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.sync_from_model()

    # ------------------------------------------------------------------ #
    def sync_from_model(self) -> None:
        """Recalcule les chemins après modification du modèle."""
        self.prepareGeometryChange()
        shape = self.model
        # Chemins en coordonnées locales (centre de la forme à l'origine).
        self._cut_path = _polygon_to_path(
            shape.cut_polygon(), -shape.x_mm, -shape.y_mm
        )
        self._object_path = _polygon_to_path(
            shape.object_polygon(), -shape.x_mm, -shape.y_mm
        )
        self._bounds = self._cut_path.boundingRect().adjusted(-2, -2, 2, 2)
        self._syncing = True
        try:
            self.setPos(shape.x_mm, shape.y_mm)
        finally:
            self._syncing = False
        self.update()

    def set_severity(self, severity: Severity | None) -> None:
        """Colore le contour selon la pire alerte touchant cette forme."""
        if severity is not self._severity:
            self._severity = severity
            self.update()

    # ------------------------------------------------------------------ #
    def boundingRect(self) -> QRectF:  # noqa: N802 (API Qt)
        return self._bounds

    def shape(self) -> QPainterPath:  # type: ignore[override]  # noqa: A003
        return self._cut_path

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        shape = self.model
        is_text = shape.kind is ShapeKind.TEXT

        # Remplissage : fond de valise visible pour découpe complète,
        # mousse éclaircie pour une poche. Comparaison par égalité (et non
        # .value / is) : tolère un cut_type revenu en str pur via Qt.
        project = self._canvas.project
        if shape.spec.cut_type == CutType.FULL:
            fill = QColor(project.background_color)
        else:
            fill = QColor(project.foam_color).lighter(180)
        fill.setAlpha(110 if is_text else 230)

        outline = QColor("#eeeeee")
        if self._severity is Severity.ERROR:
            outline = QColor(Severity.ERROR.color)
        elif self._severity is Severity.WARNING:
            outline = QColor(Severity.WARNING.color)
        if self.isSelected():
            outline = QColor("#42a5f5")

        pen = QPen(outline, 0.6)
        pen.setCosmetic(False)
        painter.setPen(pen)
        painter.setBrush(QBrush(fill))
        painter.drawPath(self._cut_path)

        # Contour de l'objet (sans marge) en pointillés : montre la marge.
        if not is_text and shape.spec.margin_mm > 0:
            dashed = QPen(QColor("#90caf9"), 0.3, Qt.PenStyle.DashLine)
            painter.setPen(dashed)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(self._object_path)

        # Étiquette : nom + dimensions réelles en mm.
        rect = self._cut_path.boundingRect()
        label = (
            shape.text if isinstance(shape, TextShape)
            else f"{shape.spec.name}\n{rect.width():.0f} × {rect.height():.0f} mm"
        )
        painter.setPen(QPen(QColor("#ffffff")))
        font = painter.font()
        font.setPointSizeF(max(min(rect.height() / 6.0, 6.0), 2.5))
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

    # ------------------------------------------------------------------ #
    def itemChange(self, change, value):  # noqa: N802 (API Qt)
        if (
            change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
            and not self._syncing
        ):
            # Magnétisme : grille, puis centres/bords (aides de placement).
            step = self._canvas.project.grid_step_mm
            point: QPointF = value
            snapped = QPointF(snap(point.x(), step), snap(point.y(), step))
            return self._canvas.snap_with_aids(self, snapped)
        if (
            change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
            and not self._syncing
        ):
            self.model.move_to(self.pos().x(), self.pos().y())
            self._canvas.notify_model_changed()
        return super().itemChange(change, value)


class FoamCanvas(QGraphicsView):
    """Vue d'édition : grille, zoom (molette), pan (clic milieu), dessin."""

    model_changed = Signal()              # géométrie modifiée (→ validation)
    selection_changed = Signal(list)      # liste de Shape sélectionnées
    cursor_moved = Signal(float, float)   # position curseur en mm

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = Project()
        self.active_tool = Tool.SELECT
        self._rubber_item: QGraphicsRectItem | None = None
        self._draw_origin: QPointF | None = None
        self._panning = False
        self._pan_anchor = QPointF()
        # Ordre chronologique de sélection (ids) : nécessaire aux opérations
        # booléennes où l'ordre compte (base de soustraction = 1re forme).
        self._selection_order: list[str] = []
        # Aides de placement (centres, axes, guides, snap intelligents).
        # Purement visuelles : jamais présentes dans les exports.
        self.aids_enabled = True
        self._guides: list[tuple[str, float]] = []  # ('v'|'h', valeur mm)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMouseTracking(True)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self._scene.selectionChanged.connect(self._on_selection_changed)

    # ------------------------------------------------------------------ #
    # Projet ↔ scène
    # ------------------------------------------------------------------ #
    def set_project(self, project: Project) -> None:
        self.project = project
        self.rebuild_scene()
        self.fit_sheet()

    def rebuild_scene(self) -> None:
        self._scene.clear()
        self._rubber_item = None
        sheet = self.project.sheet
        margin = 60
        self._scene.setSceneRect(
            -margin, -margin, sheet.width_mm + 2 * margin,
            sheet.height_mm + 2 * margin,
        )
        for shape in self.project.shapes:
            self._scene.addItem(ShapeItem(shape, self))

    def fit_sheet(self) -> None:
        """Ajuste le zoom pour voir toute la plaque."""
        sheet = self.project.sheet
        self.fitInView(
            QRectF(-20, -20, sheet.width_mm + 40, sheet.height_mm + 40),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

    def shape_items(self) -> list[ShapeItem]:
        return [i for i in self._scene.items() if isinstance(i, ShapeItem)]

    def item_for(self, shape_id: str) -> ShapeItem | None:
        for item in self.shape_items():
            if item.model.id == shape_id:
                return item
        return None

    def selected_shapes(self) -> list[Shape]:
        return [
            item.model
            for item in self._scene.selectedItems()
            if isinstance(item, ShapeItem)
        ]

    def refresh_shape(self, shape: Shape) -> None:
        """À appeler après modification du modèle (panneau propriétés)."""
        item = self.item_for(shape.id)
        if item is not None:
            item.sync_from_model()
        self.notify_model_changed()

    def notify_model_changed(self) -> None:
        self.model_changed.emit()

    def apply_severities(self, severities: dict[str, Severity]) -> None:
        """Met en évidence les formes concernées par des alertes."""
        for item in self.shape_items():
            item.set_severity(severities.get(item.model.id))

    # ------------------------------------------------------------------ #
    # Actions d'édition
    # ------------------------------------------------------------------ #
    def add_shape(self, shape: Shape, select: bool = True) -> None:
        self.project.add_shape(shape)
        item = ShapeItem(shape, self)
        self._scene.addItem(item)
        if select:
            self._scene.clearSelection()
            item.setSelected(True)
        self.notify_model_changed()

    def delete_selection(self) -> None:
        for item in list(self._scene.selectedItems()):
            if isinstance(item, ShapeItem):
                self.project.remove_shape(item.model.id)
                self._scene.removeItem(item)
        self.notify_model_changed()

    def duplicate_selection(self) -> None:
        for shape in self.selected_shapes():
            self.add_shape(shape.duplicate())

    def set_tool(self, tool: Tool) -> None:
        self.active_tool = tool
        self.setDragMode(
            QGraphicsView.DragMode.RubberBandDrag
            if tool is Tool.SELECT
            else QGraphicsView.DragMode.NoDrag
        )

    # ------------------------------------------------------------------ #
    # Fond : plaque de mousse + grille millimétrique
    # ------------------------------------------------------------------ #
    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:  # noqa: N802
        painter.fillRect(rect, QColor("#262626"))
        sheet = self.project.sheet
        sheet_rect = QRectF(0, 0, sheet.width_mm, sheet.height_mm)
        # Fond coloré (objets manquants) puis plaque de mousse par-dessus.
        painter.fillRect(sheet_rect, QColor(self.project.background_color))
        painter.fillRect(sheet_rect, QColor(self.project.foam_color))
        painter.setPen(QPen(QColor("#ffffff"), 0.4))
        painter.drawRect(sheet_rect)

        # Grille : pas fin de 1 mm visible seulement à fort zoom.
        zoom = self.transform().m11()
        grid_area = rect.intersected(sheet_rect)
        if grid_area.isEmpty():
            return
        steps = [(10.0, QColor(255, 255, 255, 40))]
        if zoom > 6:
            steps.insert(0, (1.0, QColor(255, 255, 255, 15)))
        for step, color in steps:
            pen = QPen(color, 0)
            painter.setPen(pen)
            x = step * int(grid_area.left() / step)
            while x <= grid_area.right():
                if 0 <= x <= sheet.width_mm:
                    painter.drawLine(
                        QPointF(x, grid_area.top()),
                        QPointF(x, grid_area.bottom()),
                    )
                x += step
            y = step * int(grid_area.top() / step)
            while y <= grid_area.bottom():
                if 0 <= y <= sheet.height_mm:
                    painter.drawLine(
                        QPointF(grid_area.left(), y),
                        QPointF(grid_area.right(), y),
                    )
                y += step

    # ------------------------------------------------------------------ #
    # Aides de placement : snap intelligent + guides d'alignement
    # ------------------------------------------------------------------ #
    def set_aids_enabled(self, enabled: bool) -> None:
        self.aids_enabled = enabled
        self._guides = []
        self.viewport().update()

    def clear_guides(self) -> None:
        if self._guides:
            self._guides = []
            self.viewport().update()

    def _snap_tolerance_mm(self) -> float:
        """Tolérance d'accrochage : ≈ 6 px à l'écran, plafonnée à 3 mm.

        Le plafond évite les « sauts » brutaux à faible zoom (et les
        accrochages parasites lors de déplacements programmatiques).
        """
        zoom = max(self.transform().m11(), 1e-6)
        return min(6.0 / zoom, 3.0)

    def snap_with_aids(self, item: ShapeItem, point: QPointF) -> QPointF:
        """Accrochage aux centres et bords (après le snap grille).

        Cibles, par axe : centre de la plaque, centres des autres formes,
        alignement bord à bord avec les autres formes. La cible la plus
        proche gagne ; les guides actifs sont mémorisés pour l'affichage.
        """
        if not self.aids_enabled:
            self.clear_guides()
            return point
        tolerance = self._snap_tolerance_mm()
        shape = item.model
        # Demi-empreinte de la découpe (constante pendant le drag).
        minx, miny, maxx, maxy = shape.cut_polygon().bounds
        left, right = minx - shape.x_mm, maxx - shape.x_mm
        top, bottom = miny - shape.y_mm, maxy - shape.y_mm

        sheet = self.project.sheet
        # (valeur cible pour le CENTRE, position du guide à afficher)
        targets_x: list[tuple[float, float]] = [
            (sheet.width_mm / 2, sheet.width_mm / 2),
        ]
        targets_y: list[tuple[float, float]] = [
            (sheet.height_mm / 2, sheet.height_mm / 2),
        ]
        for other in self.project.shapes:
            if other.id == shape.id:
                continue
            targets_x.append((other.x_mm, other.x_mm))
            targets_y.append((other.y_mm, other.y_mm))
            ominx, ominy, omaxx, omaxy = other.cut_polygon().bounds
            # Alignements bord à bord (gauche-gauche, droite-droite...).
            targets_x += [
                (ominx - left, ominx), (omaxx - right, omaxx),
                (ominx - right, ominx), (omaxx - left, omaxx),
            ]
            targets_y += [
                (ominy - top, ominy), (omaxy - bottom, omaxy),
                (ominy - bottom, ominy), (omaxy - top, omaxy),
            ]

        guides: list[tuple[str, float]] = []
        x, y = point.x(), point.y()
        best_x = min(targets_x, key=lambda t: abs(t[0] - x))
        if abs(best_x[0] - x) <= tolerance:
            x = best_x[0]
            guides.append(("v", best_x[1]))
        best_y = min(targets_y, key=lambda t: abs(t[0] - y))
        if abs(best_y[0] - y) <= tolerance:
            y = best_y[0]
            guides.append(("h", best_y[1]))

        if guides != self._guides:
            self._guides = guides
            self.viewport().update()
        return QPointF(x, y)

    # ------------------------------------------------------------------ #
    # Premier plan : aides visuelles (jamais exportées)
    # ------------------------------------------------------------------ #
    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:  # noqa: N802
        if not self.aids_enabled:
            return
        sheet = self.project.sheet
        zoom = max(self.transform().m11(), 1e-6)
        cx, cy = sheet.width_mm / 2, sheet.height_mm / 2

        # Axes X/Y de la plaque + croix du centre.
        axis_pen = QPen(QColor(255, 255, 255, 50), 0)
        axis_pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(axis_pen)
        painter.drawLine(QPointF(0, cy), QPointF(sheet.width_mm, cy))
        painter.drawLine(QPointF(cx, 0), QPointF(cx, sheet.height_mm))
        center_pen = QPen(QColor("#ffd54f"), 0)
        painter.setPen(center_pen)
        size = 8.0 / zoom
        painter.drawLine(QPointF(cx - size, cy), QPointF(cx + size, cy))
        painter.drawLine(QPointF(cx, cy - size), QPointF(cx, cy + size))

        # Centres de toutes les formes.
        mark_pen = QPen(QColor("#80deea"), 0)
        painter.setPen(mark_pen)
        mark = 4.0 / zoom
        for shape in self.project.shapes:
            painter.drawLine(
                QPointF(shape.x_mm - mark, shape.y_mm),
                QPointF(shape.x_mm + mark, shape.y_mm),
            )
            painter.drawLine(
                QPointF(shape.x_mm, shape.y_mm - mark),
                QPointF(shape.x_mm, shape.y_mm + mark),
            )

        # Guides d'alignement actifs (pendant un déplacement).
        guide_pen = QPen(QColor("#00e5ff"), 0)
        guide_pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(guide_pen)
        for orientation, value in self._guides:
            if orientation == "v":
                painter.drawLine(
                    QPointF(value, -20), QPointF(value, sheet.height_mm + 20)
                )
            else:
                painter.drawLine(
                    QPointF(-20, value), QPointF(sheet.width_mm + 20, value)
                )

        selected = self.selected_shapes()
        font = painter.font()
        font.setPointSizeF(max(9.0 / zoom, 2.0))
        painter.setFont(font)

        # Forme sélectionnée : coordonnées du centre + distances aux bords.
        if len(selected) == 1:
            shape = selected[0]
            minx, miny, maxx, maxy = shape.cut_polygon().bounds
            painter.setPen(QPen(QColor("#ffd54f"), 0))
            painter.drawText(
                QPointF(shape.x_mm + mark * 2, shape.y_mm - mark * 2),
                f"({shape.x_mm:.1f} ; {shape.y_mm:.1f}) mm",
            )
            distance_pen = QPen(QColor("#ffab91"), 0)
            distance_pen.setStyle(Qt.PenStyle.DotLine)
            painter.setPen(distance_pen)
            mid_y = (miny + maxy) / 2
            mid_x = (minx + maxx) / 2
            for x1, y1, x2, y2, label_value in (
                (0, mid_y, minx, mid_y, minx),
                (maxx, mid_y, sheet.width_mm, mid_y, sheet.width_mm - maxx),
                (mid_x, 0, mid_x, miny, miny),
                (mid_x, maxy, mid_x, sheet.height_mm,
                 sheet.height_mm - maxy),
            ):
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
                painter.drawText(
                    QPointF((x1 + x2) / 2, (y1 + y2) / 2 - 2.0 / zoom),
                    f"{label_value:.1f}",
                )

        # Deux formes sélectionnées : distances centre à centre et paroi.
        if len(selected) == 2:
            a, b = selected
            painter.setPen(QPen(QColor("#ce93d8"), 0, Qt.PenStyle.DashLine))
            painter.drawLine(
                QPointF(a.x_mm, a.y_mm), QPointF(b.x_mm, b.y_mm)
            )
            centers = (
                (a.x_mm - b.x_mm) ** 2 + (a.y_mm - b.y_mm) ** 2
            ) ** 0.5
            wall = a.cut_polygon().distance(b.cut_polygon())
            painter.setPen(QPen(QColor("#ce93d8"), 0))
            painter.drawText(
                QPointF((a.x_mm + b.x_mm) / 2, (a.y_mm + b.y_mm) / 2),
                f"centres : {centers:.1f} mm — paroi : {wall:.1f} mm",
            )

    # ------------------------------------------------------------------ #
    # Souris : zoom, pan, dessin
    # ------------------------------------------------------------------ #
    def wheelEvent(self, event) -> None:  # noqa: N802
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_anchor = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.active_tool is not Tool.SELECT
        ):
            scene_pos = self.mapToScene(event.position().toPoint())
            if self.active_tool is Tool.TEXT:
                self._create_text(scene_pos)
                return
            self._draw_origin = scene_pos
            self._rubber_item = self._scene.addRect(
                QRectF(scene_pos, scene_pos),
                QPen(QColor("#42a5f5"), 0.5, Qt.PenStyle.DashLine),
            )
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        scene_pos = self.mapToScene(event.position().toPoint())
        self.cursor_moved.emit(scene_pos.x(), scene_pos.y())
        if self._panning:
            delta = event.position() - self._pan_anchor
            self._pan_anchor = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            return
        if self._rubber_item is not None and self._draw_origin is not None:
            self._rubber_item.setRect(
                QRectF(self._draw_origin, scene_pos).normalized()
            )
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self.clear_guides()  # fin de déplacement : guides effacés
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        if self._rubber_item is not None:
            rect = self._rubber_item.rect()
            self._scene.removeItem(self._rubber_item)
            self._rubber_item = None
            self._draw_origin = None
            self._create_from_rect(rect)
            return
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------ #
    # Création de formes
    # ------------------------------------------------------------------ #
    def _create_from_rect(self, rect: QRectF) -> None:
        """Crée la forme correspondant au rectangle tracé à la souris."""
        step = self.project.grid_step_mm
        width = max(snap(rect.width(), step), 5.0)
        height = max(snap(rect.height(), step), 5.0)
        cx = snap(rect.center().x(), step)
        cy = snap(rect.center().y(), step)
        spec = CutoutSpec(name=f"Objet {len(self.project.shapes) + 1}")
        shape: Shape
        if self.active_tool is Tool.RECT:
            shape = RectShape(
                width_mm=width, height_mm=height, x_mm=cx, y_mm=cy, spec=spec
            )
        elif self.active_tool is Tool.CIRCLE:
            shape = CircleShape(
                diameter_mm=max(width, height), x_mm=cx, y_mm=cy, spec=spec
            )
        elif self.active_tool is Tool.ELLIPSE:
            shape = EllipseShape(
                width_mm=width, height_mm=height, x_mm=cx, y_mm=cy, spec=spec
            )
        else:
            return
        self.add_shape(shape)

    def _create_text(self, pos: QPointF) -> None:
        text, ok = QInputDialog.getText(
            self, "Texte gravé", "Texte à graver dans la mousse :"
        )
        if not ok or not text.strip():
            return
        step = self.project.grid_step_mm
        shape = TextShape(
            text=text.strip(),
            x_mm=snap(pos.x(), step),
            y_mm=snap(pos.y(), step),
            spec=CutoutSpec(name=f"Texte « {text.strip()[:20]} »"),
        )
        self.add_shape(shape)

    # ------------------------------------------------------------------ #
    def selected_shapes_ordered(self) -> list[Shape]:
        """Formes sélectionnées, dans l'ordre chronologique de sélection."""
        by_id = {s.id: s for s in self.selected_shapes()}
        ordered = [by_id[i] for i in self._selection_order if i in by_id]
        # Sécurité : formes sélectionnées hors suivi (rubber band massif).
        ordered += [s for s in by_id.values() if s not in ordered]
        return ordered

    def _on_selection_changed(self) -> None:
        selected_ids = {s.id for s in self.selected_shapes()}
        self._selection_order = [
            i for i in self._selection_order if i in selected_ids
        ]
        for shape_id in selected_ids:
            if shape_id not in self._selection_order:
                self._selection_order.append(shape_id)
        self.selection_changed.emit(self.selected_shapes())
