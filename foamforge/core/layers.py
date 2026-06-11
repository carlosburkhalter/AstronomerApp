"""FoamLayerPlanner : calcul de l'empilement de couches de mousse.

À partir de la profondeur intérieure DISPONIBLE POUR LA MOUSSE (partie
basse de la valise — le couvercle de la valise n'est jamais compté), des
épaisseurs disponibles, de la hauteur des objets et des profondeurs de
poche, propose un empilement exact (somme = profondeur intérieure) avec
un rôle par couche :

- ``BOTTOM``  : couche de fond, jamais découpée (protège le dessous) ;
- ``CUTOUT``  : couche découpée (les poches y descendent) ;
- ``SPACER``  : couche de compensation non découpée sous les CUTOUT ;
- ``SUPPORT`` : couche de soutien non découpée (réservée à un usage
  manuel/futur ; le planificateur ne la produit pas).

La couche SUPÉRIEURE de l'empilement est toujours une couche découpée.
Les poches sont mesurées depuis la surface de la mousse : une poche de
30 mm dans deux couches CUTOUT de 20 mm traverse la première (20 mm) et
entame la seconde de 10 mm. Le calcul est fait OBJET PAR OBJET
(:func:`compute_layer_assignments`) : chaque couche sait exactement
quelles formes la découpent, en traversant ou partiellement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any, Sequence

# Limite de sécurité de l'énumération des combinaisons (largement au-delà
# des cas réels : une valise de 300 mm en couches de 10 mm = 30 couches).
_MAX_LAYER_COUNT = 32


class LayerRole(str, Enum):
    """Rôle d'une couche dans l'empilement (le couvercle de la valise
    n'est PAS une couche de mousse : il n'existe pas de rôle « lid »)."""

    BOTTOM = "bottom"
    CUTOUT = "cutout"
    SPACER = "spacer"
    SUPPORT = "support"

    @property
    def label(self) -> str:
        return {
            LayerRole.BOTTOM: "Fond",
            LayerRole.CUTOUT: "Découpée",
            LayerRole.SPACER: "Compensation",
            LayerRole.SUPPORT: "Soutien",
        }[self]


@dataclass
class FoamLayer:
    """Une couche de mousse de l'empilement (ordre : du fond vers le haut)."""

    thickness_mm: float
    role: LayerRole

    def to_dict(self) -> dict[str, Any]:
        return {"thickness_mm": self.thickness_mm, "role": self.role.value}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FoamLayer":
        role = data.get("role", LayerRole.CUTOUT.value)
        # Anciens fichiers v0.2.0 : le rôle « lid » n'existe plus (le
        # couvercle de la valise n'est pas une couche de mousse) ; ces
        # couches deviennent de la compensation.
        if role == "lid":
            role = LayerRole.SPACER.value
        return cls(
            thickness_mm=float(data["thickness_mm"]),
            role=LayerRole(role),
        )


@dataclass
class LayerPlan:
    """Résultat du calcul d'empilement."""

    layers: list[FoamLayer] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def feasible(self) -> bool:
        return not self.errors and bool(self.layers)

    @property
    def total_mm(self) -> float:
        return sum(layer.thickness_mm for layer in self.layers)

    def cuttable_mm(self) -> float:
        """Profondeur découpable totale (somme des couches CUTOUT)."""
        return sum(
            layer.thickness_mm
            for layer in self.layers
            if layer.role is LayerRole.CUTOUT
        )

    def cutout_layers_top_down(self) -> list[FoamLayer]:
        """Couches CUTOUT de la surface vers le fond (ordre de poche)."""
        return [
            layer for layer in reversed(self.layers)
            if layer.role is LayerRole.CUTOUT
        ]


