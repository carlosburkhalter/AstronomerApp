"""Contrôles de sécurité de la conception.

Analyse automatiquement le projet et produit des alertes hiérarchisées :

- ``ERROR``   (rouge)  : problème bloquant pour la fabrication ;
- ``WARNING`` (orange) : amélioration recommandée ;
- ``OK``      (vert)   : conception valide.

Les contrôles couvrent : profondeur vs épaisseur, distance au bord,
distance entre découpes (parois trop fines = risque de déchirure),
chevauchements, débordements, et répartition du poids si renseigné.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations

from foamforge.core.geometry import CutType, Shape, ShapeKind, center_of_mass
from foamforge.core.project import Project


class Severity(Enum):
    """Gravité d'une alerte (couleur associée côté UI)."""

    ERROR = "error"      # rouge : bloquant
    WARNING = "warning"  # orange : recommandation
    OK = "ok"            # vert : valide

    @property
    def color(self) -> str:
        return {
            Severity.ERROR: "#d32f2f",
            Severity.WARNING: "#ef6c00",
            Severity.OK: "#2e7d32",
        }[self]


@dataclass
class Issue:
    """Alerte produite par la validation."""

    severity: Severity
    code: str
    message: str
    shape_ids: list[str] = field(default_factory=list)


def _label(shape: Shape) -> str:
    return f"« {shape.spec.name} »"


def validate_project(project: Project) -> list[Issue]:
    """Exécute tous les contrôles et retourne la liste des alertes.

    Si aucune erreur ni avertissement n'est détecté, une unique alerte
    verte « conception valide » est retournée.
    """
    issues: list[Issue] = []
    foam = project.foam_polygon()
    # Les textes gravés ne créent pas de parois fragiles : on les exclut
    # des contrôles de distance mais on vérifie qu'ils restent sur la plaque.
    cuts = [s for s in project.shapes if s.kind is not ShapeKind.TEXT]
    texts = [s for s in project.shapes if s.kind is ShapeKind.TEXT]

    issues += _check_depths(project)
    issues += _check_object_heights(project)
    issues += _check_layer_plan(project)
    issues += _check_corner_radius(cuts)
    issues += _check_inside_sheet(foam, cuts + texts)
    issues += _check_border_distance(project, foam, cuts)
    issues += _check_pairwise_distance(project, cuts)
    issues += _check_weight_balance(project, cuts)

    if not issues:
        issues.append(
            Issue(
                Severity.OK,
                "valid",
                "Conception valide : aucun problème détecté.",
            )
        )
    return issues


# ---------------------------------------------------------------------- #
# Contrôles individuels
# ---------------------------------------------------------------------- #
def _check_depths(project: Project) -> list[Issue]:
    """Profondeurs de poche cohérentes avec la mousse découpable."""
    issues: list[Issue] = []
    # Avec un empilement de couches : somme des couches découpées ;
    # sinon : épaisseur de la plaque unique.
    cuttable = project.cuttable_depth_mm()
    for shape in project.shapes:
        spec = shape.spec
        if spec.cut_type == CutType.POCKET and spec.depth_mm > cuttable:
            issues.append(
                Issue(
                    Severity.ERROR,
                    "depth_exceeds_thickness",
                    f"{_label(shape)} : profondeur de poche "
                    f"{spec.depth_mm:.1f} mm > mousse découpable "
                    f"{cuttable:.1f} mm.",
                    [shape.id],
                )
            )
        elif spec.cut_type == CutType.POCKET and spec.depth_mm > cuttable - 5:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "thin_floor",
                    f"{_label(shape)} : fond de poche < 5 mm "
                    f"({cuttable - spec.depth_mm:.1f} mm restant), "
                    "zone fragile sous l'objet.",
                    [shape.id],
                )
            )
    return issues


def _check_object_heights(project: Project) -> list[Issue]:
    """Hauteur réelle des objets vs profondeur intérieure de la valise.

    La hauteur de l'objet n'est PAS la profondeur de poche : un objet de
    80 mm peut être maintenu par une poche de 35 mm. On contrôle donc :
    objet plus haut que la valise (erreur) et poche trop faible pour un
    maintien correct (avertissement).
    """
    issues: list[Issue] = []
    case_depth = project.case_depth_mm
    for shape in project.shapes:
        spec = shape.spec
        height = spec.object_height_mm
        if height <= 0:
            continue  # hauteur non mesurée : rien à contrôler
        if height > case_depth:
            issues.append(
                Issue(
                    Severity.ERROR,
                    "object_taller_than_case",
                    f"{_label(shape)} : objet de {height:.0f} mm pour une "
                    f"valise de {case_depth:.0f} mm de profondeur "
                    "intérieure — la valise ne fermera pas.",
                    [shape.id],
                )
            )
        elif (
            spec.cut_type == CutType.POCKET
            and spec.depth_mm < height * 0.5
        ):
            issues.append(
                Issue(
                    Severity.WARNING,
                    "pocket_shallow_for_object",
                    f"{_label(shape)} : poche de {spec.depth_mm:.0f} mm pour "
                    f"un objet de {height:.0f} mm (< 50 % de maintien) — "
                    "l'objet risque de bouger.",
                    [shape.id],
                )
            )
    return issues


def _check_layer_plan(project: Project) -> list[Issue]:
    """Cohérence de l'empilement de couches s'il est défini."""
    if not project.foam_layers:
        return []
    issues: list[Issue] = []
    total = sum(layer.thickness_mm for layer in project.foam_layers)
    if abs(total - project.case_depth_mm) > 0.05:
        issues.append(
            Issue(
                Severity.ERROR,
                "layers_mismatch_depth",
                f"L'empilement de couches totalise {total:.1f} mm pour une "
                f"profondeur intérieure de {project.case_depth_mm:.1f} mm : "
                "recalculez les couches.",
            )
        )
    return issues


