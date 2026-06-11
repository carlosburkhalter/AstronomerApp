"""Tests de la bibliothèque d'objets SQLite."""

from __future__ import annotations

from pathlib import Path

import pytest

from foamforge.core.geometry import PolygonShape, RectShape
from foamforge.database.db import DEFAULT_CATEGORIES, get_connection
from foamforge.database.object_library import LibraryObject, ObjectLibrary


@pytest.fixture
def library() -> ObjectLibrary:
    return ObjectLibrary(get_connection(":memory:"))


def _camera() -> LibraryObject:
    return LibraryObject(
        name="ZWO ASI2600MC",
        brand="ZWO",
        category="caméras astro",
        width_mm=86, height_mm=86, depth_mm=120,
        weight_g=700,
        recommended_depth_mm=45,
        recommended_margin_mm=2,
        tags=["caméra", "refroidie"],
    )


def test_default_categories_seeded(library: ObjectLibrary) -> None:
    assert set(DEFAULT_CATEGORIES) <= set(library.categories())


def test_crud_roundtrip(library: ObjectLibrary) -> None:
    obj = library.add(_camera())
    assert obj.id is not None
    fetched = library.get(obj.id)
    assert fetched is not None
    assert fetched.name == "ZWO ASI2600MC"
    assert fetched.tags == ["caméra", "refroidie"]

    fetched.weight_g = 705
    library.update(fetched)
    assert library.get(obj.id).weight_g == 705

    library.delete(obj.id)
    assert library.get(obj.id) is None


def test_search(library: ObjectLibrary) -> None:
    library.add(_camera())
    library.add(LibraryObject(name="Nagler 13mm", category="oculaires"))
    assert len(library.search()) == 2
    assert len(library.search(text="ZWO")) == 1
    assert len(library.search(category="oculaires")) == 1
    assert len(library.search(text="ZWO", category="oculaires")) == 0


def test_to_shape_rect_and_contour(library: ObjectLibrary) -> None:
    rect_obj = library.add(_camera())
    shape = rect_obj.to_shape(x_mm=50, y_mm=60)
    assert isinstance(shape, RectShape)
    assert shape.spec.depth_mm == 45
    assert shape.spec.weight_g == 700

    contour_obj = library.add(LibraryObject(
        name="Forme libre",
        contour_mm=[(-10, -10), (10, -10), (0, 15)],
    ))
    shape = contour_obj.to_shape()
    assert isinstance(shape, PolygonShape)
    assert shape.cut_polygon().area > 0


def test_import_export_json(library: ObjectLibrary, tmp_path: Path) -> None:
    library.add(_camera())
    library.add(LibraryObject(name="Nagler 13mm", category="oculaires",
                              contour_mm=[(-5, -5), (5, -5), (5, 5), (-5, 5)]))
    export_path = library.export_json(tmp_path / "lib.json")

    other = ObjectLibrary(get_connection(":memory:"))
    count = other.import_json(export_path)
    assert count == 2
    restored = other.search(text="Nagler")[0]
    assert restored.contour_mm == [(-5, -5), (5, -5), (5, 5), (-5, 5)]
