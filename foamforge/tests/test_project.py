"""Tests du modèle de projet et de la persistance JSON."""

from __future__ import annotations

from pathlib import Path

import pytest

from foamforge.core.geometry import CutoutSpec, RectShape, TextShape
from foamforge.core.project import FoamSheet, Project


def _sample_project() -> Project:
    project = Project(
        name="Valise astro",
        sheet=FoamSheet(width_mm=500, height_mm=350, thickness_mm=60),
        layer_count=2,
        foam_type="Plastazote",
        notes="Penser au chiffon optique",
    )
    project.add_shape(RectShape(
        width_mm=120, height_mm=80, x_mm=100, y_mm=100,
        spec=CutoutSpec(name="Caméra", depth_mm=45),
    ))
    project.add_shape(RectShape(
        width_mm=60, height_mm=60, x_mm=300, y_mm=100,
        spec=CutoutSpec(name="Roue à filtres", depth_mm=30),
    ))
    project.add_shape(TextShape(
        text="ASTRO", x_mm=250, y_mm=300,
        spec=CutoutSpec(name="Étiquette"),
    ))
    return project


def test_save_load_roundtrip(tmp_path: Path) -> None:
    project = _sample_project()
    path = tmp_path / "test.foamforge.json"
    project.save(path)
    restored = Project.load(path)
    assert restored.to_dict() == project.to_dict()
    assert len(restored.shapes) == 3
    assert restored.sheet.thickness_mm == 60


def test_cut_order_auto_increment() -> None:
    project = _sample_project()
    orders = [s.spec.cut_order for s in project.shapes]
    assert orders == [1, 2, 3]
    assert project.next_cut_order() == 4


def test_checklist_excludes_text() -> None:
    project = _sample_project()
    items = project.checklist_items()
    assert items == ["Caméra", "Roue à filtres"]


def test_remove_and_get_shape() -> None:
    project = _sample_project()
    first = project.shapes[0]
    assert project.get_shape(first.id) is first
    project.remove_shape(first.id)
    assert project.get_shape(first.id) is None
    assert len(project.shapes) == 2


def test_rejects_newer_schema() -> None:
    with pytest.raises(ValueError, match="version plus récente"):
        Project.from_dict({"schema_version": 999})
