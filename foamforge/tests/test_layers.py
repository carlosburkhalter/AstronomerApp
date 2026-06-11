"""Tests du FoamLayerPlanner (calcul d'empilement de couches)."""

from __future__ import annotations

import pytest

from foamforge.core.layers import (
    FoamLayer,
    LayerPlan,
    LayerRole,
    plan_layers,
    pocket_cuts_per_layer,
)


def test_spec_example_120mm() -> None:
    """Exemple du cahier des charges : valise 120 mm, objet 78 mm,
    fond 10 mm, mousses 10/20/30/40 mm."""
    plan = plan_layers(
        case_depth_mm=120,
        available_foam_thicknesses_mm=[10, 20, 30, 40],
        max_object_height_mm=78,
        max_pocket_depth_mm=78,
        min_bottom_floor_mm=10,
    )
    assert plan.feasible
    # Le total doit remplir EXACTEMENT la profondeur intérieure.
    assert plan.total_mm == pytest.approx(120)
    # La profondeur découpable couvre l'objet le plus haut.
    assert plan.cuttable_mm() >= 78
    # Une couche de fond intacte d'au moins 10 mm.
    bottom = [l for l in plan.layers if l.role is LayerRole.BOTTOM]
    assert bottom and sum(l.thickness_mm for l in bottom) >= 10
    # Rôles cohérents : fond en premier, couvercle en dernier si présent.
    roles = [l.role for l in plan.layers]
    assert roles[0] is LayerRole.BOTTOM
    if LayerRole.LID in roles:
        assert roles[-1] is LayerRole.LID


def test_exact_fill_simple() -> None:
    plan = plan_layers(
        case_depth_mm=100,
        available_foam_thicknesses_mm=[20, 50],
        max_pocket_depth_mm=45,
        min_bottom_floor_mm=10,
    )
    assert plan.feasible
    assert plan.total_mm == pytest.approx(100)
    assert plan.cuttable_mm() >= 45


def test_impossible_combination_reports_error() -> None:
    """70 mm n'est pas atteignable avec des plaques de 30 mm uniquement."""
    plan = plan_layers(
        case_depth_mm=70,
        available_foam_thicknesses_mm=[30],
        min_bottom_floor_mm=0,
    )
    assert not plan.feasible
    assert any("Aucune combinaison" in e for e in plan.errors)


def test_object_taller_than_case_is_error() -> None:
    plan = plan_layers(
        case_depth_mm=100,
        available_foam_thicknesses_mm=[10, 20, 50],
        max_object_height_mm=120,
    )
    assert not plan.feasible
    assert any("Objet trop haut" in e for e in plan.errors)


def test_insufficient_floor_is_error() -> None:
    """Poche de 95 mm + fond de 10 mm > 100 mm de valise."""
    plan = plan_layers(
        case_depth_mm=100,
        available_foam_thicknesses_mm=[10, 20, 50],
        max_pocket_depth_mm=95,
        min_bottom_floor_mm=10,
    )
    assert not plan.feasible
    assert any("fond minimal" in e.lower() for e in plan.errors)


def test_shallow_pocket_warning() -> None:
    """Poche < 50 % de la hauteur de l'objet → avertissement de maintien."""
    plan = plan_layers(
        case_depth_mm=120,
        available_foam_thicknesses_mm=[10, 20, 30, 40],
        max_object_height_mm=80,
        max_pocket_depth_mm=30,
        min_bottom_floor_mm=10,
    )
    assert plan.feasible
    assert any("maintien partiel" in w for w in plan.warnings)


def test_preferred_layer_count() -> None:
    plan = plan_layers(
        case_depth_mm=100,
        available_foam_thicknesses_mm=[10, 20, 30, 40, 50],
        max_pocket_depth_mm=40,
        min_bottom_floor_mm=10,
        preferred_layer_count=3,
    )
    assert plan.feasible
    assert len(plan.layers) == 3
    assert plan.total_mm == pytest.approx(100)


def test_preferred_count_falls_back_when_impossible() -> None:
    """Si aucun empilement à N couches n'existe, le planificateur doit
    quand même proposer la meilleure alternative."""
    plan = plan_layers(
        case_depth_mm=100,
        available_foam_thicknesses_mm=[10, 20, 50],  # pas de combo à 3
        max_pocket_depth_mm=40,
        min_bottom_floor_mm=10,
        preferred_layer_count=3,
    )
    assert plan.feasible
    assert plan.total_mm == pytest.approx(100)


def test_no_thickness_available() -> None:
    plan = plan_layers(case_depth_mm=100, available_foam_thicknesses_mm=[])
    assert not plan.feasible


def test_pocket_cuts_per_layer_spans_two_layers() -> None:
    """Poche de 30 mm sur deux couches CUTOUT de 20 mm : traversante
    dans la première, 10 mm dans la seconde."""
    plan = LayerPlan(layers=[
        FoamLayer(20, LayerRole.BOTTOM),
        FoamLayer(20, LayerRole.CUTOUT),
        FoamLayer(20, LayerRole.CUTOUT),
    ])
    cuts = pocket_cuts_per_layer(plan, pocket_depth_mm=30)
    assert len(cuts) == 2
    assert cuts[0].through is True
    assert cuts[0].depth_in_layer_mm == pytest.approx(20)
    assert cuts[1].through is False
    assert cuts[1].depth_in_layer_mm == pytest.approx(10)


def test_pocket_cuts_shallow_only_top_layer() -> None:
    plan = LayerPlan(layers=[
        FoamLayer(20, LayerRole.BOTTOM),
        FoamLayer(40, LayerRole.CUTOUT),
        FoamLayer(40, LayerRole.CUTOUT),
    ])
    cuts = pocket_cuts_per_layer(plan, pocket_depth_mm=15)
    assert cuts[0].through is False
    assert cuts[0].depth_in_layer_mm == pytest.approx(15)
    assert cuts[1].depth_in_layer_mm == 0


def test_serialization_roundtrip() -> None:
    layer = FoamLayer(thickness_mm=25.0, role=LayerRole.SPACER)
    assert FoamLayer.from_dict(layer.to_dict()) == layer
