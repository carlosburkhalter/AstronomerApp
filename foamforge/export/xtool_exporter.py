"""Export pour xTool P2S (et profils machine similaires).

Produit des SVG « machine-ready » pour xTool Creative Space :

- dimensions physiques exactes en mm (``width=".."mm`` + viewBox 1:1) ;
- chemins fermés, aucune transformation ambiguë ;
- groupes nommés par fonction (CUT_FULL, CUT_POCKET, ENGRAVE, TEXT...) ;
- compensation de kerf optionnelle (le faisceau retire de la matière :
  on rétracte les contours de kerf/2 pour des logements à la cote) ;
- contrôle de la surface utile machine ;
- export par couche de mousse si un empilement est défini : chaque
  couche CUTOUT reçoit uniquement les découpes qui la traversent ou
  l'entament, les couches pleines (fond/compensation/couvercle) ne
  reçoivent que le contour de plaque.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from foamforge.core.geometry import CutType, Shape, ShapeKind, TextShape
from foamforge.core.layers import LayerPlan, LayerRole, pocket_cuts_per_layer
from foamforge.core.project import Project
from foamforge.export import (
    LAYER_CUT_FULL,
    LAYER_CUT_POCKET,
    LAYER_FOAM_BORDER,
)
from foamforge.export.svg_exporter import (
    CUT_LAYER_BY_TYPE,
    SvgPolygonEntry,
    SvgTextEntry,
    write_svg_document,
)


@dataclass(frozen=True)
class MachineProfile:
    """Profil d'une machine de découpe laser."""

    name: str
    bed_width_mm: float
    bed_height_mm: float
    kerf_mm: float = 0.0          # largeur du trait de coupe (0 = ignorer)
    stroke_width_mm: float = 0.1  # trait fin attendu par le logiciel machine


# Surface utile du xTool P2S (laser CO2 55 W) : 600 × 308 mm.
XTOOL_P2S = MachineProfile(
    name="xTool P2S",
    bed_width_mm=600.0,
    bed_height_mm=308.0,
    kerf_mm=0.0,
    stroke_width_mm=0.1,
)


class MachineExportError(Exception):
    """Projet incompatible avec le profil machine."""


def check_fits_machine(project: Project, profile: MachineProfile) -> None:
    """Vérifie que la plaque tient dans la surface utile de la machine."""
    sheet = project.sheet
    fits_normal = (
        sheet.width_mm <= profile.bed_width_mm
        and sheet.height_mm <= profile.bed_height_mm
    )
    fits_rotated = (
        sheet.height_mm <= profile.bed_width_mm
        and sheet.width_mm <= profile.bed_height_mm
    )
    if not fits_normal and not fits_rotated:
        raise MachineExportError(
            f"La plaque ({sheet.width_mm:.0f} × {sheet.height_mm:.0f} mm) "
            f"dépasse la surface utile du {profile.name} "
            f"({profile.bed_width_mm:.0f} × {profile.bed_height_mm:.0f} mm). "
            "Découpez en plusieurs plaques ou réduisez la mousse."
        )


def _kerf_compensated(polygon, kerf_mm: float):
    """Compense le trait de coupe : le faisceau élargit chaque ouverture
    de kerf/2 par côté, on rétracte donc le tracé d'autant. Si la forme
    est trop petite pour la compensation, on garde le tracé nominal."""
    if kerf_mm <= 0:
        return polygon
    compensated = polygon.buffer(-kerf_mm / 2.0, quad_segs=16)
    if compensated.is_empty or compensated.geom_type != "Polygon":
        return polygon
    return compensated


def _shape_entry(
    shape: Shape, profile: MachineProfile,
    layer_override: str | None = None,
    depth_note: str | None = None,
) -> SvgPolygonEntry | SvgTextEntry:
    if shape.kind is ShapeKind.TEXT:
        assert isinstance(shape, TextShape)
        return SvgTextEntry(
            text=shape.text,
            x_mm=shape.x_mm,
            y_mm=shape.y_mm,
            font_height_mm=shape.font_height_mm,
            rotation_deg=shape.rotation_deg,
        )
    layer = layer_override or CUT_LAYER_BY_TYPE[shape.spec.cut_type]
    polygon = shape.cut_polygon()
    # La compensation de kerf ne s'applique qu'aux vraies découpes.
    if layer in (LAYER_CUT_FULL, LAYER_CUT_POCKET):
        polygon = _kerf_compensated(polygon, profile.kerf_mm)
    tooltip = f"{shape.spec.name} — ordre {shape.spec.cut_order}"
    if depth_note:
        tooltip += f" — {depth_note}"
    return SvgPolygonEntry(polygon=polygon, layer=layer, tooltip=tooltip)


