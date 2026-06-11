"""Tests des exports SVG, DXF, PNG, PDF et checklist HTML."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import ezdxf
import pytest

from foamforge.core.geometry import CircleShape, CutoutSpec, CutType, RectShape, TextShape
from foamforge.core.project import FoamSheet, Project
from foamforge.export import ALL_LAYERS, LAYER_CUT_FULL, LAYER_CUT_POCKET
from foamforge.export.dxf_exporter import export_dxf
from foamforge.export.pdf_exporter import export_checklist_html, export_pdf, export_png
from foamforge.export.svg_exporter import export_svg


@pytest.fixture
def project() -> Project:
    project = Project(
        name="Test export",
        sheet=FoamSheet(width_mm=400, height_mm=300, thickness_mm=50),
    )
    project.add_shape(RectShape(
        width_mm=100, height_mm=60, x_mm=100, y_mm=100,
        spec=CutoutSpec(name="Caméra", depth_mm=40,
                        cut_type=CutType.POCKET, corner_radius_mm=5),
    ))
    project.add_shape(CircleShape(
        diameter_mm=50, x_mm=300, y_mm=100,
        spec=CutoutSpec(name="Oculaire", cut_type=CutType.FULL),
    ))
    project.add_shape(TextShape(
        text="ASTRO", x_mm=200, y_mm=250, font_height_mm=10,
        spec=CutoutSpec(name="Étiquette"),
    ))
    return project


def test_svg_structure(project: Project, tmp_path: Path) -> None:
    path = export_svg(project, tmp_path / "out.svg")
    root = ET.parse(path).getroot()
    # Dimensions physiques en mm.
    assert root.get("width") == "400.0mm"
    assert root.get("viewBox") == "0 0 400.0 300.0"
    ns = {"svg": "http://www.w3.org/2000/svg"}
    group_ids = {g.get("id") for g in root.findall("svg:g", ns)}
    # Tous les calques utilisés sont présents et nommés selon la convention.
    assert group_ids <= set(ALL_LAYERS)
    assert LAYER_CUT_FULL in group_ids
    assert LAYER_CUT_POCKET in group_ids
    # Le texte gravé est exporté en élément <text>.
    texts = root.findall(".//svg:text", ns)
    assert any(t.text == "ASTRO" for t in texts)


def test_dxf_structure(project: Project, tmp_path: Path) -> None:
    path = export_dxf(project, tmp_path / "out.dxf")
    doc = ezdxf.readfile(path)
    assert doc.header["$INSUNITS"] == 4  # millimètres
    layer_names = {layer.dxf.name for layer in doc.layers}
    assert set(ALL_LAYERS) <= layer_names
    msp = doc.modelspace()
    polylines = msp.query("LWPOLYLINE")
    assert len(polylines) >= 3  # plaque + 2 découpes
    full_cuts = msp.query(f'LWPOLYLINE[layer=="{LAYER_CUT_FULL}"]')
    assert len(full_cuts) == 1
    texts = msp.query("TEXT")
    assert any(t.dxf.text == "ASTRO" for t in texts)


def test_dxf_geometry_in_machine_coordinates(
    project: Project, tmp_path: Path
) -> None:
    """L'axe Y est retourné : la découpe FULL (cercle) centrée en
    (300, 100) écran doit être en (300, 200) machine."""
    path = export_dxf(project, tmp_path / "out.dxf")
    doc = ezdxf.readfile(path)
    cut = doc.modelspace().query(
        f'LWPOLYLINE[layer=="{LAYER_CUT_FULL}"]'
    )[0]
    xs = [p[0] for p in cut.get_points()]
    ys = [p[1] for p in cut.get_points()]
    assert (min(xs) + max(xs)) / 2 == pytest.approx(300, abs=0.1)
    assert (min(ys) + max(ys)) / 2 == pytest.approx(200, abs=0.1)


def test_png_and_pdf(project: Project, tmp_path: Path) -> None:
    png = export_png(project, tmp_path / "out.png")
    pdf = export_pdf(project, tmp_path / "out.pdf")
    assert png.stat().st_size > 1000
    assert pdf.read_bytes()[:5] == b"%PDF-"


def test_checklist_html(project: Project, tmp_path: Path) -> None:
    path = export_checklist_html(project, tmp_path / "checklist.html")
    content = path.read_text(encoding="utf-8")
    assert "Caméra" in content
    assert "Oculaire" in content
    # Les textes gravés ne sont pas des objets à emporter.
    assert "Étiquette" not in content
    assert 'type="checkbox"' in content
