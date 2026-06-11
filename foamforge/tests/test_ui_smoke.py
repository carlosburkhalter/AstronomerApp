"""Test de fumée de l'interface (rendu offscreen).

Vérifie que la fenêtre principale se construit, qu'on peut ajouter des
formes au canvas, que la validation alimente le panneau d'alertes et que
le panneau de propriétés reflète la sélection. Ignoré si Qt ne peut pas
s'initialiser dans l'environnement (bibliothèques système manquantes).
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip(
    "PySide6.QtWidgets", reason="PySide6 indisponible"
)


@pytest.fixture(scope="module")
def app():
    application = QtWidgets.QApplication.instance()
    if application is None:
        try:
            application = QtWidgets.QApplication([])
        except Exception as exc:  # environnement sans support graphique
            pytest.skip(f"QApplication indisponible : {exc}")
    return application


def test_main_window_smoke(app) -> None:
    from foamforge.app.main_window import MainWindow
    from foamforge.core.geometry import CutoutSpec, RectShape

    window = MainWindow()
    canvas = window.canvas
    assert canvas.project is not None

    # Ajout d'une forme via l'API du canvas (équivalent au dessin souris).
    shape = RectShape(
        width_mm=100, height_mm=60, x_mm=150, y_mm=120,
        spec=CutoutSpec(name="Caméra", depth_mm=30),
    )
    canvas.add_shape(shape)
    assert len(canvas.project.shapes) == 1
    assert len(canvas.shape_items()) == 1

    # La validation immédiate remplit le panneau d'alertes (au moins ✅).
    window.run_validation()
    assert window.alerts_panel.count() >= 1

    # La sélection alimente le panneau de propriétés.
    item = canvas.item_for(shape.id)
    assert item is not None
    item.setSelected(True)
    assert window.property_panel.name_edit.text() == "Caméra"

    # Duplication puis suppression via le canvas.
    canvas.duplicate_selection()
    assert len(canvas.project.shapes) == 2
    canvas.scene().clearSelection()
    canvas.item_for(shape.id).setSelected(True)
    canvas.delete_selection()
    assert len(canvas.project.shapes) == 1

    # Marque le projet comme enregistré : sinon closeEvent ouvre une
    # boîte modale « Enregistrer ? » qui bloquerait le test offscreen.
    window._dirty = False
    window.close()
