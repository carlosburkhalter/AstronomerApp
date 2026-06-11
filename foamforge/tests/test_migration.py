"""Tests de migration de schéma v1 → v2 et round-trip v2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from foamforge.core.geometry import CutoutSpec, RectShape
from foamforge.core.layers import FoamLayer, LayerRole
from foamforge.core.project import (
    DEFAULT_FOAM_THICKNESSES,
    Project,
    SCHEMA_VERSION,
)

# Extrait fidèle d'un fichier produit par FoamForge 0.1 (schéma v1).
_V1_DOCUMENT = {
    "schema_version": 1,
    "name": "Projet hérité",
    "case": {"width_mm": 460.0, "height_mm": 360.0, "depth_mm": 180.0},
    "sheet": {"width_mm": 440.0, "height_mm": 340.0, "thickness_mm": 60.0},
    "layer_count": 1,
    "foam_type": "Plastazote",
    "foam_color": "#1a1a1a",
    "background_color": "#b3261e",
    "min_spacing_mm": 8.0,
    "min_border_mm": 12.0,
    "grid_step_mm": 1.0,
    "notes": "ancien projet",
    "shapes": [
        {
            "id": "abc123def456",
            "kind": "rect",
            "x_mm": 100.0,
            "y_mm": 100.0,
            "rotation_deg": 0.0,
            "spec": {
                "name": "Caméra",
                "depth_mm": 45.0,
                "margin_mm": 2.0,
                "corner_radius_mm": 5.0,
                "cut_type": "pocket",
                "cut_order": 1,
                "comment": "",
                "weight_g": 700.0,
                # v1 : pas de object_height_mm ni creation_source
            },
            "geometry": {"width_mm": 90.0, "height_mm": 90.0},
        },
    ],
}


def test_v1_project_still_opens(tmp_path: Path) -> None:
    path = tmp_path / "legacy.foamforge.json"
    path.write_text(json.dumps(_V1_DOCUMENT), encoding="utf-8")
    project = Project.load(path)
    # Dimensions de valise migrées vers les champs « intérieurs ».
    assert project.case_width_mm == 460.0
    assert project.case_depth_mm == 180.0
    assert project.case_name == ""
    # Nouveaux champs avec valeurs par défaut sûres.
    assert project.available_foam_thicknesses_mm == DEFAULT_FOAM_THICKNESSES
    assert project.foam_layers == []
    assert project.min_bottom_floor_mm == 10.0
    # Formes intactes, nouveaux champs de spec par défaut.
    assert len(project.shapes) == 1
    shape = project.shapes[0]
    assert shape.spec.name == "Caméra"
    assert shape.spec.object_height_mm == 0.0
    assert shape.spec.creation_source == "manual"


def test_v1_resaved_as_v2(tmp_path: Path) -> None:
    path = tmp_path / "legacy.foamforge.json"
    path.write_text(json.dumps(_V1_DOCUMENT), encoding="utf-8")
    project = Project.load(path)
    out = tmp_path / "migrated.foamforge.json"
    project.save(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == SCHEMA_VERSION == 2
    assert data["case"]["internal_width_mm"] == 460.0
    # Et il se rouvre.
    assert Project.load(out).case_width_mm == 460.0


def test_v2_roundtrip_with_layers(tmp_path: Path) -> None:
    project = Project(
        name="Valise v2",
        case_name="Nanuk 935",
        case_depth_mm=120.0,
        available_foam_thicknesses_mm=[10.0, 20.0, 40.0],
        foam_layers=[
            FoamLayer(20.0, LayerRole.BOTTOM),
            FoamLayer(40.0, LayerRole.CUTOUT),
            FoamLayer(40.0, LayerRole.CUTOUT),
            FoamLayer(20.0, LayerRole.LID),
        ],
        min_bottom_floor_mm=15.0,
    )
    project.add_shape(RectShape(
        width_mm=80, height_mm=60, x_mm=100, y_mm=100,
        spec=CutoutSpec(name="Objet", depth_mm=50, object_height_mm=75,
                        creation_source="library"),
    ))
    path = tmp_path / "v2.foamforge.json"
    project.save(path)
    restored = Project.load(path)
    assert restored.to_dict() == project.to_dict()
    assert restored.case_name == "Nanuk 935"
    assert len(restored.foam_layers) == 4
    assert restored.foam_layers[1].role is LayerRole.CUTOUT
    assert restored.shapes[0].spec.object_height_mm == 75
    assert restored.cuttable_depth_mm() == pytest.approx(80)


def test_future_schema_still_rejected() -> None:
    with pytest.raises(ValueError, match="version plus récente"):
        Project.from_dict({"schema_version": 99})
