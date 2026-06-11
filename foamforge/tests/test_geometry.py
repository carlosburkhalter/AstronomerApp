"""Tests du modèle géométrique."""

from __future__ import annotations

import math

import pytest

from shapely.geometry import Polygon

from foamforge.core.geometry import (
    CircleShape,
    CutoutSpec,
    CutType,
    PolygonShape,
    RectShape,
    Shape,
    TextShape,
    center_of_mass,
    distance_mm,
    shape_from_dict,
)


def test_rect_dimensions() -> None:
    rect = RectShape(width_mm=80, height_mm=40, x_mm=100, y_mm=50)
    minx, miny, maxx, maxy = rect.object_polygon().bounds
    assert (maxx - minx) == pytest.approx(80)
    assert (maxy - miny) == pytest.approx(40)
    assert (minx + maxx) / 2 == pytest.approx(100)


def test_margin_expands_cut() -> None:
    rect = RectShape(width_mm=50, height_mm=30,
                     spec=CutoutSpec(margin_mm=2.0))
    minx, miny, maxx, maxy = rect.cut_polygon().bounds
    assert (maxx - minx) == pytest.approx(54, abs=0.05)
    assert (maxy - miny) == pytest.approx(34, abs=0.05)


def test_circle_area_precision() -> None:
    circle = CircleShape(diameter_mm=40, spec=CutoutSpec(margin_mm=0.0))
    expected = math.pi * 20**2
    # Tolérance < 0.1 % : précision suffisante pour la découpe laser.
    assert circle.cut_polygon().area == pytest.approx(expected, rel=1e-3)


def test_corner_radius_shrinks_corners() -> None:
    sharp = RectShape(width_mm=60, height_mm=40,
                      spec=CutoutSpec(margin_mm=0, corner_radius_mm=0))
    rounded = RectShape(width_mm=60, height_mm=40,
                        spec=CutoutSpec(margin_mm=0, corner_radius_mm=8))
    # L'arrondi retire de la matière dans les angles mais garde l'emprise.
    assert rounded.cut_polygon().area < sharp.cut_polygon().area
    assert rounded.cut_polygon().bounds == pytest.approx(
        sharp.cut_polygon().bounds, abs=0.05
    )


def test_rotation_changes_bounds() -> None:
    rect = RectShape(width_mm=100, height_mm=10, rotation_deg=90,
                     spec=CutoutSpec(margin_mm=0))
    minx, miny, maxx, maxy = rect.cut_polygon().bounds
    assert (maxx - minx) == pytest.approx(10, abs=0.01)
    assert (maxy - miny) == pytest.approx(100, abs=0.01)


def test_serialization_roundtrip() -> None:
    shapes: list[Shape] = [
        RectShape(width_mm=80, height_mm=40, x_mm=10, y_mm=20,
                  rotation_deg=15,
                  spec=CutoutSpec(name="Caméra", depth_mm=35, margin_mm=2,
                                  cut_type=CutType.POCKET, weight_g=400,
                                  comment="fragile")),
        CircleShape(diameter_mm=31.75, x_mm=5, y_mm=5),
        PolygonShape(points_mm=[(0, 0), (30, 0), (15, 25)], x_mm=50, y_mm=60),
        TextShape(text="OCULAIRES", font_height_mm=8, x_mm=70, y_mm=80),
    ]
    for original in shapes:
        restored = shape_from_dict(original.to_dict())
        assert restored.to_dict() == original.to_dict()
        assert restored.cut_polygon().area == pytest.approx(
            original.cut_polygon().area
        )


def test_text_is_always_engraving() -> None:
    text = TextShape(text="ZWO", spec=CutoutSpec(cut_type=CutType.FULL,
                                                 margin_mm=3))
    assert text.spec.cut_type is CutType.ENGRAVE
    assert text.spec.margin_mm == 0.0


def test_duplicate_is_independent() -> None:
    rect = RectShape(width_mm=50, height_mm=30, x_mm=10, y_mm=10)
    copy = rect.duplicate()
    assert copy.id != rect.id
    assert copy.x_mm == rect.x_mm + 10
    copy.spec.depth_mm = 99
    assert rect.spec.depth_mm != 99


def test_distance_and_center_of_mass() -> None:
    a = RectShape(width_mm=20, height_mm=20, x_mm=0, y_mm=0,
                  spec=CutoutSpec(margin_mm=0, weight_g=100))
    b = RectShape(width_mm=20, height_mm=20, x_mm=50, y_mm=0,
                  spec=CutoutSpec(margin_mm=0, weight_g=300))
    assert distance_mm(a, b) == pytest.approx(30)
    com = center_of_mass([a, b])
    assert com is not None
    cx, _, total = com
    assert cx == pytest.approx(37.5)
    assert total == pytest.approx(400)


def test_degenerate_polygon_is_safe() -> None:
    poly = PolygonShape(points_mm=[(0, 0)])
    assert poly.cut_polygon().area > 0


def test_corner_radius_applied_detection() -> None:
    """Petit objet + grand rayon : repli détectable (pour avertir)."""
    ok = RectShape(width_mm=60, height_mm=40,
                   spec=CutoutSpec(margin_mm=0, corner_radius_mm=8))
    assert ok.corner_radius_applied()
    too_big = RectShape(width_mm=20, height_mm=10,
                        spec=CutoutSpec(margin_mm=0, corner_radius_mm=12))
    assert not too_big.corner_radius_applied()
    # Le repli garde l'objet visible : jamais de géométrie vide.
    assert too_big.cut_polygon().area > 0


def test_corner_radius_on_compound_shape() -> None:
    """Arrondi appliqué sur une forme fusionnée (angles du L adoucis)."""
    from foamforge.core.booleans import merge_shapes

    sources = [
        RectShape(width_mm=100, height_mm=40, x_mm=50, y_mm=20,
                  spec=CutoutSpec(margin_mm=0)),
        RectShape(width_mm=40, height_mm=100, x_mm=20, y_mm=50,
                  spec=CutoutSpec(margin_mm=0)),
    ]
    compound, = merge_shapes(sources)
    compound.spec.margin_mm = 0.0
    sharp_area = compound.cut_polygon().area
    compound.spec.corner_radius_mm = 6.0
    rounded_area = compound.cut_polygon().area
    assert compound.corner_radius_applied()
    assert rounded_area < sharp_area  # angles convexes adoucis
    # L'emprise reste identique : l'arrondi ne déforme pas la silhouette.
    assert compound.cut_polygon().bounds == pytest.approx(
        Polygon(compound.object_polygon()).bounds, abs=0.05
    )
