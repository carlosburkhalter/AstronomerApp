"""Placement automatique (nesting 2D) des logements dans la mousse.

Algorithme volontairement simple et robuste pour le MVP : placement
glouton « bottom-left » sur une grille de candidats, avec vérification
exacte des distances via Shapely. Plusieurs stratégies de tri produisent
plusieurs propositions parmi lesquelles l'utilisateur choisit.

Limites connues (voir feuille de route) : pas de rotation automatique,
pas de métaheuristique. La précision des contraintes (parois minimales)
prime sur le taux de remplissage.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from shapely import affinity
from shapely.geometry import Polygon
from shapely.strtree import STRtree

from foamforge.core.geometry import Shape, ShapeKind
from foamforge.core.project import Project

# Pas de la grille de positions candidates (mm). Plus fin = plus dense
# mais plus lent ; 5 mm est un bon compromis pour des mousses de valise.
_GRID_STEP_MM = 5.0


@dataclass
class Placement:
    """Position proposée pour une forme."""

    shape_id: str
    x_mm: float
    y_mm: float


@dataclass
class NestingProposal:
    """Une proposition complète de placement."""

    strategy: str
    placements: list[Placement] = field(default_factory=list)
    unplaced_ids: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.unplaced_ids

    def apply(self, project: Project) -> None:
        """Applique la proposition au projet (déplace les formes)."""
        for placement in self.placements:
            shape = project.get_shape(placement.shape_id)
            if shape is not None:
                shape.move_to(placement.x_mm, placement.y_mm)


def _sorted_shapes(shapes: list[Shape], strategy: str) -> list[Shape]:
    """Ordre de placement selon la stratégie choisie."""
    if strategy == "area_desc":
        return sorted(shapes, key=lambda s: s.cut_polygon().area, reverse=True)
    if strategy == "longest_side_desc":
        def longest(s: Shape) -> float:
            minx, miny, maxx, maxy = s.bounds()
            return max(maxx - minx, maxy - miny)
        return sorted(shapes, key=longest, reverse=True)
    if strategy == "weight_desc":
        # Les objets lourds d'abord, placés près du centre : meilleure
        # répartition du poids dans la valise.
        return sorted(
            shapes,
            key=lambda s: (s.spec.weight_g, s.cut_polygon().area),
            reverse=True,
        )
    raise ValueError(f"Stratégie de nesting inconnue : {strategy}")


def _candidate_positions(
    project: Project, strategy: str
) -> list[tuple[float, float]]:
    """Grille de positions candidates, ordonnée selon la stratégie."""
    sheet = project.sheet
    xs, ys = [], []
    x = project.min_border_mm
    while x <= sheet.width_mm - project.min_border_mm:
        xs.append(x)
        x += _GRID_STEP_MM
    y = project.min_border_mm
    while y <= sheet.height_mm - project.min_border_mm:
        ys.append(y)
        y += _GRID_STEP_MM
    positions = [(px, py) for py in ys for px in xs]
    if strategy == "weight_desc":
        # Tri par distance au centre : les premiers placés (les plus
        # lourds) occupent le centre de la plaque.
        cx, cy = sheet.width_mm / 2, sheet.height_mm / 2
        positions.sort(key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
    return positions


def _nest_once(project: Project, strategy: str) -> NestingProposal:
    """Une passe de placement glouton pour une stratégie donnée."""
    shapes = [s for s in project.shapes if s.kind is not ShapeKind.TEXT]
    proposal = NestingProposal(strategy=strategy)
    foam = project.foam_polygon().buffer(-project.min_border_mm)
    spacing = project.min_spacing_mm

    placed_polys: list[Polygon] = []
    tree: STRtree | None = None

    for shape in _sorted_shapes(shapes, strategy):
        # Polygone local (centré sur l'origine) à translater sur la grille.
        local = affinity.translate(shape.cut_polygon(), -shape.x_mm, -shape.y_mm)
        placed = False
        for x, y in _candidate_positions(project, strategy):
            candidate = affinity.translate(local, x, y)
            if not foam.contains(candidate):
                continue
            if tree is not None:
                # Pré-filtre spatial puis vérification exacte de la paroi.
                grown = candidate.buffer(spacing)
                hits = tree.query(grown)
                if any(grown.intersects(placed_polys[i]) for i in hits):
                    continue
            proposal.placements.append(Placement(shape.id, x, y))
            placed_polys.append(candidate)
            tree = STRtree(placed_polys)
            placed = True
            break
        if not placed:
            proposal.unplaced_ids.append(shape.id)
    return proposal


def propose_layouts(
    project: Project, strategies: list[str] | None = None
) -> list[NestingProposal]:
    """Calcule plusieurs propositions de placement automatique.

    Retourne les propositions triées : complètes d'abord, puis par nombre
    de formes placées décroissant.
    """
    if strategies is None:
        strategies = ["area_desc", "longest_side_desc", "weight_desc"]
    proposals = [_nest_once(project, s) for s in strategies]
    proposals.sort(key=lambda p: (not p.complete, len(p.unplaced_ids)))
    return proposals