def _combos_summing_to(
    target_tenths: int, thicknesses_tenths: tuple[int, ...]
) -> list[tuple[int, ...]]:
    """Toutes les multisets d'épaisseurs (en dixièmes de mm) sommant
    exactement à ``target_tenths``. Ordonnées décroissantes, sans doublons."""
    ordered = tuple(sorted(set(thicknesses_tenths)))
    if not ordered:
        return []

    @lru_cache(maxsize=None)
    def solve(remaining: int, max_index: int, depth: int) -> tuple[tuple[int, ...], ...]:
        if remaining == 0:
            return ((),)
        if depth >= _MAX_LAYER_COUNT:
            return ()
        results: list[tuple[int, ...]] = []
        for i in range(max_index, -1, -1):
            t = ordered[i]
            if t <= remaining:
                for tail in solve(remaining - t, i, depth + 1):
                    results.append((t, *tail))
        return tuple(results)

    return list(solve(target_tenths, len(ordered) - 1, 0))


def plan_layers(
    case_depth_mm: float,
    available_foam_thicknesses_mm: Sequence[float],
    max_pocket_depth_mm: float = 0.0,
    max_object_height_mm: float = 0.0,
    min_bottom_floor_mm: float = 10.0,
    preferred_layer_count: int | None = None,
) -> LayerPlan:
    """Calcule un empilement de couches remplissant exactement la valise.

    :param case_depth_mm: profondeur intérieure de la valise.
    :param available_foam_thicknesses_mm: épaisseurs de plaques disponibles.
    :param max_pocket_depth_mm: poche la plus profonde du projet.
    :param max_object_height_mm: objet le plus haut (hauteur réelle mesurée).
    :param min_bottom_floor_mm: fond minimal souhaité sous les poches.
    :param preferred_layer_count: si fourni, privilégie ce nombre de couches.

    Le couvercle de la valise n'entre jamais dans le calcul : seule la
    profondeur disponible pour la mousse est remplie, et la couche du
    dessus est toujours une couche découpée.
    """
    plan = LayerPlan()
    thicknesses = sorted({t for t in available_foam_thicknesses_mm if t > 0})
    if not thicknesses:
        plan.errors.append("Aucune épaisseur de mousse disponible.")
        return plan
    if case_depth_mm <= 0:
        plan.errors.append("Profondeur intérieure de valise invalide.")
        return plan

    # --- Contrôles préalables ----------------------------------------- #
    if max_object_height_mm > case_depth_mm:
        plan.errors.append(
            f"Objet trop haut : {max_object_height_mm:.0f} mm pour une "
            f"valise de {case_depth_mm:.0f} mm de profondeur intérieure."
        )
        return plan

    needed_cut = max(max_pocket_depth_mm, max_object_height_mm)
    if needed_cut + min_bottom_floor_mm > case_depth_mm:
        plan.errors.append(
            f"Impossible : poche/objet de {needed_cut:.0f} mm + fond minimal "
            f"de {min_bottom_floor_mm:.0f} mm > profondeur intérieure de "
            f"{case_depth_mm:.0f} mm. Réduisez le fond minimal ou la "
            "profondeur de poche."
        )
        return plan

    # --- Énumération des empilements possibles ------------------------- #
    # Travail en dixièmes de mm : évite les erreurs d'arrondi flottant.
    tenths = tuple(round(t * 10) for t in thicknesses)
    target = round(case_depth_mm * 10)
    combos = _combos_summing_to(target, tenths)
    if not combos:
        plan.errors.append(
            f"Aucune combinaison des épaisseurs {thicknesses} mm ne remplit "
            f"exactement {case_depth_mm:.0f} mm. Ajoutez une épaisseur "
            "(par exemple une plaque fine de compensation)."
        )
        return plan

    # --- Affectation des rôles et notation des candidats ---------------- #
    best: tuple[float, list[FoamLayer]] | None = None
    for combo in combos:
        assignment = _assign_roles(
            [t / 10.0 for t in combo],
            needed_cut_mm=needed_cut,
            min_bottom_floor_mm=min_bottom_floor_mm,
        )
        if assignment is None:
            continue
        score = _score(assignment, preferred_layer_count)
        if best is None or score < best[0]:
            best = (score, assignment)

    if best is None:
        plan.errors.append(
            "Aucun empilement ne permet à la fois le fond minimal de "
            f"{min_bottom_floor_mm:.0f} mm et {needed_cut:.0f} mm de "
            "profondeur découpable. Ajustez les épaisseurs disponibles."
        )
        return plan

    plan.layers = best[1]
    # --- Avertissements ------------------------------------------------ #
    cuttable = plan.cuttable_mm()
    if max_pocket_depth_mm > 0 and cuttable < max_pocket_depth_mm:
        plan.errors.append(
            f"Profondeur découpable ({cuttable:.0f} mm) insuffisante pour "
            f"la poche la plus profonde ({max_pocket_depth_mm:.0f} mm)."
        )
    bottom = sum(
        layer.thickness_mm for layer in plan.layers
        if layer.role in (LayerRole.BOTTOM, LayerRole.SPACER)
    )
    if bottom < min_bottom_floor_mm:
        plan.warnings.append(
            f"Fond restant de {bottom:.0f} mm sous les découpes "
            f"(souhaité : {min_bottom_floor_mm:.0f} mm)."
        )
    if (
        max_object_height_mm > 0
        and max_pocket_depth_mm > 0
        and max_pocket_depth_mm < max_object_height_mm * 0.5
    ):
        plan.warnings.append(
            f"Poche de {max_pocket_depth_mm:.0f} mm pour un objet de "
            f"{max_object_height_mm:.0f} mm : maintien partiel "
            "(< 50 % de la hauteur), vérifiez la stabilité."
        )
    return plan


