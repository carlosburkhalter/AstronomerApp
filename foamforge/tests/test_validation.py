"""Tests des contrôles de sécurité."""

from __future__ import annotations

from foamforge.core.geometry import CutoutSpec, CutType, RectShape
from foamforge.core.project import FoamSheet, Project
from foamforge.core.validation import Severity, validate_project, worst_severity


def _project(**kwargs) -> Project:
    defaults = dict(
        sheet=FoamSheet(width_mm=400, height_mm=300, thickness_mm=50),
        min_spacing_mm=8.0,
        min_border_mm=12.0,
    )
    defaults.update(kwargs)
    return Project(**defaults)


def test_valid_design_is_green() -> None:
    project = _project()
    project.add_shape(RectShape(
        width_mm=80, height_mm=60, x_mm=100, y_mm=100,
        spec=CutoutSpec(depth_mm=30, margin_mm=1),
    ))
    project.add_shape(RectShape(
        width_mm=80, height_mm=60, x_mm=280, y_mm=200,
        spec=CutoutSpec(depth_mm=30, margin_mm=1),
    ))
    issues = validate_project(project)
    assert worst_severity(issues) is Severity.OK
    assert len(issues) == 1


def test_overlap_is_blocking() -> None:
    project = _project()
    for x in (100, 130):
        project.add_shape(RectShape(width_mm=80, height_mm=60,
                                    x_mm=x, y_mm=150))
    issues = validate_project(project)
    assert any(i.code == "overlap" and i.severity is Severity.ERROR
               for i in issues)


def test_thin_wall_detected() -> None:
    project = _project()
    # Découpes de 82 mm (80 + 2×1 de marge) espacées de 85 mm centre à
    # centre → paroi de 3 mm < minimum/2 (4 mm) : erreur bloquante.
    project.add_shape(RectShape(width_mm=80, height_mm=60, x_mm=100,
                                y_mm=150, spec=CutoutSpec(margin_mm=1)))
    project.add_shape(RectShape(width_mm=80, height_mm=60, x_mm=185,
                                y_mm=150, spec=CutoutSpec(margin_mm=1)))
    issues = validate_project(project)
    assert any(i.code == "wall_too_thin" and i.severity is Severity.ERROR
               for i in issues)


def test_spacing_warning_between_half_and_full_minimum() -> None:
    project = _project()
    # Paroi de 6 mm : entre 4 (minimum/2) et 8 (minimum) → avertissement.
    project.add_shape(RectShape(width_mm=80, height_mm=60, x_mm=100,
                                y_mm=150, spec=CutoutSpec(margin_mm=0)))
    project.add_shape(RectShape(width_mm=80, height_mm=60, x_mm=186,
                                y_mm=150, spec=CutoutSpec(margin_mm=0)))
    issues = validate_project(project)
    assert any(i.code == "wall_thin" and i.severity is Severity.WARNING
               for i in issues)


def test_outside_sheet_is_blocking() -> None:
    project = _project()
    project.add_shape(RectShape(width_mm=80, height_mm=60, x_mm=390,
                                y_mm=150))
    issues = validate_project(project)
    assert any(i.code == "outside_sheet" for i in issues)


def test_border_too_close_is_blocking() -> None:
    project = _project()
    # Bord gauche à 4 mm (< 12/2 = 6 mm) → erreur.
    project.add_shape(RectShape(width_mm=80, height_mm=60, x_mm=45,
                                y_mm=150, spec=CutoutSpec(margin_mm=1)))
    issues = validate_project(project)
    assert any(i.code == "border_too_close" and i.severity is Severity.ERROR
               for i in issues)


def test_pocket_deeper_than_sheet_is_blocking() -> None:
    project = _project()
    project.add_shape(RectShape(
        width_mm=80, height_mm=60, x_mm=150, y_mm=150,
        spec=CutoutSpec(depth_mm=80, cut_type=CutType.POCKET),
    ))
    issues = validate_project(project)
    assert any(i.code == "depth_exceeds_thickness"
               and i.severity is Severity.ERROR for i in issues)


def test_unbalanced_weight_warns() -> None:
    project = _project()
    # Tout le poids dans le coin haut-gauche.
    project.add_shape(RectShape(
        width_mm=60, height_mm=60, x_mm=60, y_mm=60,
        spec=CutoutSpec(depth_mm=30, weight_g=2000),
    ))
    issues = validate_project(project)
    assert any(i.code == "weight_unbalanced" for i in issues)