def _check_corner_radius(cuts: list[Shape]) -> list[Issue]:
    """Rayon d'arrondi applicable : trop grand pour la géométrie = repli.

    L'arrondi est appliqué par ouverture morphologique ; quand le rayon
    dépasse la demi-largeur de la forme, le moteur retombe proprement sur
    la géométrie non arrondie (l'objet ne disparaît jamais), mais
    l'utilisateur doit en être informé : l'export ne correspondra pas à
    son intention.
    """
    issues: list[Issue] = []
    for shape in cuts:
        if not shape.corner_radius_applied():
            issues.append(
                Issue(
                    Severity.WARNING,
                    "corner_radius_too_large",
                    f"{_label(shape)} : rayon d'arrondi de "
                    f"{shape.spec.corner_radius_mm:.1f} mm trop grand pour "
                    "cette géométrie — les angles resteront vifs. "
                    "Réduisez le rayon.",
                    [shape.id],
                )
            )
    return issues


def _check_inside_sheet(foam, shapes: list[Shape]) -> list[Issue]:
    """Aucune découpe ne doit déborder de la plaque."""
    issues: list[Issue] = []
    for shape in shapes:
        if not foam.contains(shape.cut_polygon()):
            issues.append(
                Issue(
                    Severity.ERROR,
                    "outside_sheet",
                    f"{_label(shape)} dépasse de la plaque de mousse.",
                    [shape.id],
                )
            )
    return issues


def _check_border_distance(
    project: Project, foam, cuts: list[Shape]
) -> list[Issue]:
    """Paroi minimale entre chaque découpe et le bord de la plaque."""
    issues: list[Issue] = []
    minimum = project.min_border_mm
    border = foam.exterior
    for shape in cuts:
        poly = shape.cut_polygon()
        if not foam.contains(poly):
            continue  # déjà signalé en erreur "outside_sheet"
        dist = poly.distance(border)
        if dist < minimum / 2:
            issues.append(
                Issue(
                    Severity.ERROR,
                    "border_too_close",
                    f"{_label(shape)} est à {dist:.1f} mm du bord "
                    f"(paroi critique, minimum {minimum:.0f} mm) : "
                    "risque de déchirure.",
                    [shape.id],
                )
            )
        elif dist < minimum:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "border_close",
                    f"{_label(shape)} est à {dist:.1f} mm du bord "
                    f"(recommandé : {minimum:.0f} mm).",
                    [shape.id],
                )
            )
    return issues


def _check_pairwise_distance(
    project: Project, cuts: list[Shape]
) -> list[Issue]:
    """Paroi minimale entre découpes : zones trop fines et chevauchements."""
    issues: list[Issue] = []
    minimum = project.min_spacing_mm
    polygons = {s.id: s.cut_polygon() for s in cuts}
    for a, b in combinations(cuts, 2):
        pa, pb = polygons[a.id], polygons[b.id]
        if pa.intersects(pb):
            issues.append(
                Issue(
                    Severity.ERROR,
                    "overlap",
                    f"{_label(a)} et {_label(b)} se chevauchent.",
                    [a.id, b.id],
                )
            )
            continue
        dist = pa.distance(pb)
        if dist < minimum / 2:
            issues.append(
                Issue(
                    Severity.ERROR,
                    "wall_too_thin",
                    f"Paroi de {dist:.1f} mm entre {_label(a)} et "
                    f"{_label(b)} (minimum {minimum:.0f} mm) : "
                    "zone trop fine, risque de déchirure.",
                    [a.id, b.id],
                )
            )
        elif dist < minimum:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "wall_thin",
                    f"Paroi de {dist:.1f} mm entre {_label(a)} et "
                    f"{_label(b)} (recommandé : {minimum:.0f} mm).",
                    [a.id, b.id],
                )
            )
    return issues


# Au-delà de ce ratio d'excentrement du centre de masse (par rapport à la
# demi-dimension de la plaque), la valise risque d'être déséquilibrée.
_BALANCE_RATIO_WARNING = 0.25


def _check_weight_balance(project: Project, cuts: list[Shape]) -> list[Issue]:
    """Répartition du poids si les poids des objets sont renseignés."""
    com = center_of_mass(cuts)
    if com is None:
        return []
    cx, cy, total = com
    sheet = project.sheet
    offset_x = abs(cx - sheet.width_mm / 2) / (sheet.width_mm / 2)
    offset_y = abs(cy - sheet.height_mm / 2) / (sheet.height_mm / 2)
    worst = max(offset_x, offset_y)
    if worst > _BALANCE_RATIO_WARNING:
        return [
            Issue(
                Severity.WARNING,
                "weight_unbalanced",
                f"Poids mal réparti : centre de masse ({cx:.0f}, {cy:.0f}) mm "
                f"décalé de {worst * 100:.0f} % du centre de la plaque "
                f"(total {total:.0f} g). Rapprochez les objets lourds du centre.",
                [s.id for s in cuts if s.spec.weight_g > 0],
            )
        ]
    return []


def worst_severity(issues: list[Issue]) -> Severity:
    """Gravité globale d'une liste d'alertes (pour le feu tricolore UI)."""
    if any(i.severity is Severity.ERROR for i in issues):
        return Severity.ERROR
    if any(i.severity is Severity.WARNING for i in issues):
        return Severity.WARNING
    return Severity.OK
