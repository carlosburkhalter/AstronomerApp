"""Modèle géométrique des formes de découpe.

Chaque logement (cutout) est décrit par :
- une forme de base (rectangle, cercle, ellipse, polygone, texte) centrée
  sur son origine locale ;
- une position / rotation dans le plan de la mousse ;
- une spécification de découpe (:class:`CutoutSpec`) : profondeur, marge,
  rayon d'arrondi, type de découpe, ordre, commentaire, poids.

La géométrie effective de découpe (marge + arrondis appliqués) est produite
par :meth:`Shape.cut_polygon` sous forme de polygone Shapely en mm.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Sequence

from shapely import affinity
from shapely.geometry import Point, Polygon, box

# Nombre de segments par quart de cercle pour les buffers Shapely.
# 32 donne une flèche < 0.01 mm pour des rayons usuels : suffisant pour laser.
_QUAD_SEGS = 32


class CutType(str, Enum):
    """Type de découpe d'un logement."""

    FULL = "full"        # découpe traversante
    POCKET = "pocket"    # poche partielle (profondeur < épaisseur)
    ENGRAVE = "engrave"  # gravure de surface

    @property
    def label(self) -> str:
        return {
            CutType.FULL: "Découpe complète",
            CutType.POCKET: "Poche partielle",
            CutType.ENGRAVE: "Gravure",
        }[self]


class ShapeKind(str, Enum):
    """Nature géométrique d'une forme."""

    RECT = "rect"
    CIRCLE = "circle"
    ELLIPSE = "ellipse"
    POLYGON = "polygon"
    TEXT = "text"


