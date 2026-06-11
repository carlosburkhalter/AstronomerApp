"""Tests de l'export xTool P2S et de l'export par couche."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from foamforge.core.geometry import (
    CircleShape,
    CutoutSpec,
    CutType,
    RectShape,
    TextShape,
)
from foamforge.core.layers import FoamLayer, LayerRole
from foamforge.core.project import FoamSheet, Project
from foamforge.export import LAYER_CUT_FULL, LAYER_CUT_POCKET, LAYER_FOAM_BORDER
from foamforge.export.xtool_exporter import (
    XTOOL_P2S,
    MachineExportError,
    MachineProfile,
    check_fits_machine,
    export_layers_svg,
    export_xtool_svg,
)

_NS = {"svg": "http://www.w3.org/2000/svg"}


def _layered_project() -> Project:
    """Valise 120 mm : fond 20, deux couches découpées de 40, couvercle 20.

    - une poche de 30 mm (entame seulement la couche du haut) ;
    - une poche de 60 mm (traverse la couche du haut, 20 mm dans la 2e) ;
    - une découpe complète (traverse les deux couches découpées) ;
    - un texte gravé (surface de la couche du haut uniquement).
    """
    project = Project(
        name="Valise lunette",
        case_depth_mm=120.0,
        sheet=FoamSheet(width_mm=500, height_mm=300, thickness_mm=80),
        foam_layers=[
            FoamLayer(20.0, LayerRole.BOTTOM),
            FoamLayer(40.0, LayerRole.CUTOUT),
            FoamLayer(40.0, LayerRole.CUTOUT),
            FoamLayer(20.0, LayerRole.LID),
        ],
    )
    project.add_shape(RectShape(
        width_mm=100, height_mm=60, x_mm=100, y_mm=100,
        spec=CutoutSpec(name="Poche 30", depth_mm=30),
    ))
    project.add_shape(RectShape(
        width_mm=100, height_mm=60, x_mm=280, y_mm=100,
        spec=CutoutSpec(name="Poche 60", depth_mm=60),
    ))
    project.add_shape(CircleShape(
        diameter_mm=60, x_mm=420, y_mm=100,
        spec=CutoutSpec(name="Traversante", cut_type=CutType.FULL),
    ))
    project.add_shape(TextShape(
        text="LUNETTE", x_mm=250, y_mm=250,
        spec=CutoutSpec(name="Étiquette"),
    ))
    return project


def _paths_in_layer(svg_path: Path, layer: str) -> list[ET.Element]:
    root = ET.parse(svg_path).getroot()
    group = root.find(f"svg:g[@id='{layer}']", _NS)
    return [] if group is None else group.findall("svg:path", _NS)


# ---------------------------------------------------------------------- #
# Profil machine et SVG global
# ---------------------------------------------------------------------- #
def test_global_export_dimensions_and_layers(tmp_path: Path) -> None:
    project = _layered_project()
    path = export_xtool_svg(project, tmp_path / "xtool.svg")
    root = ET.parse(path).getroot()
    # Dimensions physiques exactes en mm, viewBox 1:1, pas de transform.
    assert root.get("width") == "500.0mm"
    assert root.get("height") == "300.0mm"
    assert root.get("viewBox") == "0 0 500.0 300.0"
    for element in root.iter():
        if element.tag.endswith("path"):
            assert element.get("transform") is None
            assert element.get("d", "").rstrip().endswith("Z")  # fermé
    group_ids = {g.get("id") for g in root.findall("svg:g", _NS)}
    assert {LAYER_FOAM_BORDER, LAYER_CUT_FULL, LAYER_CUT_POCKET} <= group_ids


def test_sheet_larger_than_bed_is_rejected(tmp_path: Path) -> None:
    project = _layered_project()
    project.sheet = FoamSheet(width_mm=700, height_mm=400, thickness_mm=80)
    with pytest.raises(MachineExportError, match="surface utile"):
        export_xtool_svg(project, tmp_path / "too_big.svg")


def test_rotated_fit_is_accepted() -> None:
    """Une plaque de 300 × 500 mm tient en pivotant (lit 600 × 308)."""
    project = _layered_project()
    project.sheet = FoamSheet(width_mm=300, height_mm=500, thickness_mm=80)
    check_fits_machine(project, XTOOL_P2S)  # ne doit pas lever


def test_kerf_compensation_shrinks_cuts(tmp_path: Path) -> None:
    project = Project(sheet=FoamSheet(400, 300, 50))
    project.add_shape(CircleShape(
        diameter_mm=50, x_mm=200, y_mm=150,
        spec=CutoutSpec(name="Rond", margin_mm=0, cut_type=CutType.FULL),
    ))
    profile = MachineProfile("kerf-test", 600, 308, kerf_mm=0.4)
    path = export_xtool_svg(project, tmp_path / "kerf.svg", profile)
    cut = _paths_in_layer(path, LAYER_CUT_FULL)[0]
    xs = [
        float(token.split(",")[0])
        for token in cut.get("d").replace("M ", "").replace("Z", "").split(" L ")
    ]
    # Diamètre tracé = 50 - kerf : le faisceau rendra l'ouverture à 50.
    assert max(xs) - min(xs) == pytest.approx(50 - 0.4, abs=0.05)


# ---------------------------------------------------------------------- #
# Export par couche
# ---------------------------------------------------------------------- #
def test_layer_files_naming_and_count(tmp_path: Path) -> None:
    project = _layered_project()
    files = export_layers_svg(project, tmp_path, base_name="valise_lunette")
    names = [f.name for f in files]
    assert names == [
        "valise_lunette_LAYER_01_BOTTOM.svg",
        "valise_lunette_LAYER_02_CUTOUT.svg",
        "valise_lunette_LAYER_03_CUTOUT.svg",
        "valise_lunette_LAYER_04_LID.svg",
    ]


def test_layer_cut_distribution(tmp_path: Path) -> None:
    project = _layered_project()
    files = export_layers_svg(project, tmp_path, base_name="v")
    bottom, cut_low, cut_top, lid = files

    # Couches pleines : uniquement le contour de plaque.
    for plain in (bottom, lid):
        assert len(_paths_in_layer(plain, LAYER_FOAM_BORDER)) == 1
        assert not _paths_in_layer(plain, LAYER_CUT_FULL)
        assert not _paths_in_layer(plain, LAYER_CUT_POCKET)

    # Couche découpée supérieure (3e fichier) : poche 30 → partielle ;
    # poche 60 → traversante ; découpe FULL → traversante. Total :
    # 2 FULL + 1 POCKET, plus le texte gravé.
    assert len(_paths_in_layer(cut_top, LAYER_CUT_FULL)) == 2
    assert len(_paths_in_layer(cut_top, LAYER_CUT_POCKET)) == 1
    root = ET.parse(cut_top).getroot()
    texts = root.findall(".//svg:text", _NS)
    assert any(t.text == "LUNETTE" for t in texts)

    # Couche découpée inférieure (2e fichier) : poche 60 → 20 mm restants
    # (partielle) ; découpe FULL → traversante ; poche 30 absente ;
    # pas de texte.
    assert len(_paths_in_layer(cut_low, LAYER_CUT_FULL)) == 1
    assert len(_paths_in_layer(cut_low, LAYER_CUT_POCKET)) == 1
    assert not ET.parse(cut_low).getroot().findall(".//svg:text", _NS)


def test_layer_export_requires_plan(tmp_path: Path) -> None:
    project = Project()  # pas d'empilement défini
    project.add_shape(RectShape(width_mm=50, height_mm=50, x_mm=100, y_mm=100))
    with pytest.raises(MachineExportError, match="Calculer les couches"):
        export_layers_svg(project, tmp_path)
