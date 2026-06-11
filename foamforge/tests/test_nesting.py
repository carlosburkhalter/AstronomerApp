"""Tests du placement automatique."""

from __future__ import annotations

from itertools import combinations

from foamforge.core.geometry import CutoutSpec, RectShape
from foamforge.core.nesting import propose_layouts
from foamforge.core.project import FoamSheet, Project
from foamforge.core.validation import Severity, validate_project, worst_severity


def _crowded_project() -> Project:
    """Projet dont les formes se chevauchent volontairement au départ."""
    project = Project(
        sheet=FoamSheet(width_mm=400, height_mm=300, thickness_mm=50)
    )
    sizes = [(120, 80), (100, 60), (80, 80), (60, 40), (50, 50)]
    for i, (w, h) in enumerate(sizes):
        project.add_shape(RectShape(
            width_mm=w, height_mm=h, x_mm=100, y_mm=100,
            spec=CutoutSpec(name=f"Objet {i + 1}", margin_mm=1,
                            weight_g=100 * (i + 1)),
        ))
    return project


def test_nesting_resolves_overlaps() -> None:
    project = _crowded_project()
    proposals = propose_layouts(project)
    assert proposals, "au moins une proposition attendue"
    best = proposals[0]
    assert best.complete, "la plaque est assez grande pour tout placer"
    best.apply(project)
    # Après placement : plus aucune erreur bloquante.
    issues = validate_project(project)
    assert worst_severity(issues) is not Severity.ERROR


def test_nesting_respects_spacing_and_border() -> None:
    project = _crowded_project()
    proposals = propose_layouts(project, strategies=["area_desc"])
    proposals[0].apply(project)
    foam = project.foam_polygon()
    polys = [s.cut_polygon() for s in project.shapes]
    for poly in polys:
        assert foam.contains(poly)
        assert poly.distance(foam.exterior) >= project.min_border_mm - 0.01
    for a, b in combinations(polys, 2):
        assert a.distance(b) >= project.min_spacing_mm - 0.01


def test_nesting_reports_unplaceable() -> None:
    project = Project(sheet=FoamSheet(width_mm=100, height_mm=100,
                                      thickness_mm=50))
    project.add_shape(RectShape(width_mm=200, height_mm=200))
    proposals = propose_layouts(project, strategies=["area_desc"])
    assert not proposals[0].complete
    assert len(proposals[0].unplaced_ids) == 1