@dataclass
class CutoutSpec:
    """Paramètres de découpe d'un logement."""

    name: str = "Objet"
    depth_mm: float = 30.0
    margin_mm: float = 1.0          # tolérance ajoutée autour de l'objet
    corner_radius_mm: float = 0.0   # arrondi des angles convexes
    cut_type: CutType = CutType.POCKET
    cut_order: int = 0
    comment: str = ""
    weight_g: float = 0.0           # 0 = poids inconnu
    # Hauteur réelle mesurée de l'objet (≠ profondeur de poche !).
    # 0 = inconnue. Sert aux contrôles hauteur/valise et au plan de couches.
    object_height_mm: float = 0.0
    # Traçabilité : "manual", "library", "photo", "compound".
    creation_source: str = "manual"

    def __post_init__(self) -> None:
        # Auto-réparation : Qt (QVariant) et le JSON peuvent transformer
        # l'enum str CutType en chaîne pure ; on renormalise toujours.
        self.cut_type = CutType(self.cut_type)

    def cut_strategy(self) -> str:
        """Stratégie de maintien dérivée des paramètres.

        - ``through``         : découpe traversante ;
        - ``partial_support`` : poche moins profonde que l'objet
          (maintien partiel volontaire) ;
        - ``pocket``          : logement classique.
        """
        if self.cut_type == CutType.FULL:
            return "through"
        if 0 < self.object_height_mm and self.depth_mm < self.object_height_mm:
            return "partial_support"
        return "pocket"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "depth_mm": self.depth_mm,
            "margin_mm": self.margin_mm,
            "corner_radius_mm": self.corner_radius_mm,
            "cut_type": self.cut_type.value,
            "cut_order": self.cut_order,
            "comment": self.comment,
            "weight_g": self.weight_g,
            "object_height_mm": self.object_height_mm,
            "creation_source": self.creation_source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CutoutSpec":
        return cls(
            name=data.get("name", "Objet"),
            depth_mm=float(data.get("depth_mm", 30.0)),
            margin_mm=float(data.get("margin_mm", 1.0)),
            corner_radius_mm=float(data.get("corner_radius_mm", 0.0)),
            cut_type=CutType(data.get("cut_type", CutType.POCKET.value)),
            cut_order=int(data.get("cut_order", 0)),
            comment=data.get("comment", ""),
            weight_g=float(data.get("weight_g", 0.0)),
            object_height_mm=float(data.get("object_height_mm", 0.0)),
            creation_source=data.get("creation_source", "manual"),
        )


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Shape:
    """Forme positionnée dans le plan de la mousse (classe de base).

    ``x_mm`` / ``y_mm`` désignent le centre de la forme ; la rotation est
    appliquée autour de ce centre, en degrés, sens horaire à l'écran
    (axe Y vers le bas, convention écran).
    """

    x_mm: float = 0.0
    y_mm: float = 0.0
    rotation_deg: float = 0.0
    spec: CutoutSpec = field(default_factory=CutoutSpec)
    id: str = field(default_factory=_new_id)

    kind: ShapeKind = field(init=False, repr=False)

    # ------------------------------------------------------------------ #
    # Géométrie
    # ------------------------------------------------------------------ #
    def base_polygon(self) -> Polygon:
        """Polygone local, centré sur l'origine, sans marge ni rotation."""
        raise NotImplementedError

    def object_polygon(self) -> Polygon:
        """Polygone de l'objet (sans marge) placé dans le plan mousse."""
        poly = self.base_polygon()
        if self.rotation_deg:
            poly = affinity.rotate(poly, self.rotation_deg, origin=(0, 0))
        return affinity.translate(poly, self.x_mm, self.y_mm)

    def cut_polygon(self) -> Polygon:
        """Polygone réellement découpé : marge de tolérance + arrondis.

        - La marge est un offset extérieur (buffer) à jointures arrondies,
          fidèle à ce qu'attend un opérateur laser/CNC.
        - Le rayon d'arrondi est appliqué par ouverture morphologique
          (érosion puis dilatation) : seuls les angles convexes sont
          adoucis, le polygone reste inclus dans son offset d'origine.
        - Si le rayon est trop grand pour la géométrie, repli propre sur
          la version non arrondie : l'objet ne disparaît jamais
          (:meth:`corner_radius_applied` permet de le détecter pour
          avertir l'utilisateur).
        """
        poly = self.object_polygon()
        margin = max(self.spec.margin_mm, 0.0)
        if margin > 0:
            poly = poly.buffer(margin, quad_segs=_QUAD_SEGS, join_style="round")
        radius = max(self.spec.corner_radius_mm, 0.0)
        if radius > 0:
            opened = poly.buffer(-radius, quad_segs=_QUAD_SEGS).buffer(
                radius, quad_segs=_QUAD_SEGS
            )
            # Si la forme est trop petite pour le rayon demandé, on garde
            # la version non arrondie plutôt que de produire du vide.
            if not opened.is_empty and isinstance(opened, Polygon):
                poly = opened
        return poly

    def corner_radius_applied(self) -> bool:
        """Vrai si le rayon d'arrondi demandé est réellement applicable.

        Faux uniquement quand un rayon > 0 est demandé mais que la forme
        est trop petite (le moteur a dû replier sur les angles vifs).
        """
        radius = max(self.spec.corner_radius_mm, 0.0)
        if radius <= 0:
            return True
        poly = self.object_polygon()
        margin = max(self.spec.margin_mm, 0.0)
        if margin > 0:
            poly = poly.buffer(margin, quad_segs=_QUAD_SEGS, join_style="round")
        # Même condition exacte que le repli de cut_polygon() : vide OU
        # éclaté en plusieurs morceaux = rayon inapplicable.
        opened = poly.buffer(-radius, quad_segs=_QUAD_SEGS).buffer(
            radius, quad_segs=_QUAD_SEGS
        )
        return (not opened.is_empty) and isinstance(opened, Polygon)

    def bounds(self) -> tuple[float, float, float, float]:
        """Boîte englobante (minx, miny, maxx, maxy) de la découpe, en mm."""
        return self.cut_polygon().bounds

    # ------------------------------------------------------------------ #
    # Manipulation
    # ------------------------------------------------------------------ #
    def move_to(self, x_mm: float, y_mm: float) -> None:
        self.x_mm = x_mm
        self.y_mm = y_mm

    def duplicate(self, offset_mm: float = 10.0) -> "Shape":
        """Copie indépendante, décalée pour rester visible."""
        data = self.to_dict()
        data["id"] = _new_id()
        copy = shape_from_dict(data)
        copy.x_mm += offset_mm
        copy.y_mm += offset_mm
        copy.spec.name = f"{self.spec.name} (copie)"
        return copy

    # ------------------------------------------------------------------ #
    # Sérialisation
    # ------------------------------------------------------------------ #
    def _geometry_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "x_mm": self.x_mm,
            "y_mm": self.y_mm,
            "rotation_deg": self.rotation_deg,
            "spec": self.spec.to_dict(),
            "geometry": self._geometry_dict(),
        }


