"""Test de régression : l'objet disparaissait après édition des propriétés.

Bug v0.1 : le combo « Type de découpe » stockait l'enum CutType (hérite de
str) comme userData Qt ; QVariant le convertissait en str pur. Après une
édition dans le panneau de propriétés, ``spec.cut_type`` devenait ``"pocket"``
au lieu de ``CutType.POCKET`` : ``paint()`` levait AttributeError sur
``.value`` → Qt cessait de dessiner l'item (objet invisible), et la
validation par ``is CutType.POCKET`` devenait silencieusement fausse.

Ce module rejoue le scénario complet (création → édition de toutes les
propriétés → rendu réel de la scène → sauvegarde/réouverture) pour chaque
type de forme.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip(
    "PySide6.QtWidgets", reason="PySide6 indisponible"
)

from PySide6.QtCore import QRectF  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402

from foamforge.core.geometry import (  # noqa: E402
    CircleShape,
    CutoutSpec,
    CutType,
    EllipseShape,
    RectShape,
    TextShape,
)
from foamforge.core.project import Project  # noqa: E402
from foamforge.core.validation import validate_project  # noqa: E402


@pytest.fixture(scope="module")
def app():
    application = QtWidgets.QApplication.instance()
    if application is None:
        try:
            application = QtWidgets.QApplication([])
        except Exception as exc:
            pytest.skip(f"QApplication indisponible : {exc}")
    return application


def _render_scene(canvas) -> QImage:
    """Rend réellement la scène : détecte les erreurs de paint() que les
    simples accès au modèle ne voient pas."""
    image = QImage(800, 600, QImage.Format.Format_RGB32)
    painter = QPainter(image)
    canvas.scene().render(
        painter, QRectF(0, 0, 800, 600), QRectF(-20, -20, 440, 340)
    )
    painter.end()
    return image


def _edit_all_properties(panel) -> None:
    """Simule l'édition utilisateur de chaque champ du panneau."""
    panel.name_edit.setText("Objet édité")
    panel.name_edit.editingFinished.emit()
    panel.x_spin.setValue(210.0)
    panel.y_spin.setValue(140.0)
    panel.rotation_spin.setValue(15.0)
    panel.depth_spin.setValue(35.0)
    panel.margin_spin.setValue(2.5)
    # Changement de type de découpe : c'était le déclencheur du bug
    # (currentData() revenait en str pur via QVariant).
    panel.cut_type_combo.setCurrentIndex(0)  # FULL
    panel.cut_type_combo.setCurrentIndex(1)  # POCKET


@pytest.mark.parametrize(
    "shape_factory",
    [
        lambda: RectShape(width_mm=100, height_mm=60, x_mm=150, y_mm=120,
                          spec=CutoutSpec(name="Rect")),
        lambda: CircleShape(diameter_mm=50, x_mm=150, y_mm=120,
                            spec=CutoutSpec(name="Cercle")),
        lambda: EllipseShape(width_mm=80, height_mm=40, x_mm=150, y_mm=120,
                             spec=CutoutSpec(name="Ellipse")),
        lambda: TextShape(text="LABEL", x_mm=150, y_mm=120,
                          spec=CutoutSpec(name="Texte")),
    ],
    ids=["rect", "circle", "ellipse", "text"],
)
def test_shape_survives_property_edits(app, shape_factory, tmp_path) -> None:
    from foamforge.app.main_window import MainWindow

    window = MainWindow()
    canvas = window.canvas
    panel = window.property_panel
    panel.set_expert_mode(True)

    shape = shape_factory()
    canvas.add_shape(shape)
    item = canvas.item_for(shape.id)
    item.setSelected(True)

    _edit_all_properties(panel)

    # 1. cut_type doit rester un enum CutType, jamais un str pur.
    assert isinstance(shape.spec.cut_type, CutType), (
        f"cut_type dégradé en {type(shape.spec.cut_type).__name__}"
    )

    # 2. L'item doit toujours exister, être visible, et avoir une emprise.
    item = canvas.item_for(shape.id)
    assert item is not None
    assert item.isVisible()
    assert item.boundingRect().width() > 0

    # 3. Le rendu réel de la scène ne doit lever aucune exception de paint.
    _render_scene(canvas)

    # 4. La validation doit voir la forme et rester cohérente.
    issues = validate_project(canvas.project)
    assert issues, "la validation doit toujours produire un résultat"

    # 5. Sauvegarde puis réouverture : la forme est toujours là.
    path = tmp_path / "regression.foamforge.json"
    canvas.project.save(path)
    reloaded = Project.load(path)
    restored = reloaded.get_shape(shape.id)
    assert restored is not None
    assert isinstance(restored.spec.cut_type, CutType)
    assert restored.cut_polygon().area > 0

    window._dirty = False
    window.close()


def test_depth_validation_still_works_after_panel_edit(app) -> None:
    """Le bug rendait la validation de profondeur silencieusement inactive
    (comparaison ``is CutType.POCKET`` avec un str)."""
    from foamforge.app.main_window import MainWindow

    window = MainWindow()
    canvas = window.canvas
    panel = window.property_panel

    shape = RectShape(width_mm=100, height_mm=60, x_mm=150, y_mm=120,
                      spec=CutoutSpec(name="Poche profonde"))
    canvas.add_shape(shape)
    canvas.item_for(shape.id).setSelected(True)

    # Édition via le panneau : poche plus profonde que la plaque (50 mm).
    panel.cut_type_combo.setCurrentIndex(1)  # POCKET — passe par QVariant
    panel.depth_spin.setValue(500.0)

    issues = validate_project(canvas.project)
    assert any(i.code == "depth_exceeds_thickness" for i in issues), (
        "la validation de profondeur doit voir la poche éditée via le panneau"
    )

    window._dirty = False
    window.close()


def test_position_synced_after_mouse_move(app) -> None:
    """Après un déplacement (souris/nesting), une édition dans le panneau ne
    doit pas réappliquer l'ancienne position mémorisée à la sélection."""
    from foamforge.app.main_window import MainWindow

    window = MainWindow()
    canvas = window.canvas
    panel = window.property_panel

    shape = RectShape(width_mm=80, height_mm=50, x_mm=100, y_mm=100,
                      spec=CutoutSpec(name="Mobile"))
    canvas.add_shape(shape)
    item = canvas.item_for(shape.id)
    item.setSelected(True)
    assert panel.x_spin.value() == 100.0

    # Déplacement équivalent à un drag souris.
    item.setPos(250.0, 180.0)
    window._on_model_changed()  # ce que ferait le signal model_changed
    assert panel.x_spin.value() == 250.0

    # Une édition de la profondeur ne doit PAS ramener la forme en (100, 100).
    panel.depth_spin.setValue(40.0)
    assert shape.x_mm == 250.0
    assert shape.y_mm == 180.0

    window._dirty = False
    window.close()
