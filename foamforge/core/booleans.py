"""Formes composées : fusion, soustraction, intersection de formes.

Permet de construire une géométrie personnalisée en combinant des formes
simples (deux rectangles chevauchés → découpe en L ; un cercle soustrait
d'un rectangle → encoche). Les opérations travaillent sur la géométrie
des OBJETS (sans marge) : la forme composée reçoit ensuite sa propre
marge de tolérance, son arrondi, sa profondeur, comme toute autre forme.

La spec de la forme composée hérite de la première forme source
(profondeur, type de découpe, poids cumulé).
"""

from __future__ import annotations

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

from foamforge.core.geometry import CutoutSpec, PolygonShape, Shape


class BooleanOperationError(Exception):
    """Opération booléenne impossible (résultat vide ou disjoint)."""


def _as_single_polygon(geometry, operation: str) -> Polygon:
    """Valide et normalise le résultat d'une opération booléenne."""
    if geometry.is_empty:
        raise BooleanOperationError(
            f"{operation} : le résultat est vide (les formes ne se "
            "chevauchent pas comme attendu)."
        )
    geometry = geometry.buffer(0)  # répare la géométrie
    if isinstance(geometry, MultiPolygon):
        raise BooleanOperationError(
            f"{operation} : le résultat est en plusieurs morceaux disjoints. "
            "Rapprochez les formes pour qu'elles se touchent, ou gardez-les "
            "séparées."
        )
    if not isinstance(geometry, Polygon) or geometry.area <= 0:
        raise BooleanOperationError(
            f"{operation} : le résultat n'est pas une surface exploitable."
        )
    return geometry


def _compound_spec(sources: list[Shape], name: str | None) -> CutoutSpec:
    """Spécification de découpe de la forme composée (héritée des sources)."""
    first = sources[0].spec
    return CutoutSpec(
        name=name or f"{first.name} (composée)",
        depth_mm=max(s.spec.depth_mm for s in sources),
        margin_mm=first.margin_mm,
        corner_radius_mm=first.corner_radius_mm,
        cut_type=first.cut_type,
        comment=first.comment,
        weight_g=sum(s.spec.weight_g for s in sources),
        object_height_mm=max(s.spec.object_height_mm for s in sources),
        creation_source="compound",
    )


def merge_shapes(shapes: list[Shape], name: str | None = None) -> PolygonShape:
    """Fusionne (union) plusieurs formes chevauchées en une seule.

    Les formes doivent former une surface d'un seul tenant.
    """
    if len(shapes) < 2:
        raise BooleanOperationError("Sélectionnez au moins deux formes.")
    union = unary_union([s.object_polygon() for s in shapes])
    polygon = _as_single_polygon(union, "Fusion")
    return PolygonShape.from_polygon(polygon, spec=_compound_spec(shapes, name))


def subtract_shapes(
    base: Shape, tools: list[Shape], name: str | None = None
) -> PolygonShape:
    """Soustrait des formes « outils » d'une forme de base (encoches).

    L'ordre compte : la première forme sélectionnée est la base, les
    suivantes sont retirées.
    """
    if not tools:
        raise BooleanOperationError(
            "Sélectionnez la forme de base puis les formes à soustraire."
        )
    result = base.object_polygon().difference(
        unary_union([t.object_polygon() for t in tools])
    )
    polygon = _as_single_polygon(result, "Soustraction")
    spec = _compound_spec([base], name)
    spec.name = name or f"{base.spec.name} (encoche)"
    return PolygonShape.from_polygon(polygon, spec=spec)


def intersect_shapes(
    shapes: list[Shape], name: str | None = None
) -> PolygonShape:
    """Intersection : ne garde que la zone commune à toutes les formes."""
    if len(shapes) < 2:
        raise BooleanOperationError("Sélectionnez au moins deux formes.")
    result = shapes[0].object_polygon()
    for other in shapes[1:]:
        result = result.intersection(other.object_polygon())
    polygon = _as_single_polygon(result, "Intersection")
    return PolygonShape.from_polygon(polygon, spec=_compound_spec(shapes, name))