def export_xtool_svg(
    project: Project,
    path: str | Path,
    profile: MachineProfile = XTOOL_P2S,
) -> Path:
    """Export SVG global prêt pour xTool Creative Space."""
    check_fits_machine(project, profile)
    sheet = project.sheet
    entries: list[SvgPolygonEntry | SvgTextEntry] = [
        SvgPolygonEntry(sheet.polygon(), LAYER_FOAM_BORDER)
    ]
    for shape in sorted(project.shapes, key=lambda s: s.spec.cut_order):
        entries.append(_shape_entry(shape, profile))
    return write_svg_document(
        sheet.width_mm,
        sheet.height_mm,
        entries,
        path,
        title=f"FoamForge — {project.name} — {profile.name}",
        stroke_width_mm=profile.stroke_width_mm,
    )


# ---------------------------------------------------------------------- #
# Export par couche de mousse
# ---------------------------------------------------------------------- #
def _layer_file_name(base: str, index: int, role: LayerRole) -> str:
    return f"{base}_LAYER_{index:02d}_{role.value.upper()}.svg"


def export_layers_svg(
    project: Project,
    directory: str | Path,
    profile: MachineProfile = XTOOL_P2S,
    base_name: str | None = None,
) -> list[Path]:
    """Exporte un SVG par couche de mousse de l'empilement.

    Répartition des découpes (poches mesurées depuis la surface du bloc
    découpable, sous l'éventuel couvercle) :

    - une poche traverse entièrement une couche → tracé sur ``CUT_FULL`` ;
    - une poche entame partiellement une couche → ``CUT_POCKET`` avec la
      profondeur restante annotée ;
    - une découpe ``FULL`` du projet traverse toutes les couches CUTOUT ;
    - gravures et textes vont sur la couche CUTOUT supérieure uniquement ;
    - les couches BOTTOM/SPACER/LID ne contiennent que le contour plaque.

    Retourne la liste des fichiers écrits (ordre : du fond vers le haut).
    """
    plan: LayerPlan = project.layer_plan()
    if not plan.layers:
        raise MachineExportError(
            "Aucun empilement de couches défini : utilisez « Calculer les "
            "couches » avant l'export par couche."
        )
    check_fits_machine(project, profile)

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    base = base_name or project.name.replace(" ", "_")
    sheet = project.sheet
    shapes = sorted(project.shapes, key=lambda s: s.spec.cut_order)

    # Index (dans la pile complète, du fond vers le haut) des couches CUTOUT,
    # puis ordre surface → fond pour la répartition des poches.
    cutout_indices_top_down = [
        i for i, layer in reversed(list(enumerate(plan.layers)))
        if layer.role is LayerRole.CUTOUT
    ]

    # Préparation des entrées par couche de la pile.
    entries_per_layer: list[list[SvgPolygonEntry | SvgTextEntry]] = [
        [SvgPolygonEntry(sheet.polygon(), LAYER_FOAM_BORDER)]
        for _ in plan.layers
    ]

    top_cutout = cutout_indices_top_down[0] if cutout_indices_top_down else None
    for shape in shapes:
        if shape.kind is ShapeKind.TEXT or shape.spec.cut_type == CutType.ENGRAVE:
            # Gravures et textes : surface de la couche découpable du haut.
            if top_cutout is not None:
                entries_per_layer[top_cutout].append(
                    _shape_entry(shape, profile)
                )
            continue
        if shape.spec.cut_type == CutType.FULL:
            # Découpe complète : traverse toutes les couches découpables.
            for index in cutout_indices_top_down:
                entries_per_layer[index].append(
                    _shape_entry(shape, profile, layer_override=LAYER_CUT_FULL)
                )
            continue
        # Poche : répartition selon la profondeur.
        cuts = pocket_cuts_per_layer(plan, shape.spec.depth_mm)
        for index, cut in zip(cutout_indices_top_down, cuts):
            if cut.depth_in_layer_mm <= 0:
                continue
            if cut.through:
                entries_per_layer[index].append(
                    _shape_entry(shape, profile, layer_override=LAYER_CUT_FULL,
                                 depth_note="traversante dans cette couche")
                )
            else:
                entries_per_layer[index].append(
                    _shape_entry(
                        shape, profile, layer_override=LAYER_CUT_POCKET,
                        depth_note=(
                            f"poche de {cut.depth_in_layer_mm:.1f} mm "
                            "dans cette couche"
                        ),
                    )
                )

    written: list[Path] = []
    for index, (layer, entries) in enumerate(
        zip(plan.layers, entries_per_layer), start=1
    ):
        file_path = directory / _layer_file_name(base, index, layer.role)
        write_svg_document(
            sheet.width_mm,
            sheet.height_mm,
            entries,
            file_path,
            title=(
                f"FoamForge — {project.name} — couche {index} "
                f"({layer.role.label}, {layer.thickness_mm:.0f} mm)"
            ),
            stroke_width_mm=profile.stroke_width_mm,
        )
        written.append(file_path)
    return written
