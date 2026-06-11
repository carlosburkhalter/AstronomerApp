"""Export DXF pour CNC / laser industriel (via ezdxf).

Produit un DXF R2010 en millimètres (``$INSUNITS = 4``), avec un calque
par fonction (convention :mod:`foamforge.export`). Les contours sont des
LWPOLYLINE fermées, les textes des entités TEXT sur le calque ``TEXT``.

Note repère : le canvas FoamForge utilise un axe Y vers le bas (convention
écran), le DXF un axe Y vers le haut (convention machine). L'export
retourne donc la géométrie verticalement pour que la pièce sorte à
l'endroit sur la machine.
"""

from __future__ import annotations

from pathlib import Path

import ezdxf
from ezdxf.document import Drawing
from shapely.geometry import Polygon

from foamforge.core.geometry import CutType, ShapeKind, TextShape
from foamforge.core.project import Project
from foamforge.core.units import clean
from foamforge.export import (
    LAYER_CUT_FULL,
    LAYER_CUT_POCKET,
    LAYER_ENGRAVE,
    LAYER_FOAM_BORDER,
    LAYER_REFERENCE,
    LAYER_TEXT,
)

# Couleurs ACI (AutoCAD Color Index) par calque.
_LAYER_ACI = {
    LAYER_FOAM_BORDER: 7,   # blanc/noir
    LAYER_CUT_FULL: 1,      # rouge
    LAYER_CUT_POCKET: 5,    # bleu
    LAYER_ENGRAVE: 3,       # vert
    LAYER_TEXT: 6,          # magenta
    LAYER_REFERENCE: 8,     # gris
}

_CUT_LAYER = {
    CutType.FULL: LAYER_CUT_FULL,
    CutType.POCKET: LAYER_CUT_POCKET,
    CutType.ENGRAVE: LAYER_ENGRAVE,
}


def _new_document() -> Drawing:
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    for name, color in _LAYER_ACI.items():
        doc.layers.add(name, color=color)
    return doc


def _add_polygon(
    msp, polygon: Polygon, layer: str, sheet_height_mm: float
) -> None:
    """Ajoute un polygone (extérieur + trous) en LWPOLYLINE fermées."""
    rings = [polygon.exterior, *polygon.interiors]
    for ring in rings:
        points = [
            (clean(x), clean(sheet_height_mm - y)) for x, y in ring.coords
        ]
        msp.add_lwpolyline(points, close=True, dxfattribs={"layer": layer})


def export_dxf(project: Project, path: str | Path) -> Path:
    """Écrit le fichier DXF du projet et retourne son chemin."""
    doc = _new_document()
    msp = doc.modelspace()
    sheet = project.sheet
    height = sheet.height_mm

    # Contour de la plaque.
    _add_polygon(msp, sheet.polygon(), LAYER_FOAM_BORDER, height)

    # Découpes dans l'ordre défini.
    for shape in sorted(project.shapes, key=lambda s: s.spec.cut_order):
        if shape.kind is ShapeKind.TEXT:
            _add_text(msp, shape, height)  # type: ignore[arg-type]
            continue
        layer = _CUT_LAYER[shape.spec.cut_type]
        _add_polygon(msp, shape.cut_polygon(), layer, height)

    # Croix de repérage aux coins.
    for x in (0.0, sheet.width_mm):
        for y in (0.0, height):
            machine_y = height - y
            msp.add_line(
                (x - 5, machine_y),
                (x + 5, machine_y),
                dxfattribs={"layer": LAYER_REFERENCE},
            )
            msp.add_line(
                (x, machine_y - 5),
                (x, machine_y + 5),
                dxfattribs={"layer": LAYER_REFERENCE},
            )

    path = Path(path)
    doc.saveas(path)
    return path


def _add_text(msp, shape: TextShape, sheet_height_mm: float) -> None:
    text = msp.add_text(
        shape.text,
        height=shape.font_height_mm,
        rotation=-shape.rotation_deg,  # inversion d'axe Y → angle opposé
        dxfattribs={"layer": LAYER_TEXT},
    )
    text.set_placement(
        (clean(shape.x_mm), clean(sheet_height_mm - shape.y_mm)),
        align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER,
    )