@dataclass
class RectShape(Shape):
    """Rectangle (logement le plus courant : boîtiers, batteries...)."""

    width_mm: float = 50.0
    height_mm: float = 30.0

    def __post_init__(self) -> None:
        self.kind = ShapeKind.RECT

    def base_polygon(self) -> Polygon:
        hw, hh = self.width_mm / 2.0, self.height_mm / 2.0
        return box(-hw, -hh, hw, hh)

    def _geometry_dict(self) -> dict[str, Any]:
        return {"width_mm": self.width_mm, "height_mm": self.height_mm}


@dataclass
class CircleShape(Shape):
    """Cercle (oculaires, objectifs, filtres...)."""

    diameter_mm: float = 40.0

    def __post_init__(self) -> None:
        self.kind = ShapeKind.CIRCLE

    def base_polygon(self) -> Polygon:
        return Point(0, 0).buffer(self.diameter_mm / 2.0, quad_segs=_QUAD_SEGS)

    def _geometry_dict(self) -> dict[str, Any]:
        return {"diameter_mm": self.diameter_mm}


@dataclass
class EllipseShape(Shape):
    """Ellipse (poignées, objets oblongs)."""

    width_mm: float = 60.0
    height_mm: float = 30.0

    def __post_init__(self) -> None:
        self.kind = ShapeKind.ELLIPSE

    def base_polygon(self) -> Polygon:
        circle = Point(0, 0).buffer(0.5, quad_segs=_QUAD_SEGS)
        return affinity.scale(circle, self.width_mm, self.height_mm, origin=(0, 0))

    def _geometry_dict(self) -> dict[str, Any]:
        return {"width_mm": self.width_mm, "height_mm": self.height_mm}


