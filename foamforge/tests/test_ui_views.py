"""Tests UI : 3D interactive, vue éclatée, aides de placement.

Rendu offscreen. Couvre : initialisation sans crash, rotation/zoom,
sélection par clic 3D synchronisée avec la 2D, effeuillage des couches,
vue éclatée (rendu, visibilité, capture PNG), snap intelligent du canvas
et non-contamination des exports par les aides visuelles.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip(
    "PySide6.QtWidgets", reason="PySide6 indisponible"
)

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402

from foamforge.core.geometry import CutoutSpec, CutType, RectShape  # noqa: E402
from foamforge.core.layers import FoamLayer, LayerRole  # noqa: E402
from foamforge.core.project import FoamSheet, Project  # noqa: E402


@pytest.fixture(scope="module")
def app():
    application = QtWidgets.QApplication.instance()
    if application is None:
        try:
            application = QtWidgets.QApplication([])
        except Exception as exc:
            pytest.skip(f"QApplication indisponible : {exc}")
    return application


def _layered_project() -> Project:
    project = Project(
        name="Test 3D",
        case_depth_mm=110.0,
        sheet=FoamSheet(width_mm=400, height_mm=300, thickness_mm=90),
        foam_layers=[
            FoamLayer(20.0, LayerRole.BOTTOM),
            FoamLayer(30.0, LayerRole.CUTOUT),
            FoamLayer(30.0, LayerRole.CUTOUT),
            FoamLayer(30.0, LayerRole.CUTOUT),
        ],
    )
    project.add_shape(RectShape(
        width_mm=100, height_mm=80, x_mm=120, y_mm=120,
        spec=CutoutSpec(name="Poche 20", depth_mm=20, object_height_mm=40),
    ))
    project.add_shape(RectShape(
        width_mm=80, height_mm=60, x_mm=290, y_mm=180,
        spec=CutoutSpec(name="Poche 80", depth_mm=80),
    ))
    return project


def _render(widget) -> QImage:
    image = QImage(widget.size(), QImage.Format.Format_RGB32)
    widget.render(image)
    return image


# ---------------------------------------------------------------------- #
# Vue 3D interactive
# ---------------------------------------------------------------------- #
def test_view3d_initializes_and_renders(app) -> None:
    from foamforge.ui.view3d import FoamView3D

    view = FoamView3D()
    view.set_project(_layered_project())
    view.resize(800, 600)
    _render(view)  # ne doit pas lever


def test_view3d_camera_controls(app) -> None:
    from foamforge.ui.view3d import FoamView3D

    view = FoamView3D()
    view.set_project(_layered_project())
    view.resize(800, 600)
    az, el, zoom = view._azimuth_deg, view._elevation_deg, view._zoom

    # Simulation d'un drag gauche : rotation.
    class _Event:
        def __init__(self, pos, button=Qt.MouseButton.LeftButton, delta=0):
            self._pos, self._button, self._delta = pos, button, delta
        def position(self): return self._pos
        def button(self): return self._button
        def angleDelta(self):
            class _D:
                def __init__(self, y): self._y = y
                def y(self): return self._y
            return _D(self._delta)

    view.mousePressEvent(_Event(QPointF(100, 100)))
    view.mouseMoveEvent(_Event(QPointF(140, 120)))
    view.mouseReleaseEvent(_Event(QPointF(140, 120)))
    assert view._azimuth_deg != az
    assert view._elevation_deg != el

    view.wheelEvent(_Event(QPointF(0, 0), delta=120))
    assert view._zoom > zoom

    # L'élévation reste bornée (pas de retournement sous la mousse).
    for _ in range(50):
        view.mousePressEvent(_Event(QPointF(0, 0)))
        view.mouseMoveEvent(_Event(QPointF(0, 400)))
        view.mouseReleaseEvent(_Event(QPointF(0, 400)))
    assert 10.0 <= view._elevation_deg <= 89.0
    _render(view)


def test_view3d_click_selects_shape(app) -> None:
    """Cliquer un logement en 3D émet l'id de l'objet correspondant."""
    from foamforge.ui.view3d import FoamView3D

    project = _layered_project()
    view = FoamView3D()
    view.set_project(project)
    view.resize(800, 600)
    _render(view)  # construit la géométrie + zones de picking

    received: list[str] = []
    view.shape_clicked.connect(received.append)

    # Position écran du centre du premier logement (via la projection).
    shape = project.shapes[0]
    top_z = sum(l.thickness_mm for l in project.foam_layers)
    point, _ = view._project_point(shape.x_mm, shape.y_mm, top_z)
    scale, offset = view._view_transform()
    screen = point * scale + offset
    view._pick(screen)
    assert received == [shape.id]


def test_view3d_selection_sync_and_layers_crossed(app) -> None:
    from foamforge.ui.view3d import FoamView3D

    project = _layered_project()
    view = FoamView3D()
    view.set_project(project)
    deep = project.shapes[1]  # poche de 80 mm
    view.set_selected_ids([deep.id])
    assert deep.id in view._selected_ids
    # 80 mm sur des couches de 30 (du haut) : traverse 4 et 3, entame 2.
    assert view._layers_crossed(deep) == "2, 3, 4"
    view.resize(800, 600)
    _render(view)  # rendu avec sélection : pas de crash


def test_view3d_layer_peeling(app) -> None:
    """L'effeuillage réduit la pile visible et re-référence les poches."""
    from foamforge.ui.view3d import FoamView3D

    view = FoamView3D()
    view.set_project(_layered_project())
    assert len(view._stack()) == 4
    view.set_visible_layer_count(2)  # fond + 1 couche découpée
    assert len(view._stack()) == 2
    assert view._hidden_top_mm() == pytest.approx(60)  # 2 × 30 masqués
    view.resize(800, 600)
    _render(view)


