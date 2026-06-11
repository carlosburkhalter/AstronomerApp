"""Export SVG pour découpe laser.

Produit un SVG en unités millimètres réelles (``width="...mm"`` +
``viewBox`` 1 unité = 1 mm), structuré en groupes ``<g id="CALQUE">``
suivant la convention de calques de :mod:`foamforge.export`. Les tracés
sont des chemins fermés sans remplissage, trait fin, directement
exploitables par LightBurn, xTool Creative Space, Inkscape ou un pilote
laser.

Le cœur (:func:`write_svg_document`) est partagé avec l'export xTool et
l'export par couche : il prend une liste d'entrées (polygone ou texte +
calque) et écrit un document propre, sans transformation ambiguë.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from shapely.geometry import Polygon

from foamforge.core.geometry import CutType, ShapeKind, TextShape
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

CUT_LAYER_BY_TYPE = {
    CutType.FULL: LAYER_CUT_FULL,
    CutType.POCKET: LAYER_CUT_POCKET,
    CutType.ENGRAVE: LAYER_ENGRAVE,
}


@dataclass
class SvgPolygonEntry:
    """Un contour à tracer sur un calque donné."""

    polygon: Polygon
    layer: str
    tooltip: str = ""


@dataclass
class SvgTextEntry:
    """Un texte gravé."""

    text: str
    x_mm: float
    y_mm: float
    font_height_mm: float
    rotation_deg: float = 0.0
    layer: str = LAYER_TEXT


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


def _add_reference_crosses(
    group: ET.Element, width_mm: float, height_mm: float, size_mm: float = 5.0
) -> None:
    """Croix de repérage aux quatre coins, pour le calage machine."""
    color = LAYER_COLORS[LAYER_REFERENCE]
    for x in (0.0, width_mm):
        for y in (0.0, height_mm):
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


def write_svg_document(
    width_mm: float,
    height_mm: float,
    entries: list[SvgPolygonEntry | SvgTextEntry],
    path: str | Path,
    title: str,
    stroke_width_mm: float = 0.2,
    with_references: bool = True,
) -> Path:
    """Écrit un document SVG propre (mm réels, calques nommés, chemins
    fermés, aucune transformation sauf la rotation des textes)."""
    root = ET.Element("svg")
    root.set("xmlns", _SVG_NS)
    root.set("width", f"{clean(width_mm)}mm")
    root.set("height", f"{clean(height_mm)}mm")
    root.set("viewBox", f"0 0 {clean(width_mm)} {clean(height_mm)}")
    title_el = ET.SubElement(root, "title")
    title_el.text = title

    groups: dict[str, ET.Element] = {}

    def layer(name: str) -> ET.Element:
        if name not in groups:
            group = ET.SubElement(root, "g")
            group.set("id", name)
            groups[name] = group
        return groups[name]

    for entry in entries:
        if isinstance(entry, SvgPolygonEntry):
            element = ET.SubElement(layer(entry.layer), "path")
            element.set("d", polygon_path_data(entry.polygon))
            element.set("fill", "none")
            element.set("fill-rule", "evenodd")
            element.set("stroke", LAYER_COLORS.get(entry.layer, "#000000"))
            element.set("stroke-width", str(clean(stroke_width_mm)))
            if entry.tooltip:
                info = ET.SubElement(element, "title")
                info.text = entry.tooltip
        else:
            element = ET.SubElement(layer(entry.layer), "text")
            element.set("x", str(clean(entry.x_mm)))
            element.set("y", str(clean(entry.y_mm)))
            element.set("font-size", str(clean(entry.font_height_mm)))
            element.set("font-family", "sans-serif")
            element.set("text-anchor", "middle")
            element.set("dominant-baseline", "central")
            element.set("fill", LAYER_COLORS.get(entry.layer, "#000000"))
            if entry.rotation_deg:
                element.set(
                    "transform",
                    f"rotate({clean(entry.rotation_deg)} "
                    f"{clean(entry.x_mm)} {clean(entry.y_mm)})",
                )
            element.text = entry.text

    if with_references:
        _add_reference_crosses(layer(LAYER_REFERENCE), width_mm, height_mm)

    path = Path(path)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return path


def project_entries(
    project: Project,
) -> list[SvgPolygonEntry | SvgTextEntry]:
    """Entrées SVG de toutes les découpes du projet (plaque comprise)."""
    entries: list[SvgPolygonEntry | SvgTextEntry] = [
        SvgPolygonEntry(project.sheet.polygon(), LAYER_FOAM_BORDER)
    ]
    for shape in sorted(project.shapes, key=lambda s: s.spec.cut_order):
        if shape.kind is ShapeKind.TEXT:
            assert isinstance(shape, TextShape)
            entries.append(
                SvgTextEntry(
                    text=shape.text,
                    x_mm=shape.x_mm,
                    y_mm=shape.y_mm,
                    font_height_mm=shape.font_height_mm,
                    rotation_deg=shape.rotation_deg,
                )
            )
            continue
        entries.append(
            SvgPolygonEntry(
                polygon=shape.cut_polygon(),
                layer=CUT_LAYER_BY_TYPE[shape.spec.cut_type],
                tooltip=(
                    f"{shape.spec.name} — {shape.spec.cut_type.label}, "
                    f"profondeur {shape.spec.depth_mm:.1f} mm, "
                    f"ordre {shape.spec.cut_order}"
                ),
            )
        )
    return entries


def export_svg(project: Project, path: str | Path) -> Path:
    """Écrit le fichier SVG du projet et retourne son chemin."""
    return write_svg_document(
        project.sheet.width_mm,
        project.sheet.height_mm,
        project_entries(project),
        path,
        title=f"FoamForge — {project.name}",
    )
