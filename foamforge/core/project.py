"""Modèle de projet FoamForge et persistance JSON.

Un projet décrit la valise (dimensions intérieures), l'empilement de
couches de mousse et la liste des logements (formes + paramètres de
découpe). Le format de fichier est un JSON versionné, lisible et
diffable, avec l'extension ``.foamforge.json``.

Schéma v2 (FoamForge 0.2) : dimensions intérieures de valise nommées,
épaisseurs de mousse disponibles, empilement de couches calculé, hauteur
réelle des objets. Les fichiers v1 sont migrés automatiquement à
l'ouverture (voir :func:`_migrate_v1_to_v2`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shapely.geometry import Polygon, box

from foamforge.core.geometry import Shape, shape_from_dict
from foamforge.core.layers import FoamLayer, LayerPlan, LayerRole

FILE_EXTENSION = ".foamforge.json"
SCHEMA_VERSION = 2

# Épaisseurs de plaques couramment disponibles dans le commerce (mm).
DEFAULT_FOAM_THICKNESSES = [10.0, 20.0, 30.0, 40.0, 50.0]

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
    # Valise de destination : DIMENSIONS INTÉRIEURES utiles, en mm.
    case_name: str = ""               # marque/modèle de la valise
    case_width_mm: float = 420.0      # largeur intérieure
    case_height_mm: float = 320.0     # hauteur (profondeur du plan) intérieure
    case_depth_mm: float = 160.0      # profondeur intérieure (axe vertical)
    # Plaque de mousse (surface de travail du canvas = intérieur utile).
    sheet: FoamSheet = field(default_factory=FoamSheet)
    layer_count: int = 1
    foam_type: str = FOAM_TYPES[0]
    foam_color: str = "#1a1a1a"        # mousse noire par défaut
    background_color: str = "#b3261e"  # fond rouge : objets manquants visibles
    # Empilement de couches (FoamLayerPlanner) — vide = mono-plaque.
    available_foam_thicknesses_mm: list[float] = field(
        default_factory=lambda: list(DEFAULT_FOAM_THICKNESSES)
    )
    foam_layers: list[FoamLayer] = field(default_factory=list)
    min_bottom_floor_mm: float = 10.0  # fond minimal souhaité sous les poches
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
    # Couches de mousse
    # ------------------------------------------------------------------ #
    def layer_plan(self) -> LayerPlan:
        """Empilement courant sous forme de plan (sans recalcul)."""
        plan = LayerPlan()
        plan.layers = list(self.foam_layers)
        return plan

    def cuttable_depth_mm(self) -> float:
        """Profondeur découpable : somme des couches CUTOUT, ou l'épaisseur
        de la plaque unique si aucun empilement n'est défini."""
        if self.foam_layers:
            return sum(
                layer.thickness_mm
                for layer in self.foam_layers
                if layer.role is LayerRole.CUTOUT
            )
        return self.sheet.thickness_mm

    def max_pocket_depth_mm(self) -> float:
        """Poche la plus profonde du projet (gravures exclues)."""
        from foamforge.core.geometry import CutType

        depths = [
            s.spec.depth_mm
            for s in self.shapes
            if s.spec.cut_type != CutType.ENGRAVE
        ]
        return max(depths, default=0.0)

    def max_object_height_mm(self) -> float:
        """Objet le plus haut (hauteurs réelles mesurées renseignées)."""
        return max(
            (s.spec.object_height_mm for s in self.shapes), default=0.0
        )

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
                "name": self.case_name,
                "internal_width_mm": self.case_width_mm,
                "internal_height_mm": self.case_height_mm,
                "internal_depth_mm": self.case_depth_mm,
            },
            "sheet": self.sheet.to_dict(),
            "layer_count": self.layer_count,
            "foam_type": self.foam_type,
            "foam_color": self.foam_color,
            "background_color": self.background_color,
            "available_foam_thicknesses_mm": list(
                self.available_foam_thicknesses_mm
            ),
            "foam_layers": [layer.to_dict() for layer in self.foam_layers],
            "min_bottom_floor_mm": self.min_bottom_floor_mm,
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
        if version < 2:
            data = _migrate_v1_to_v2(data)
        case = data.get("case", {})
        project = cls(
            name=data.get("name", "Projet"),
            case_name=case.get("name", ""),
            case_width_mm=float(case.get("internal_width_mm", 420.0)),
            case_height_mm=float(case.get("internal_height_mm", 320.0)),
            case_depth_mm=float(case.get("internal_depth_mm", 160.0)),
            sheet=FoamSheet.from_dict(data.get("sheet", {})),
            layer_count=int(data.get("layer_count", 1)),
            foam_type=data.get("foam_type", FOAM_TYPES[0]),
            foam_color=data.get("foam_color", "#1a1a1a"),
            background_color=data.get("background_color", "#b3261e"),
            available_foam_thicknesses_mm=[
                float(t)
                for t in data.get(
                    "available_foam_thicknesses_mm", DEFAULT_FOAM_THICKNESSES
                )
            ],
            foam_layers=[
                FoamLayer.from_dict(layer)
                for layer in data.get("foam_layers", [])
            ],
            min_bottom_floor_mm=float(data.get("min_bottom_floor_mm", 10.0)),
            min_spacing_mm=float(data.get("min_spacing_mm", 8.0)),
            min_border_mm=float(data.get("min_border_mm", 12.0)),
            grid_step_mm=float(data.get("grid_step_mm", 1.0)),
            notes=data.get("notes", ""),
        )
        for shape_data in data.get("shapes", []):
            project.shapes.append(shape_from_dict(shape_data))
        return project

    @property
    def schema_version(self) -> int:
        return SCHEMA_VERSION

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


# ---------------------------------------------------------------------- #
# Migrations de schéma
# ---------------------------------------------------------------------- #
def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """Migre un dictionnaire de projet v1 vers la structure v2.

    v1 stockait la valise sous ``case.width_mm/height_mm/depth_mm`` ; v2
    nomme explicitement les dimensions intérieures et ajoute les champs
    d'empilement de couches (vides : l'ancienne plaque unique reste le
    comportement par défaut).
    """
    migrated = dict(data)
    old_case = data.get("case", {})
    migrated["case"] = {
        "name": old_case.get("name", ""),
        "internal_width_mm": old_case.get("width_mm", 420.0),
        "internal_height_mm": old_case.get("height_mm", 320.0),
        "internal_depth_mm": old_case.get("depth_mm", 160.0),
    }
    migrated.setdefault(
        "available_foam_thicknesses_mm", list(DEFAULT_FOAM_THICKNESSES)
    )
    migrated.setdefault("foam_layers", [])
    migrated.setdefault("min_bottom_floor_mm", 10.0)
    migrated["schema_version"] = 2
    return migrated
