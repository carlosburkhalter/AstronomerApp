"""Tests des formes composées (fusion / soustraction / intersection)."""

from __future__ import annotations

import pytest

from foamforge.core.booleans import (
    BooleanOperationError,
    intersect_shapes,
    merge_shapes,
    subtract_shapes,
)
from foamforge.core.geometry import (
    CircleShape,
    CutoutSpec,
    PolygonShape,
    RectShape,
    shape_from_dict,
)


def _l_shape_sources() -> list[RectShape]:
    """Deux rectangles chevauchés formant un L."""
    return [
        RectShape(width_mm=100, height_mm=40, x_mm=50, y_mm=20,
                  spec=CutoutSpec(name="Base", depth_mm=30, margin_mm=2,
                                  weight_g=100)),
        RectShape(width_mm=40, height_mm=100, x_mm=20, y_mm=50,
                  spec=CutoutSpec(name="Branche", depth_mm=40, weight_g=50)),
    ]


def test_merge_two_rects_makes_L() -> None:
    sources = _l_shape_sources()
    merged, = merge_shapes(sources, name="Équerre")
    assert isinstance(merged, PolygonShape)
    assert merged.spec.name == "Équerre"
    # Aire du L = somme des aires - chevauchement (40 × 40).
    expected = 100 * 40 + 40 * 100 - 40 * 40
    assert merged.object_polygon().area == pytest.approx(expected, rel=1e-6)
    # La spec hérite : profondeur max, poids cumulé, source = compound.
    assert merged.spec.depth_mm == 40
    assert merged.spec.weight_g == 150
    assert merged.spec.creation_source == "compound"


def test_merge_disjoint_shapes_fails_clearly() -> None:
    a = RectShape(width_mm=20, height_mm=20, x_mm=0, y_mm=0)
    b = RectShape(width_mm=20, height_mm=20, x_mm=200, y_mm=200)
    with pytest.raises(BooleanOperationError, match="disjoints"):
        merge_shapes([a, b])


def test_subtract_circle_makes_notch() -> None:
    base = RectShape(width_mm=100, height_mm=60, x_mm=0, y_mm=0,
                     spec=CutoutSpec(name="Boîtier", depth_mm=30))
    # Cercle à cheval sur le bord droit : encoche ouverte.
    notch = CircleShape(diameter_mm=30, x_mm=50, y_mm=0)
    result, = subtract_shapes(base, [notch])
    assert result.object_polygon().area < base.object_polygon().area
    assert "encoche" in result.spec.name


def test_subtract_inside_creates_hole() -> None:
    """Un cercle entièrement intérieur crée un trou (anneau conservé)."""
    base = RectShape(width_mm=100, height_mm=100, x_mm=0, y_mm=0,
                     spec=CutoutSpec(margin_mm=0))
    hole = CircleShape(diameter_mm=30, x_mm=0, y_mm=0)
    result, = subtract_shapes(base, [hole])
    polygon = result.base_polygon()
    assert len(polygon.interiors) == 1
    assert polygon.area == pytest.approx(
        100 * 100 - hole.object_polygon().area, rel=1e-3
    )


def test_subtract_everything_fails() -> None:
    base = RectShape(width_mm=20, height_mm=20, x_mm=0, y_mm=0)
    eater = RectShape(width_mm=100, height_mm=100, x_mm=0, y_mm=0)
    with pytest.raises(BooleanOperationError, match="vide"):
        subtract_shapes(base, [eater])


def test_intersection() -> None:
    a = RectShape(width_mm=60, height_mm=60, x_mm=0, y_mm=0)
    b = RectShape(width_mm=60, height_mm=60, x_mm=30, y_mm=30)
    result, = intersect_shapes([a, b])
    assert result.object_polygon().area == pytest.approx(30 * 30, rel=1e-6)


def test_compound_serialization_with_holes() -> None:
    """Les trous des formes composées survivent à la sauvegarde JSON."""
    base = RectShape(width_mm=100, height_mm=100, x_mm=50, y_mm=50)
    hole = CircleShape(diameter_mm=30, x_mm=50, y_mm=50)
    compound, = subtract_shapes(base, [hole])
    restored = shape_from_dict(compound.to_dict())
    assert isinstance(restored, PolygonShape)
    assert len(restored.base_polygon().interiors) == 1
    assert restored.base_polygon().area == pytest.approx(
        compound.base_polygon().area
    )


def test_compound_margin_still_applies() -> None:
    """La marge de tolérance reste applicable à la forme composée."""
    merged, = merge_shapes(_l_shape_sources())
    merged.spec.margin_mm = 0.0
    area_no_margin = merged.cut_polygon().area
    merged.spec.margin_mm = 3.0
    assert merged.cut_polygon().area > area_no_margin


def test_merge_requires_two_shapes() -> None:
    with pytest.raises(BooleanOperationError):
        merge_shapes([RectShape()])


def test_subtract_splitting_base_creates_islands() -> None:
    """Une soustraction qui coupe la base en deux produit deux formes."""
    base = RectShape(width_mm=100, height_mm=40, x_mm=0, y_mm=0,
                     spec=CutoutSpec(name="Barre", depth_mm=30))
    splitter = RectShape(width_mm=10, height_mm=60, x_mm=0, y_mm=0)
    islands = subtract_shapes(base, [splitter])
    assert len(islands) == 2
    # Le plus grand îlot garde le nom, le second est numéroté.
    assert islands[0].object_polygon().area >= islands[1].object_polygon().area
    assert "(2)" in islands[1].spec.name
    total = sum(s.object_polygon().area for s in islands)
    assert total == pytest.approx(100 * 40 - 10 * 40, rel=1e-6)


def test_merge_islands_opt_in() -> None:
    """La fusion de formes disjointes reste une erreur par défaut, mais
    peut produire des îlots si demandé explicitement."""
    a = RectShape(width_mm=20, height_mm=20, x_mm=0, y_mm=0)
    b = RectShape(width_mm=20, height_mm=20, x_mm=200, y_mm=200)
    with pytest.raises(BooleanOperationError):
        merge_shapes([a, b])
    islands = merge_shapes([a, b], split_islands=True)
    assert len(islands) == 2
