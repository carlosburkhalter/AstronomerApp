"""Bibliothèque d'objets : CRUD, recherche, import/export, réutilisation.

Chaque objet de la bibliothèque (caméra, oculaire, batterie...) mémorise
ses dimensions, son poids, son contour 2D éventuel et les paramètres de
découpe recommandés. Il peut être instancié dans n'importe quel projet
via :meth:`LibraryObject.to_shape`.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from foamforge.core.geometry import (
    CutoutSpec,
    CutType,
    PolygonShape,
    RectShape,
    Shape,
)


@dataclass
class LibraryObject:
    """Objet réutilisable de la bibliothèque."""

    name: str
    category: str = ""
    brand: str = ""
    width_mm: float = 0.0
    height_mm: float = 0.0
    depth_mm: float = 0.0
    weight_g: float = 0.0
    # Contour 2D optionnel (sommets en mm, centrés sur l'origine).
    contour_mm: list[tuple[float, float]] | None = None
    recommended_depth_mm: float = 0.0
    recommended_margin_mm: float = 1.0
    tags: list[str] = field(default_factory=list)
    id: int | None = None

    def to_shape(self, x_mm: float = 0.0, y_mm: float = 0.0) -> Shape:
        """Instancie l'objet en forme de projet, prêt à placer."""
        spec = CutoutSpec(
            name=self.name,
            depth_mm=self.recommended_depth_mm or self.depth_mm or 30.0,
            margin_mm=self.recommended_margin_mm,
            cut_type=CutType.POCKET,
            weight_g=self.weight_g,
        )
        if self.contour_mm:
            return PolygonShape(
                points_mm=list(self.contour_mm), x_mm=x_mm, y_mm=y_mm, spec=spec
            )
        return RectShape(
            width_mm=self.width_mm or 50.0,
            height_mm=self.height_mm or 50.0,
            x_mm=x_mm,
            y_mm=y_mm,
            spec=spec,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "brand": self.brand,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "depth_mm": self.depth_mm,
            "weight_g": self.weight_g,
            "contour_mm": (
                [list(p) for p in self.contour_mm] if self.contour_mm else None
            ),
            "recommended_depth_mm": self.recommended_depth_mm,
            "recommended_margin_mm": self.recommended_margin_mm,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LibraryObject":
        contour = data.get("contour_mm")
        return cls(
            name=data["name"],
            category=data.get("category", ""),
            brand=data.get("brand", ""),
            width_mm=float(data.get("width_mm", 0.0)),
            height_mm=float(data.get("height_mm", 0.0)),
            depth_mm=float(data.get("depth_mm", 0.0)),
            weight_g=float(data.get("weight_g", 0.0)),
            contour_mm=[tuple(p) for p in contour] if contour else None,
            recommended_depth_mm=float(data.get("recommended_depth_mm", 0.0)),
            recommended_margin_mm=float(data.get("recommended_margin_mm", 1.0)),
            tags=list(data.get("tags", [])),
        )


class ObjectLibrary:
    """Accès à la bibliothèque d'objets stockée en SQLite."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    # ------------------------------------------------------------------ #
    # Catégories
    # ------------------------------------------------------------------ #
    def categories(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT name FROM categories ORDER BY name"
        ).fetchall()
        return [row["name"] for row in rows]

    def _category_id(self, name: str) -> int | None:
        if not name:
            return None
        self._conn.execute(
            "INSERT OR IGNORE INTO categories(name) VALUES (?)", (name,)
        )
        row = self._conn.execute(
            "SELECT id FROM categories WHERE name = ?", (name,)
        ).fetchone()
        return row["id"]

    # ------------------------------------------------------------------ #
    # CRUD objets
    # ------------------------------------------------------------------ #
    def add(self, obj: LibraryObject) -> LibraryObject:
        cursor = self._conn.execute(
            """
            INSERT INTO objects(
                name, brand, category_id, width_mm, height_mm, depth_mm,
                weight_g, contour_json, recommended_depth_mm,
                recommended_margin_mm, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obj.name,
                obj.brand,
                self._category_id(obj.category),
                obj.width_mm,
                obj.height_mm,
                obj.depth_mm,
                obj.weight_g,
                json.dumps(obj.contour_mm) if obj.contour_mm else None,
                obj.recommended_depth_mm,
                obj.recommended_margin_mm,
                ",".join(obj.tags),
            ),
        )
        self._conn.commit()
        obj.id = cursor.lastrowid
        return obj

    def update(self, obj: LibraryObject) -> None:
        if obj.id is None:
            raise ValueError("Objet sans identifiant : utilisez add().")
        self._conn.execute(
            """
            UPDATE objects SET
                name = ?, brand = ?, category_id = ?, width_mm = ?,
                height_mm = ?, depth_mm = ?, weight_g = ?, contour_json = ?,
                recommended_depth_mm = ?, recommended_margin_mm = ?, tags = ?
            WHERE id = ?
            """,
            (
                obj.name,
                obj.brand,
                self._category_id(obj.category),
                obj.width_mm,
                obj.height_mm,
                obj.depth_mm,
                obj.weight_g,
                json.dumps(obj.contour_mm) if obj.contour_mm else None,
                obj.recommended_depth_mm,
                obj.recommended_margin_mm,
                ",".join(obj.tags),
                obj.id,
            ),
        )
        self._conn.commit()

    def delete(self, object_id: int) -> None:
        self._conn.execute("DELETE FROM objects WHERE id = ?", (object_id,))
        self._conn.commit()

    def get(self, object_id: int) -> LibraryObject | None:
        row = self._conn.execute(
            "SELECT o.*, c.name AS category FROM objects o "
            "LEFT JOIN categories c ON c.id = o.category_id WHERE o.id = ?",
            (object_id,),
        ).fetchone()
        return self._row_to_object(row) if row else None

    def search(
        self, text: str = "", category: str = ""
    ) -> list[LibraryObject]:
        """Recherche par texte (nom, marque, tags) et/ou catégorie."""
        query = (
            "SELECT o.*, c.name AS category FROM objects o "
            "LEFT JOIN categories c ON c.id = o.category_id WHERE 1=1"
        )
        params: list[Any] = []
        if text:
            query += " AND (o.name LIKE ? OR o.brand LIKE ? OR o.tags LIKE ?)"
            like = f"%{text}%"
            params += [like, like, like]
        if category:
            query += " AND c.name = ?"
            params.append(category)
        query += " ORDER BY o.name"
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_object(row) for row in rows]

    @staticmethod
    def _row_to_object(row: sqlite3.Row) -> LibraryObject:
        contour = (
            [tuple(p) for p in json.loads(row["contour_json"])]
            if row["contour_json"]
            else None
        )
        return LibraryObject(
            id=row["id"],
            name=row["name"],
            brand=row["brand"],
            category=row["category"] or "",
            width_mm=row["width_mm"],
            height_mm=row["height_mm"],
            depth_mm=row["depth_mm"],
            weight_g=row["weight_g"],
            contour_mm=contour,
            recommended_depth_mm=row["recommended_depth_mm"],
            recommended_margin_mm=row["recommended_margin_mm"],
            tags=[t for t in row["tags"].split(",") if t],
        )

    # ------------------------------------------------------------------ #
    # Import / export (partage de bibliothèques entre utilisateurs)
    # ------------------------------------------------------------------ #
    def export_json(self, path: str | Path) -> Path:
        objects = [obj.to_dict() for obj in self.search()]
        path = Path(path)
        path.write_text(
            json.dumps({"foamforge_library": 1, "objects": objects},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def import_json(self, path: str | Path) -> int:
        """Importe une bibliothèque JSON ; retourne le nombre d'objets ajoutés."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        objects = data.get("objects", [])
        for obj_data in objects:
            self.add(LibraryObject.from_dict(obj_data))
        return len(objects)
