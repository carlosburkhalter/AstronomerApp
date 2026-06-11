"""Tests du calcul de couches OBJET PAR OBJET (sans couvercle).

Reprend l'exemple du cahier des charges :

Couches : 20 mm fond + 3 × 30 mm découpées (du fond vers le haut).
- oculaire : poche 25 mm → découpe la couche supérieure uniquement ;
- caméra  : poche 55 mm → traverse la couche sup. + 25 mm dans la 2e ;
- monture : poche 85 mm → traverse 2 couches + 25 mm dans la 3e.
"""

from __future__ import annotations

import pytest

from foamforge.core.geometry import CircleShape, CutoutSpec, CutType, RectShape, TextShape
from foamforge.core.layers import (
    FoamLayer,
    LayerRole,
    compute_layer_assignments,
    plan_layers,
)
from foamforge.core.project import FoamSheet, Project


def _spec_project() -> Project:
    project = Project(
        case_depth_mm=110.0,
        sheet=FoamSheet(width_mm=500, height_mm=300, thickness_mm=90),
        foam_layers=[
            FoamLayer(20.0, LayerRole.BOTTOM),    # couche 1 (fond)
            FoamLayer(30.0, LayerRole.CUTOUT),    # couche 2
            FoamLayer(30.0, LayerRole.CUTOUT),    # couche 3
            FoamLayer(30.0, LayerRole.CUTOUT),    # couche 4 (surface)
        ],
    )
    project.add_shape(CircleShape(
        diameter_mm=45, x_mm=80, y_mm=80,
        spec=CutoutSpec(name="Oculaire", depth_mm=25),
    ))
    project.add_shape(RectShape(
        width_mm=90, height_mm=90, x_mm=220, y_mm=120,
        spec=CutoutSpec(name="Caméra", depth_mm=55),
    ))
    project.add_shape(RectShape(
        width_mm=120, height_mm=80, x_mm=390, y_mm=150,
        spec=CutoutSpec(name="Monture", depth_mm=85),
    ))
    return project


def _cuts_of(assignments, layer_index: int, name_by_id: dict) -> dict:
    """{nom: (through, profondeur)} pour une couche donnée."""
    assignment = next(a for a in assignments if a.index == layer_index)
    return {
        name_by_id[c.shape_id]: (c.through, c.depth_in_layer_mm)
        for c in assignment.cuts
    }


def test_spec_example_per_object() -> None:
    project = _spec_project()
    assignments = project.layer_assignments()
    names = {s.id: s.spec.name for s in project.shapes}

    # Couche 1 (fond) : jamais découpée.
    assert _cuts_of(assignments, 1, names) == {}

    # Couche 4 (surface) : les trois objets la découpent.
    top = _cuts_of(assignments, 4, names)
    assert top["Oculaire"] == (False, pytest.approx(25))
    assert top["Caméra"] == (True, pytest.approx(30))
    assert top["Monture"] == (True, pytest.approx(30))

    # Couche 3 : l'oculaire est absent ; caméra 25 mm ; monture traverse.
    middle = _cuts_of(assignments, 3, names)
    assert "Oculaire" not in middle
    assert middle["Caméra"] == (False, pytest.approx(25))
    assert middle["Monture"] == (True, pytest.approx(30))

    # Couche 2 : seule la monture descend encore (25 mm).
    low = _cuts_of(assignments, 2, names)
    assert set(low) == {"Monture"}
    assert low["Monture"] == (False, pytest.approx(25))


def test_full_cut_crosses_all_cutout_layers() -> None:
    project = _spec_project()
    project.add_shape(RectShape(
        width_mm=40, height_mm=40, x_mm=450, y_mm=60,
        spec=CutoutSpec(name="Passage", cut_type=CutType.FULL),
    ))
    assignments = project.layer_assignments()
    names = {s.id: s.spec.name for s in project.shapes}
    for index in (2, 3, 4):
        cuts = _cuts_of(assignments, index, names)
        assert cuts["Passage"][0] is True
    assert "Passage" not in _cuts_of(assignments, 1, names)


def test_text_only_marks_top_layer_surface() -> None:
    project = _spec_project()
    project.add_shape(TextShape(
        text="ASTRO", x_mm=250, y_mm=260, spec=CutoutSpec(name="Texte"),
    ))
    assignments = project.layer_assignments()
    surface_cuts = [
        c for a in assignments for c in a.cuts if c.is_surface
    ]
    assert len(surface_cuts) == 1
    top_index = max(
        a.index for a in assignments
        if a.layer.role is LayerRole.CUTOUT
    )
    assert any(
        c.is_surface for a in assignments if a.index == top_index
        for c in a.cuts
    )


def test_layer_altitudes() -> None:
    project = _spec_project()
    assignments = project.layer_assignments()
    assert [a.z_bottom_mm for a in assignments] == [0.0, 20.0, 50.0, 80.0]
    assert assignments[-1].z_top_mm == pytest.approx(110.0)


def test_planner_never_produces_lid() -> None:
    """Le couvercle de la valise n'apparaît jamais dans le plan."""
    for depth, thicknesses in [
        (120, [10, 20, 30, 40]),
        (100, [20, 50]),
        (90, [10, 30]),
    ]:
        plan = plan_layers(
            case_depth_mm=depth,
            available_foam_thicknesses_mm=thicknesses,
            max_pocket_depth_mm=depth / 2,
            min_bottom_floor_mm=10,
        )
        assert plan.feasible
        roles = {layer.role for layer in plan.layers}
        assert "lid" not in {r.value for r in roles}
        # La couche supérieure est toujours découpée.
        assert plan.layers[-1].role is LayerRole.CUTOUT


def test_legacy_lid_layer_becomes_spacer() -> None:
    layer = FoamLayer.from_dict({"thickness_mm": 20.0, "role": "lid"})
    assert layer.role is LayerRole.SPACER


def test_cut_strategy_derivation() -> None:
    assert CutoutSpec(cut_type=CutType.FULL).cut_strategy() == "through"
    assert CutoutSpec(depth_mm=35, object_height_mm=80).cut_strategy() \
        == "partial_support"
    assert CutoutSpec(depth_mm=30, object_height_mm=30).cut_strategy() \
        == "pocket"
    assert CutoutSpec(depth_mm=30).cut_strategy() == "pocket"


def test_mono_plate_has_no_assignments_without_plan() -> None:
    project = Project()
    project.add_shape(RectShape(width_mm=50, height_mm=50,
                                x_mm=100, y_mm=100))
    assert project.layer_assignments() == []