def _assign_roles(
    combo: list[float],
    needed_cut_mm: float,
    min_bottom_floor_mm: float,
) -> list[FoamLayer] | None:
    """Affecte les rôles à une combinaison d'épaisseurs (ou None si inapte).

    Stratégie : choisir le plus petit sous-ensemble de couches CUTOUT
    couvrant la profondeur nécessaire, le fond le plus fin satisfaisant
    le minimum, le reste en SPACER. Les couches découpées sont placées
    en haut : la couche supérieure est toujours découpée.
    """
    thicknesses = sorted(combo, reverse=True)  # grandes couches → découpe

    # Couches découpées : les plus épaisses d'abord, jusqu'à couvrir le besoin.
    cutout: list[float] = []
    remaining = list(thicknesses)
    for t in thicknesses:
        if sum(cutout) >= needed_cut_mm and cutout:
            break
        cutout.append(t)
        remaining.remove(t)
    if needed_cut_mm > 0 and sum(cutout) < needed_cut_mm:
        return None
    if not cutout:
        # Aucune poche demandée : au moins une couche reste découpable.
        if remaining:
            cutout.append(remaining.pop(0))
        else:
            return None

    # Fond : il faut au moins min_bottom dans les couches restantes.
    if min_bottom_floor_mm > 0 and sum(remaining) < min_bottom_floor_mm:
        return None
    bottom = sorted(remaining)  # du fond vers le haut
    if min_bottom_floor_mm > 0 and not bottom:
        return None
    return (
        [FoamLayer(t, LayerRole.BOTTOM) for t in bottom[:1]]
        + [FoamLayer(t, LayerRole.SPACER) for t in bottom[1:]]
        + [FoamLayer(t, LayerRole.CUTOUT) for t in sorted(cutout)]
    )


def _score(layers: list[FoamLayer], preferred_count: int | None) -> float:
    """Note un empilement (plus petit = meilleur).

    Critères : nombre de couches proche du souhait (ou minimal), peu de
    couches de compensation, profondeur découpable sans excès inutile.
    """
    count = len(layers)
    spacers = sum(1 for l in layers if l.role is LayerRole.SPACER)
    score = count * 10.0 + spacers * 5.0
    if preferred_count is not None:
        score += abs(count - preferred_count) * 100.0
    return score


# ---------------------------------------------------------------------- #
# Découpe par couche (export multi-couches)
# ---------------------------------------------------------------------- #
@dataclass
class LayerCut:
    """Ce qu'une poche découpe dans UNE couche CUTOUT donnée."""

    through: bool          # la découpe traverse toute la couche
    depth_in_layer_mm: float  # profondeur entamée dans cette couche


