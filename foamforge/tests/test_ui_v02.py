"""Tests UI des nouveautés v0.2 (rendu offscreen).

Couvre : dialogue de paramètres du projet (dimensions intérieures,
modification après création), panneau de couches (calcul + application),
bascule vue 2D/3D avec rendu réel, et opérations booléennes via la
fenêtre principale.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip(
    "PySide6.QtWidgets", reason="PySide6 indisponible"
)

from PySide6.QtGui import QImage, QPainter  # noqa: E402

from foamforge.core.geometry import CutoutSpec, RectShape  # noqa: E402
from foamforge.core.layers import LayerRole  # noqa: E402
from foamforge.core.project import Project  # noqa: E402


@pytest.fixture(scope="module")
def app():
    application = QtWidgets.QApplication.instance()
    if application is None:
        try:
            application = QtWidgets.QApplication([])
        except Exception as exc:
            pytest.skip(f"QApplication indisponible : {exc}")
    return application


def _window():
    from foamforge.app.main_window import MainWindow

    return MainWindow()


# ---------------------------------------------------------------------- #
# Dialogue paramètres / dimensions intérieures
# ---------------------------------------------------------------------- #
def test_settings_dialog_builds_project(app) -> None:
    from foamforge.ui.dialogs import ProjectSettingsDialog

    dialog = ProjectSettingsDialog()
    dialog.name_edit.setText("Valise test")
    dialog.case_name_edit.setText("Nanuk 935")
    dialog.case_width.setValue(450)
    dialog.case_height.setValue(330)
    dialog.case_depth.setValue(120)
    dialog.thicknesses_edit.setText("10, 20, 40")
    dialog.min_floor.setValue(15)
    project = dialog.build_project()
    assert project.case_name == "Nanuk 935"
    assert project.case_width_mm == 450
    assert project.case_depth_mm == 120
    # Le canvas représente l'intérieur utile de la valise.
    assert project.sheet.width_mm == 450
    assert project.sheet.height_mm == 330
    assert project.available_foam_thicknesses_mm == [10.0, 20.0, 40.0]
    assert project.min_bottom_floor_mm == 15


def test_settings_dialog_edits_existing_project(app) -> None:
    from foamforge.ui.dialogs import ProjectSettingsDialog

    project = Project(name="Avant", case_depth_mm=160.0)
    dialog = ProjectSettingsDialog(project=project)
    # Pré-rempli depuis le projet.
    assert dialog.name_edit.text() == "Avant"
    assert dialog.case_depth.value() == 160.0
    # Modification puis application.
    dialog.case_depth.setValue(140)
    dialog.apply_to(project)
    assert project.case_depth_mm == 140


def test_thickness_parsing(app) -> None:
    from foamforge.ui.dialogs import _parse_thicknesses

    assert _parse_thicknesses("10, 20, 30") == [10.0, 20.0, 30.0]
    assert _parse_thicknesses("40 ; 20 ; n'importe quoi ; 20") == [20.0, 40.0]
    assert _parse_thicknesses("") == []


# ---------------------------------------------------------------------- #
# Panneau de couches
# ---------------------------------------------------------------------- #
def test_layers_panel_computes_and_applies(app) -> None:
    window = _window()
    project = Project(
        case_depth_mm=120.0,
        available_foam_thicknesses_mm=[10.0, 20.0, 30.0, 40.0],
        min_bottom_floor_mm=10.0,
    )
    project.add_shape(RectShape(
        width_mm=100, height_mm=80, x_mm=200, y_mm=150,
        spec=CutoutSpec(depth_mm=60, object_height_mm=78),
    ))
    window.set_project(project)

    window.layers_panel.compute()
    assert project.foam_layers, "l'empilement doit être appliqué au projet"
    assert sum(l.thickness_mm for l in project.foam_layers) == pytest.approx(120)
    assert project.cuttable_depth_mm() >= 78
    # La plaque de travail suit la profondeur découpable.
    assert project.sheet.thickness_mm == pytest.approx(
        project.cuttable_depth_mm()
    )
    # La liste affiche toutes les couches.
    assert window.layers_panel._list.count() == len(project.foam_layers)

    window._dirty = False
    window.close()


def test_layers_panel_reports_impossible(app) -> None:
    window = _window()
    project = Project(
        case_depth_mm=70.0,
        available_foam_thicknesses_mm=[30.0],  # 70 impossible avec 30
    )
    window.set_project(project)
    window.layers_panel.compute()
    assert not project.foam_layers
    assert "⛔" in window.layers_panel._messages.text()
    window._dirty = False
    window.close()


# ---------------------------------------------------------------------- #
# Vue 3D
# ---------------------------------------------------------------------- #
def test_3d_view_toggle_and_render(app) -> None:
    window = _window()
    project = Project(case_depth_mm=120.0)
    project.add_shape(RectShape(
        width_mm=100, height_mm=60, x_mm=150, y_mm=120,
        spec=CutoutSpec(name="Poche", depth_mm=40),
    ))
    window.set_project(project)
    window.layers_panel.compute()

    # Bascule 2D → 3D (la page 3D embarque le visualiseur + contrôles).
    window._view3d_action.setChecked(True)
    assert window._center_stack.currentWidget() is window._page3d

    # Rendu réel du widget 3D : ne doit lever aucune exception.
    window.view3d.resize(800, 600)
    image = QImage(800, 600, QImage.Format.Format_RGB32)
    window.view3d.render(image)

    # Retour 2D.
    window._view2d_action.setChecked(True)
    assert window._center_stack.currentWidget() is window.canvas

    window._dirty = False
    window.close()


# ---------------------------------------------------------------------- #
# Booléens via la fenêtre (sans boîte modale : on appelle le cœur)
# ---------------------------------------------------------------------- #
def test_selection_order_tracking(app) -> None:
    window = _window()
    canvas = window.canvas
    a = RectShape(width_mm=60, height_mm=40, x_mm=100, y_mm=100,
                  spec=CutoutSpec(name="A"))
    b = RectShape(width_mm=60, height_mm=40, x_mm=130, y_mm=120,
                  spec=CutoutSpec(name="B"))
    canvas.add_shape(a, select=False)
    canvas.add_shape(b, select=False)
    canvas.scene().clearSelection()
    # Sélection B d'abord, puis A : l'ordre chronologique doit être B, A.
    canvas.item_for(b.id).setSelected(True)
    canvas.item_for(a.id).setSelected(True)
    ordered = canvas.selected_shapes_ordered()
    assert [s.spec.name for s in ordered] == ["B", "A"]
    window._dirty = False
    window.close()