@dataclass
class PolygonShape(Shape):
    """Polygone libre : forme dessinée, contour photo ou forme composée.

    ``points_mm`` est la liste des sommets locaux, centrés sur l'origine.
    ``holes_mm`` contient les anneaux intérieurs (trous), par exemple après
    soustraction d'un cercle dans un rectangle (encoche fermée).
    """

    points_mm: list[tuple[float, float]] = field(default_factory=list)
    holes_mm: list[list[tuple[float, float]]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.kind = ShapeKind.POLYGON

    @classmethod
    def from_polygon(cls, polygon: Polygon, **kwargs: Any) -> "PolygonShape":
        """Crée la forme depuis un polygone Shapely (photo, fusion...).

        Le polygone est recentré sur son centroïde ; la position de la
        forme reprend le centroïde d'origine. Les trous sont conservés.
        """
        cx, cy = polygon.centroid.x, polygon.centroid.y
        pts = [(x - cx, y - cy) for x, y in polygon.exterior.coords[:-1]]
        holes = [
            [(x - cx, y - cy) for x, y in ring.coords[:-1]]
            for ring in polygon.interiors
        ]
        kwargs.setdefault("x_mm", cx)
        kwargs.setdefault("y_mm", cy)
        return cls(points_mm=pts, holes_mm=holes, **kwargs)

    def base_polygon(self) -> Polygon:
        if len(self.points_mm) < 3:
            # Polygone dégénéré : on retourne un point bufferisé minuscule
            # pour ne jamais casser la validation ni l'export.
            return Point(0, 0).buffer(0.5)
        poly = Polygon(
            self.points_mm,
            [hole for hole in self.holes_mm if len(hole) >= 3],
        )
        if not poly.is_valid:
            poly = poly.buffer(0)  # répare les auto-intersections
            if poly.geom_type == "MultiPolygon":
                poly = max(poly.geoms, key=lambda g: g.area)
        return poly

    def _geometry_dict(self) -> dict[str, Any]:
        return {
            "points_mm": [list(p) for p in self.points_mm],
            "holes_mm": [[list(p) for p in hole] for hole in self.holes_mm],
        }


# Largeur approximative d'un caractère par rapport à sa hauteur, pour
# estimer l'encombrement d'un texte gravé sans dépendre d'une fonte.
_TEXT_ASPECT = 0.62


@dataclass
class TextShape(Shape):
    """Texte gravé dans la mousse (étiquettes de logements)."""

    text: str = "TEXTE"
    font_height_mm: float = 10.0

    def __post_init__(self) -> None:
        self.kind = ShapeKind.TEXT
        # Un texte est toujours une gravure, sans marge de tolérance.
        self.spec.cut_type = CutType.ENGRAVE
        self.spec.margin_mm = 0.0

    def estimated_width_mm(self) -> float:
        return max(len(self.text), 1) * self.font_height_mm * _TEXT_ASPECT

    def base_polygon(self) -> Polygon:
        hw = self.estimated_width_mm() / 2.0
        hh = self.font_height_mm / 2.0
        return box(-hw, -hh, hw, hh)

    def _geometry_dict(self) -> dict[str, Any]:
        return {"text": self.text, "font_height_mm": self.font_height_mm}


# ---------------------------------------------------------------------- #
# Fabrique de désérialisation
# ---------------------------------------------------------------------- #
_SHAPE_CLASSES: dict[ShapeKind, type[Shape]] = {
    ShapeKind.RECT: RectShape,
    ShapeKind.CIRCLE: CircleShape,
    ShapeKind.ELLIPSE: EllipseShape,
    ShapeKind.POLYGON: PolygonShape,
    ShapeKind.TEXT: TextShape,
}


def shape_from_dict(data: dict[str, Any]) -> Shape:
    """Reconstruit une forme depuis sa représentation JSON."""
    kind = ShapeKind(data["kind"])
    geometry = dict(data.get("geometry", {}))
    if kind is ShapeKind.POLYGON:
        geometry["points_mm"] = [tuple(p) for p in geometry.get("points_mm", [])]
        geometry["holes_mm"] = [
            [tuple(p) for p in hole] for hole in geometry.get("holes_mm", [])
        ]
    cls = _SHAPE_CLASSES[kind]
    shape = cls(
        x_mm=float(data.get("x_mm", 0.0)),
        y_mm=float(data.get("y_mm", 0.0)),
        rotation_deg=float(data.get("rotation_deg", 0.0)),
        spec=CutoutSpec.from_dict(data.get("spec", {})),
        id=data.get("id", _new_id()),
        **geometry,
    )
    return shape


def polygon_to_points(
    polygon: Polygon, decimals: int = 2
) -> list[tuple[float, float]]:
    """Extrait les sommets extérieurs d'un polygone, arrondis pour export."""
    return [
        (round(x, decimals), round(y, decimals))
        for x, y in polygon.exterior.coords
    ]


def center_of_mass(
    shapes: Sequence[Shape],
) -> tuple[float, float, float] | None:
    """Centre de masse (x, y, poids total en g) des formes pondérées.

    Retourne ``None`` si aucun poids n'est renseigné.
    """
    total = sum(s.spec.weight_g for s in shapes)
    if total <= 0:
        return None
    cx = sum(s.x_mm * s.spec.weight_g for s in shapes) / total
    cy = sum(s.y_mm * s.spec.weight_g for s in shapes) / total
    return cx, cy, total


def distance_mm(a: Shape, b: Shape) -> float:
    """Distance minimale entre deux découpes (0 si contact/chevauchement)."""
    return a.cut_polygon().distance(b.cut_polygon())


def rotate_point(
    x: float, y: float, angle_deg: float
) -> tuple[float, float]:
    """Rotation d'un point autour de l'origine (utilitaire UI)."""
    a = math.radians(angle_deg)
    return (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a))