def test_view3d_mono_plate_fallback(app) -> None:
    """Sans empilement : la 3D montre la plaque unique sans crash."""
    from foamforge.ui.view3d import FoamView3D

    project = Project()
    project.add_shape(RectShape(width_mm=80, height_mm=60,
                                x_mm=150, y_mm=120,
                                spec=CutoutSpec(depth_mm=30)))
    view = FoamView3D()
    view.set_project(project)
    view.resize(640, 480)
    _render(view)


# ---------------------------------------------------------------------- #
# Vue éclatée
# ---------------------------------------------------------------------- #
def test_exploded_view_renders_and_hides_layers(app, tmp_path) -> None:
    from foamforge.ui.exploded_view import ExplodedView

    project = _layered_project()
    view = ExplodedView()
    view.set_project(project)
    view.resize(900, 700)
    _render(view)

    # Une case à cocher par couche, masquage répercuté au diagramme.
    assert len(view._checkboxes) == 4
    view._checkboxes[0].setChecked(False)  # masque la couche du haut
    hidden_index = view._checkboxes[0].property("ff_layer_index")
    assert hidden_index in view.diagram._hidden
    _render(view)

    # Capture PNG.
    out = view.diagram.export_png(tmp_path / "eclate.png")
    assert out.stat().st_size > 1000


def test_exploded_layer_selection(app) -> None:
    from foamforge.ui.exploded_view import ExplodedDiagram

    diagram = ExplodedDiagram()
    diagram.set_project(_layered_project())
    diagram.resize(900, 700)
    _render(diagram)  # construit les zones cliquables
    assert diagram._hit_zones
    polygon, index = diagram._hit_zones[-1]
    received = []
    diagram.layer_clicked.connect(received.append)

    class _Event:
        def __init__(self, pos): self._pos = pos
        def position(self): return self._pos

    diagram.mousePressEvent(_Event(polygon.boundingRect().center()))
    assert received and received[0] == index
    assert diagram._selected == index


# ---------------------------------------------------------------------- #
# Aides de placement (canvas 2D)
# ---------------------------------------------------------------------- #
def test_snap_to_plate_center_and_other_shapes(app) -> None:
    from foamforge.ui.canvas import FoamCanvas

    canvas = FoamCanvas()
    project = Project(sheet=FoamSheet(width_mm=400, height_mm=300,
                                      thickness_mm=50))
    canvas.set_project(project)
    fixed = RectShape(width_mm=60, height_mm=40, x_mm=100, y_mm=80,
                      spec=CutoutSpec(name="Fixe"))
    moving = RectShape(width_mm=40, height_mm=40, x_mm=300, y_mm=200,
                       spec=CutoutSpec(name="Mobile"))
    canvas.add_shape(fixed, select=False)
    canvas.add_shape(moving, select=False)
    item = canvas.item_for(moving.id)

    # Près du centre de la plaque (200, 150) : accroche exacte + guides.
    snapped = canvas.snap_with_aids(item, QPointF(198.5, 151.2))
    assert snapped.x() == pytest.approx(200)
    assert snapped.y() == pytest.approx(150)
    assert ("v", 200.0) in canvas._guides
    assert ("h", 150.0) in canvas._guides

    # Près du centre X d'une autre forme : alignement de centres.
    snapped = canvas.snap_with_aids(item, QPointF(101.4, 220.0))
    assert snapped.x() == pytest.approx(100)

    # Aides désactivées : aucun accrochage, aucun guide.
    canvas.set_aids_enabled(False)
    snapped = canvas.snap_with_aids(item, QPointF(198.5, 151.2))
    assert snapped.x() == pytest.approx(198.5)
    assert canvas._guides == []


def test_aids_do_not_affect_exports(app, tmp_path) -> None:
    """Les aides sont purement visuelles : exports identiques on/off."""
    from foamforge.export.svg_exporter import export_svg
    from foamforge.ui.canvas import FoamCanvas

    canvas = FoamCanvas()
    project = Project(sheet=FoamSheet(width_mm=400, height_mm=300,
                                      thickness_mm=50))
    canvas.set_project(project)
    canvas.add_shape(RectShape(width_mm=80, height_mm=60, x_mm=150,
                               y_mm=120), select=False)

    canvas.set_aids_enabled(True)
    with_aids = export_svg(project, tmp_path / "on.svg").read_bytes()
    canvas.set_aids_enabled(False)
    without_aids = export_svg(project, tmp_path / "off.svg").read_bytes()
    assert with_aids == without_aids
    # Et aucun élément de guide dans le SVG.
    assert b"guide" not in with_aids.lower()
