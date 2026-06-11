"""Modèle de projet FoamForge et persistance JSON.

Un projet décrit la valise, la plaque de mousse (dimensions, épaisseur,
nombre de couches, type) et la liste des logements (formes + paramètres
de découpe). Le format de fichier est un JSON versionné, lisible et
diffable, avec l'extension ``.foamforge.json``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shapely.geometry import Polygon, box

from foamforge.core.geometry import Shape, shape_from_dict

FILE_EXTENSION = ".foamforge.json"
SCHEMA_VERSION = 1

# Types de mousse proposés par défaut (extensible côté UI).
FOAM_TYPES = [
    "Polyéthylène (PE)",
    "Polyuréthane (PU)",
    "EVA",
    "XLPE réticulé",
    "Plastazote",
]


@dataclass
class FoamSheet:
    """Plaque de mousse à découper."""

    width_mm: float = 400.0
    height_mm: float = 300.0
    thickness_mm: float = 50.0

    def polygon(self) -> Polygon:
        """Contour extérieur de la plaque, origine au coin haut-gauche."""
        return box(0.0, 0.0, self.width_mm, self.height_mm)

    def to_dict(self) -> dict[str, Any]:
        return {
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "thickness_mm": self.thickness_mm,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FoamSheet":
        return cls(
            width_mm=float(data.get("width_mm", 400.0)),
            height_mm=float(data.get("height_mm", 300.0)),
            thickness_mm=float(data.get("thickness_mm", 50.0)),
        )


@dataclass
class Project:
    """Projet de mousse de protection."""

    name: str = "Nouveau projet"
    # Valise de destination (information / contrôle de cohérence).
    case_width_mm: float = 420.0
    case_height_mm: float = 320.0
    case_depth_mm: float = 160.0
    # Plaque de mousse.
    sheet: FoamSheet = field(default_factory=FoamSheet)
    layer_count: int = 1
    foam_type: str = FOAM_TYPES[0]
    foam_color: str = "#1a1a1a"        # mousse noire par défaut
    background_color: str = "#b3261e"  # fond rouge : objets manquants visibles
    # Règles de sécurité (mode expert : ajustables).
    min_spacing_mm: float = 8.0   # paroi minimale entre deux découpes
    min_border_mm: float = 12.0   # paroi minimale avec le bord de la plaque
    grid_step_mm: float = 1.0     # pas du magnétisme
    notes: str = ""
    shapes: list[Shape] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Gestion des formes
    # ------------------------------------------------------------------ #
    def add_shape(self, shape: Shape) -> None:
        if shape.spec.cut_order <= 0:
            shape.spec.cut_order = self.next_cut_order()
        self.shapes.append(shape)

    def remove_shape(self, shape_id: str) -> None:
        self.shapes = [s for s in self.shapes if s.id != shape_id]

    def get_shape(self, shape_id: str) -> Shape | None:
        for shape in self.shapes:
            if shape.id == shape_id:
                return shape
        return None

    def next_cut_order(self) -> int:
        return max((s.spec.cut_order for s in self.shapes), default=0) + 1

    def foam_polygon(self) -> Polygon:
        return self.sheet.polygon()

    # ------------------------------------------------------------------ #
    # Checklist (la mousse sert aussi à ne rien oublier)
    # ------------------------------------------------------------------ #
    def checklist_items(self) -> list[str]:
        """Noms des objets attendus dans la valise, dans l'ordre de découpe.

        Les textes gravés sont des étiquettes, pas des objets à emporter.
        """
        cuts = [s for s in self.shapes if s.kind.value != "text"]
        cuts.sort(key=lambda s: s.spec.cut_order)
        return [s.spec.name for s in cuts]

    # ------------------------------------------------------------------ #
    # Persistance
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "case": {
                "width_mm": self.case_width_mm,
                "height_mm": self.case_height_mm,
                "depth_mm": self.case_depth_mm,
            },
            "sheet": self.sheet.to_dict(),
            "layer_count": self.layer_count,
            "foam_type": self.foam_type,
            "foam_color": self.foam_color,
            "background_color": self.background_color,
            "min_spacing_mm": self.min_spacing_mm,
            "min_border_mm": self.min_border_mm,
            "grid_step_mm": self.grid_step_mm,
            "notes": self.notes,
            "shapes": [s.to_dict() for s in self.shapes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        version = int(data.get("schema_version", 1))
        if version > SCHEMA_VERSION:
            raise ValueError(
                f"Fichier créé par une version plus récente de FoamForge "
                f"(schéma {version} > {SCHEMA_VERSION})."
            )
        case = data.get("case", {})
        project = cls(
            name=data.get("name", "Projet"),
            case_width_mm=float(case.get("width_mm", 420.0)),
            case_height_mm=float(case.get("height_mm", 320.0)),
            case_depth_mm=float(case.get("depth_mm", 160.0)),
            sheet=FoamSheet.from_dict(data.get("sheet", {})),
            layer_count=int(data.get("layer_count", 1)),
            foam_type=data.get("foam_type", FOAM_TYPES[0]),
            foam_color=data.get("foam_color", "#1a1a1a"),
            background_color=data.get("background_color", "#b3261e"),
            min_spacing_mm=float(data.get("min_spacing_mm", 8.0)),
            min_border_mm=float(data.get("min_border_mm", 12.0)),
            grid_step_mm=float(data.get("grid_step_mm", 1.0)),
            notes=data.get("notes", ""),
        )
        for shape_data in data.get("shapes", []):
            project.shapes.append(shape_from_dict(shape_data))
        return project

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)