def pocket_cuts_per_layer(
    plan: LayerPlan, pocket_depth_mm: float
) -> list[LayerCut]:
    """Répartit une poche sur les couches CUTOUT (de la surface vers le bas).

    Exemple : poche de 30 mm sur deux couches de 20 mm →
    [LayerCut(through=True, 20), LayerCut(through=False, 10)].
    """
    cuts: list[LayerCut] = []
    remaining = max(pocket_depth_mm, 0.0)
    for layer in plan.cutout_layers_top_down():
        if remaining <= 0:
            cuts.append(LayerCut(through=False, depth_in_layer_mm=0.0))
            continue
        if remaining >= layer.thickness_mm - 1e-6:
            cuts.append(
                LayerCut(through=True, depth_in_layer_mm=layer.thickness_mm)
            )
            remaining -= layer.thickness_mm
        else:
            cuts.append(LayerCut(through=False, depth_in_layer_mm=remaining))
            remaining = 0.0
    return cuts


# ---------------------------------------------------------------------- #
# Affectation objet par objet (chaque couche sait ce qu'elle découpe)
# ---------------------------------------------------------------------- #
@dataclass
class ShapeLayerCut:
    """Ce qu'UNE forme découpe dans UNE couche donnée."""

    shape_id: str
    through: bool             # traverse toute l'épaisseur de la couche
    depth_in_layer_mm: float  # profondeur entamée dans cette couche
    is_surface: bool = False  # gravure/texte : surface uniquement


@dataclass
class LayerAssignment:
    """Une couche de la pile et la liste exacte de ses découpes."""

    index: int                # 1 = couche du fond, croissant vers le haut
    layer: FoamLayer
    z_bottom_mm: float        # altitude du bas de la couche (0 = fond)
    cuts: list[ShapeLayerCut] = field(default_factory=list)

    @property
    def z_top_mm(self) -> float:
        return self.z_bottom_mm + self.layer.thickness_mm


def compute_layer_assignments(
    plan: LayerPlan, shapes: Sequence["object"]
) -> list[LayerAssignment]:
    """Calcule, objet par objet, ce que chaque couche doit découper.

    - une poche traverse les couches CUTOUT entièrement couvertes par sa
      profondeur, puis entame partiellement la suivante ;
    - une découpe complète (``CutType.FULL``) traverse TOUTES les couches
      CUTOUT ;
    - gravures et textes ne marquent que la surface de la couche CUTOUT
      supérieure ;
    - les couches BOTTOM/SPACER/SUPPORT ne reçoivent jamais de découpe.

    Retourne une affectation par couche, du fond vers le haut, avec les
    altitudes (z) de chaque couche pour les vues 3D/éclatée.
    """
    from foamforge.core.geometry import CutType, ShapeKind

    assignments: list[LayerAssignment] = []
    z = 0.0
    for index, layer in enumerate(plan.layers, start=1):
        assignments.append(LayerAssignment(index, layer, z))
        z += layer.thickness_mm

    cutout_top_down = [
        a for a in reversed(assignments)
        if a.layer.role is LayerRole.CUTOUT
    ]
    if not cutout_top_down:
        return assignments

    top_cutout = cutout_top_down[0]
    for shape in shapes:
        spec = shape.spec
        if shape.kind is ShapeKind.TEXT or spec.cut_type == CutType.ENGRAVE:
            top_cutout.cuts.append(
                ShapeLayerCut(shape.id, through=False,
                              depth_in_layer_mm=min(spec.depth_mm, 2.0),
                              is_surface=True)
            )
            continue
        if spec.cut_type == CutType.FULL:
            for assignment in cutout_top_down:
                assignment.cuts.append(
                    ShapeLayerCut(
                        shape.id, through=True,
                        depth_in_layer_mm=assignment.layer.thickness_mm,
                    )
                )
            continue
        # Poche : répartition selon la profondeur demandée.
        for assignment, cut in zip(
            cutout_top_down, pocket_cuts_per_layer(plan, spec.depth_mm)
        ):
            if cut.depth_in_layer_mm <= 0:
                continue
            assignment.cuts.append(
                ShapeLayerCut(shape.id, through=cut.through,
                              depth_in_layer_mm=cut.depth_in_layer_mm)
            )
    return assignments
