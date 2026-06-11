"""Export SVG pour découpe laser.

Produit un SVG en unités millimètres réelles (``width="...mm"`` +
``viewBox`` 1 unité = 1 mm), structuré en groupes ``<g id="CALQUE">``
suivant la convention de calques de :mod:`foamforge.export`. Les tracés
sont des chemins fermés sans remplissage, trait fin, directement
exploitables par LightBurn, Inkscape ou un pilote laser.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from shapely.geometry import Polygon

from foamforge.core.geometry import CutType, Shape, ShapeKind, TextShape
from foamforge.core.project import Project
from foamforge.core.units import clean
from foamforge.export import (
    LAYER_COLORS,
    LAYER_CUT_FULL,
    LAYER_CUT_POCKET,
    LAYER_ENGRAVE,
    LAYER_FOAM_BORDER,
    LAYER_REFERENCE,
    LAYER_TEXT,
)

_SVG_NS = "http://www.w3.org/2000/svg"

_CUT_LAYER = {
    CutType.FULL: LAYER_CUT_FULL,
    CutType.POCKET: LAYER_CUT_POCKET,
    CutType.ENGRAVE: LAYER_ENGRAVE,
}


def _ring_to_path(coords) -> str:
    """Convertit un anneau de coordonnées en données de chemin SVG."""
    points = [f"{clean(x)},{clean(y)}" for x, y in coords]
    return "M " + " L ".join(points) + " Z"


def polygon_path_data(polygon: Polygon) -> str:
    """Chemin SVG d'un polygone, trous inclus (règle evenodd)."""
    data = _ring_to_path(polygon.exterior.coords)
    for interior in polygon.interiors:
        data += " " + _ring_to_path(interior.coords)
    return data


def _add_polygon(group: ET.Element, polygon: Polygon, color: str) -> ET.Element:
    path = ET.SubElement(group, "path")
    path.set("d", polygon_path_data(polygon))
    path.set("fill", "none")
    path.set("stroke", color)
    path.set("stroke-width", "0.2")
    return path


def _add_reference_cross(
    group: ET.Element, x: float, y: float, size_mm: float = 5.0
) -> None:
    """Croix de repérage pour le calage machine."""
    color = LAYER_COLORS[LAYER_REFERENCE]
    for x1, y1, x2, y2 in (
        (x - size_mm, y, x + size_mm, y),
        (x, y - size_mm, x, y + size_mm),
    ):
        line = ET.SubElement(group, "line")
        line.set("x1", str(clean(x1)))
        line.set("y1", str(clean(y1)))
        line.set("x2", str(clean(x2)))
        line.set("y2", str(clean(y2)))
        line.set("stroke", color)
        line.set("stroke-width", "0.2")


def export_svg(project: Project, path: str | Path) -> Path:
    """Écrit le fichier SVG du projet et retourne son chemin."""
    sheet = project.sheet
    root = ET.Element("svg")
    root.set("xmlns", _SVG_NS)
    root.set("width", f"{clean(sheet.width_mm)}mm")
    root.set("height", f"{clean(sheet.height_mm)}mm")
    root.set("viewBox", f"0 0 {clean(sheet.width_mm)} {clean(sheet.height_mm)}")

    title = ET.SubElement(root, "title")
    title.text = f"FoamForge — {project.name}"

    groups: dict[str, ET.Element] = {}

    def layer(name: str) -> ET.Element:
        if name not in groups:
            group = ET.SubElement(root, "g")
            group.set("id", name)
            groups[name] = group
        return groups[name]

    # Contour de la plaque.
    _add_polygon(
        layer(LAYER_FOAM_BORDER),
        sheet.polygon(),
        LAYER_COLORS[LAYER_FOAM_BORDER],
    )

    # Découpes, dans l'ordre de découpe défini par l'utilisateur.
    for shape in sorted(project.shapes, key=lambda s: s.spec.cut_order):
        if shape.kind is ShapeKind.TEXT:
            _add_text(layer(LAYER_TEXT), shape)  # type: ignore[arg-type]
            continue
        layer_name = _CUT_LAYER[shape.spec.cut_type]
        element = _add_polygon(
            layer(layer_name), shape.cut_polygon(), LAYER_COLORS[layer_name]
        )
        # Métadonnées utiles à l'opérateur (info-bulle dans les éditeurs SVG).
        info = ET.SubElement(element, "title")
        info.text = (
            f"{shape.spec.name} — {shape.spec.cut_type.label}, "
            f"profondeur {shape.spec.depth_mm:.1f} mm, "
            f"ordre {shape.spec.cut_order}"
        )

    # Repères de calage aux quatre coins de la plaque.
    ref = layer(LAYER_REFERENCE)
    for x in (0.0, sheet.width_mm):
        for y in (0.0, sheet.height_mm):
            _add_reference_cross(ref, x, y)

    path = Path(path)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return path


def _add_text(group: ET.Element, shape: TextShape) -> None:
    """Texte gravé : élément ``<text>`` vectorisable par l'outil laser."""
    element = ET.SubElement(group, "text")
    element.set("x", str(clean(shape.x_mm)))
    element.set("y", str(clean(shape.y_mm)))
    element.set("font-size", str(clean(shape.font_height_mm)))
    element.set("font-family", "sans-serif")
    element.set("text-anchor", "middle")
    element.set("dominant-baseline", "central")
    element.set("fill", LAYER_COLORS[LAYER_TEXT])
    if shape.rotation_deg:
        element.set(
            "transform",
            f"rotate({clean(shape.rotation_deg)} "
            f"{clean(shape.x_mm)} {clean(shape.y_mm)})",
        )
    element.text = shape.text
