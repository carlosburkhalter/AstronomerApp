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


def _result_polygons(
    geometry, operation: str, split_islands: bool
) -> list[Polygon]:
    """Valide et normalise le résultat d'une opération booléenne.

    Si le résultat est un MultiPolygon (plusieurs îlots disjoints, par
    exemple après une soustraction qui coupe la base en deux) :

    - ``split_islands=True`` : retourne un polygone par îlot (l'appelant
      crée plusieurs formes) ;
    - ``split_islands=False`` : erreur claire pour l'utilisateur.
    """
    if geometry.is_empty:
        raise BooleanOperationError(
            f"{operation} : le résultat est vide (les formes ne se "
            "chevauchent pas comme attendu)."
        )
    geometry = geometry.buffer(0)  # répare la géométrie
    if isinstance(geometry, MultiPolygon):
        if not split_islands:
            raise BooleanOperationError(
                f"{operation} : le résultat est en plusieurs morceaux "
                "disjoints. Rapprochez les formes pour qu'elles se "
                "touchent, ou gardez-les séparées."
            )
        islands = sorted(
            (g for g in geometry.geoms if g.area > 0),
            key=lambda g: g.area,
            reverse=True,
        )
        if not islands:
            raise BooleanOperationError(
                f"{operation} : le résultat n'est pas une surface exploitable."
            )
        return islands
    if not isinstance(geometry, Polygon) or geometry.area <= 0:
        raise BooleanOperationError(
            f"{operation} : le résultat n'est pas une surface exploitable."
        )
    return [geometry]


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


def _build_shapes(
    polygons: list[Polygon], spec_source: CutoutSpec
) -> list[PolygonShape]:
    """Crée une forme par polygone ; les îlots secondaires sont numérotés."""
    shapes: list[PolygonShape] = []
    for i, polygon in enumerate(polygons):
        spec = CutoutSpec.from_dict(spec_source.to_dict())
        if i > 0:
            spec.name = f"{spec_source.name} ({i + 1})"
            spec.cut_order = 0  # ré-attribué par le projet à l'ajout
        shapes.append(PolygonShape.from_polygon(polygon, spec=spec))
    return shapes


def merge_shapes(
    shapes: list[Shape],
    name: str | None = None,
    split_islands: bool = False,
) -> list[PolygonShape]:
    """Fusionne (union) plusieurs formes chevauchées.

    Retourne une liste de formes : une seule si le résultat est d'un seul
    tenant, plusieurs si ``split_islands`` et îlots disjoints.
    """
    if len(shapes) < 2:
        raise BooleanOperationError("Sélectionnez au moins deux formes.")
    union = unary_union([s.object_polygon() for s in shapes])
    polygons = _result_polygons(union, "Fusion", split_islands)
    return _build_shapes(polygons, _compound_spec(shapes, name))


def subtract_shapes(
    base: Shape,
    tools: list[Shape],
    name: str | None = None,
    split_islands: bool = True,
) -> list[PolygonShape]:
    """Soustrait des formes « outils » d'une forme de base (encoches).

    L'ordre compte : la première forme sélectionnée est la base, les
    suivantes sont retirées. Une soustraction qui coupe la base en deux
    produit plusieurs formes (``split_islands`` par défaut : c'est un
    résultat légitime, contrairement à une fusion de formes disjointes).
    """
    if not tools:
        raise BooleanOperationError(
            "Sélectionnez la forme de base puis les formes à soustraire."
        )
    result = base.object_polygon().difference(
        unary_union([t.object_polygon() for t in tools])
    )
    polygons = _result_polygons(result, "Soustraction", split_islands)
    spec = _compound_spec([base], name)
    spec.name = name or f"{base.spec.name} (encoche)"
    return _build_shapes(polygons, spec)


def intersect_shapes(
    shapes: list[Shape],
    name: str | None = None,
    split_islands: bool = False,
) -> list[PolygonShape]:
    """Intersection : ne garde que la zone commune à toutes les formes."""
    if len(shapes) < 2:
        raise BooleanOperationError("Sélectionnez au moins deux formes.")
    result = shapes[0].object_polygon()
    for other in shapes[1:]:
        result = result.intersection(other.object_polygon())
    polygons = _result_polygons(result, "Intersection", split_islands)
    return _build_shapes(polygons, _compound_spec(shapes, name))
