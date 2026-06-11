"""Panneau de propriétés : édition de la forme sélectionnée.

Affiche et modifie la géométrie (position, dimensions, rotation) et les
paramètres de découpe (profondeur, marge, arrondi, type, ordre, poids,
commentaire). En mode débutant, seuls les réglages essentiels sont
visibles ; le mode expert révèle tout.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from foamforge.core.geometry import (
    CircleShape,
    CutType,
    EllipseShape,
    RectShape,
    Shape,
    TextShape,
)


def _mm_spin(minimum: float, maximum: float, step: float = 1.0) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setSingleStep(step)
    spin.setDecimals(1)
    spin.setSuffix(" mm")
    return spin


class PropertyPanel(QWidget):
    """Formulaire de propriétés de la forme sélectionnée."""

    shape_edited = Signal(object)  # Shape modifiée → rafraîchir le canvas

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._shape: Shape | None = None
        self._updating = False
        self._expert = False
        # Lignes (label, widget) réservées au mode expert.
        self._expert_rows: list[tuple[QWidget, QWidget]] = []

        layout = QVBoxLayout(self)
        self._title = QLabel("Aucune sélection")
        self._title.setStyleSheet("font-weight: bold;")
        layout.addWidget(self._title)

        self._form = QFormLayout()
        layout.addLayout(self._form)
        layout.addStretch()

        # --- Identité -------------------------------------------------- #
        self.name_edit = QLineEdit()
        self._add_row("Nom de l'objet", self.name_edit)

        # --- Géométrie -------------------------------------------------- #
        self.x_spin = _mm_spin(-5000, 5000)
        self._add_row("Position X", self.x_spin)
        self.y_spin = _mm_spin(-5000, 5000)
        self._add_row("Position Y", self.y_spin)
        self.width_spin = _mm_spin(1, 3000)
        self._add_row("Largeur", self.width_spin)
        self.height_spin = _mm_spin(1, 3000)
        self._add_row("Hauteur", self.height_spin)
        self.diameter_spin = _mm_spin(1, 3000)
        self._add_row("Diamètre", self.diameter_spin)
        self.rotation_spin = QDoubleSpinBox()
        self.rotation_spin.setRange(-360, 360)
        self.rotation_spin.setSuffix(" °")
        self._add_row("Rotation", self.rotation_spin, expert=True)

        # --- Texte gravé ------------------------------------------------ #
        self.text_edit = QLineEdit()
        self._add_row("Texte", self.text_edit)
        self.font_height_spin = _mm_spin(2, 100)
        self._add_row("Hauteur du texte", self.font_height_spin)

        # --- Paramètres de découpe -------------------------------------- #
        self.cut_type_combo = QComboBox()
        for cut_type in CutType:
            self.cut_type_combo.addItem(cut_type.label, cut_type)
        self._add_row("Type de découpe", self.cut_type_combo)
        self.depth_spin = _mm_spin(0, 500)
        self._add_row("Profondeur", self.depth_spin)
        self.margin_spin = _mm_spin(0, 50, 0.5)
        self.margin_spin.setToolTip(
            "Marge de tolérance ajoutée autour de l'objet (ex. +1, +2, +3 mm)"
        )
        self._add_row("Marge de tolérance", self.margin_spin)
        self.radius_spin = _mm_spin(0, 100, 0.5)
        self._add_row("Rayon d'arrondi", self.radius_spin, expert=True)
        self.order_spin = QSpinBox()
        self.order_spin.setRange(1, 999)
        self._add_row("Ordre de découpe", self.order_spin, expert=True)
        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0, 100000)
        self.weight_spin.setSuffix(" g")
        self.weight_spin.setToolTip(
            "Poids de l'objet : permet le contrôle de répartition du poids"
        )
        self._add_row("Poids", self.weight_spin, expert=True)
        self.comment_edit = QLineEdit()
        self._add_row("Commentaire", self.comment_edit, expert=True)

        self._connect_signals()
        self.set_shape(None)

    # ------------------------------------------------------------------ #
    def _add_row(
        self, label: str, widget: QWidget, expert: bool = False
    ) -> None:
        label_widget = QLabel(label)
        self._form.addRow(label_widget, widget)
        widget.setProperty("ff_label", label_widget)
        if expert:
            self._expert_rows.append((label_widget, widget))

    def _connect_signals(self) -> None:
        self.name_edit.editingFinished.connect(self._apply)
        self.text_edit.editingFinished.connect(self._apply)
        self.comment_edit.editingFinished.connect(self._apply)
        for spin in (
            self.x_spin, self.y_spin, self.width_spin, self.height_spin,
            self.diameter_spin, self.rotation_spin, self.font_height_spin,
            self.depth_spin, self.margin_spin, self.radius_spin,
            self.weight_spin,
        ):
            spin.valueChanged.connect(self._apply)
        self.order_spin.valueChanged.connect(self._apply)
        self.cut_type_combo.currentIndexChanged.connect(self._apply)

    # ------------------------------------------------------------------ #
    # Modes débutant / expert
    # ------------------------------------------------------------------ #
    def set_expert_mode(self, expert: bool) -> None:
        self._expert = expert
        self._refresh_visibility()

    # ------------------------------------------------------------------ #
    # Sélection
    # ------------------------------------------------------------------ #
    def set_shape(self, shape: Shape | None) -> None:
        """Charge la forme sélectionnée dans le formulaire (ou rien)."""
        self._shape = shape
        self._updating = True
        try:
            if shape is None:
                self._title.setText("Aucune sélection")
            else:
                self._title.setText(shape.spec.name)
                self.name_edit.setText(shape.spec.name)
                self.x_spin.setValue(shape.x_mm)
                self.y_spin.setValue(shape.y_mm)
                self.rotation_spin.setValue(shape.rotation_deg)
                if isinstance(shape, (RectShape, EllipseShape)):
                    self.width_spin.setValue(shape.width_mm)
                    self.height_spin.setValue(shape.height_mm)
                if isinstance(shape, CircleShape):
                    self.diameter_spin.setValue(shape.diameter_mm)
                if isinstance(shape, TextShape):
                    self.text_edit.setText(shape.text)
                    self.font_height_spin.setValue(shape.font_height_mm)
                spec = shape.spec
                index = self.cut_type_combo.findData(spec.cut_type)
                self.cut_type_combo.setCurrentIndex(max(index, 0))
                self.depth_spin.setValue(spec.depth_mm)
                self.margin_spin.setValue(spec.margin_mm)
                self.radius_spin.setValue(spec.corner_radius_mm)
                self.order_spin.setValue(max(spec.cut_order, 1))
                self.weight_spin.setValue(spec.weight_g)
                self.comment_edit.setText(spec.comment)
            self._refresh_visibility()
        finally:
            self._updating = False

    def _refresh_visibility(self) -> None:
        """Montre uniquement les champs pertinents pour la forme + le mode."""
        shape = self._shape
        has_shape = shape is not None
        is_rect_like = isinstance(shape, (RectShape, EllipseShape))
        is_circle = isinstance(shape, CircleShape)
        is_text = isinstance(shape, TextShape)

        visibility: dict[QWidget, bool] = {
            self.name_edit: has_shape,
            self.x_spin: has_shape,
            self.y_spin: has_shape,
            self.width_spin: is_rect_like,
            self.height_spin: is_rect_like,
            self.diameter_spin: is_circle,
            self.rotation_spin: has_shape,
            self.text_edit: is_text,
            self.font_height_spin: is_text,
            self.cut_type_combo: has_shape and not is_text,
            self.depth_spin: has_shape,
            self.margin_spin: has_shape and not is_text,
            self.radius_spin: has_shape and not is_text,
            self.order_spin: has_shape,
            self.weight_spin: has_shape and not is_text,
            self.comment_edit: has_shape,
        }
        expert_widgets = {widget for _, widget in self._expert_rows}
        for widget, visible in visibility.items():
            if widget in expert_widgets and not self._expert:
                visible = False
            widget.setVisible(visible)
            label = widget.property("ff_label")
            if label is not None:
                label.setVisible(visible)

    # ------------------------------------------------------------------ #
    # Application des modifications au modèle
    # ------------------------------------------------------------------ #
    def _apply(self) -> None:
        if self._updating or self._shape is None:
            return
        shape = self._shape
        shape.spec.name = self.name_edit.text() or shape.spec.name
        shape.x_mm = self.x_spin.value()
        shape.y_mm = self.y_spin.value()
        shape.rotation_deg = self.rotation_spin.value()
        if isinstance(shape, (RectShape, EllipseShape)):
            shape.width_mm = self.width_spin.value()
            shape.height_mm = self.height_spin.value()
        if isinstance(shape, CircleShape):
            shape.diameter_mm = self.diameter_spin.value()
        if isinstance(shape, TextShape):
            if self.text_edit.text().strip():
                shape.text = self.text_edit.text().strip()
            shape.font_height_mm = self.font_height_spin.value()
        spec = shape.spec
        if not isinstance(shape, TextShape):
            spec.cut_type = self.cut_type_combo.currentData()
            spec.margin_mm = self.margin_spin.value()
            spec.corner_radius_mm = self.radius_spin.value()
            spec.weight_g = self.weight_spin.value()
        spec.depth_mm = self.depth_spin.value()
        spec.cut_order = self.order_spin.value()
        spec.comment = self.comment_edit.text()
        self._title.setText(spec.name)
        self.shape_edited.emit(shape)
