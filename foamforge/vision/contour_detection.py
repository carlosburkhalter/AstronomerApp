"""Détection des contours d'objets sur photo et vectorisation.

Pipeline : niveaux de gris → flou → seuillage Otsu inversé (objets sombres
sur fond clair, cas typique d'objets posés sur une feuille A4 blanche) →
contours externes → filtrage par aire → simplification (Douglas-Peucker)
→ lissage → polygones Shapely en millimètres.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from shapely.geometry import Polygon

from foamforge.core.geometry import CutoutSpec, CutType, PolygonShape

# Tolérance de simplification Douglas-Peucker, en mm : en dessous de
# 0.5 mm l'œil ne voit pas la différence et le laser non plus.
_SIMPLIFY_TOLERANCE_MM = 0.5
# Lissage final : petit buffer aller-retour qui casse les marches d'escalier
# de la pixellisation sans déformer la silhouette.
_SMOOTH_RADIUS_MM = 0.8


@dataclass
class DetectedObject:
    """Objet détecté sur la photo, prêt pour prévisualisation."""

    polygon_mm: Polygon          # contour nettoyé, en mm (repère photo)
    area_mm2: float
    contour_px: np.ndarray       # contour brut, pour superposition à l'image


def detect_object_contours(
    image_bgr: np.ndarray,
    mm_per_px: float,
    min_area_mm2: float = 400.0,
    exclude_quad_px: np.ndarray | None = None,
) -> list[DetectedObject]:
    """Détecte les objets de la photo et retourne leurs contours en mm.

    :param image_bgr: image OpenCV (BGR).
    :param mm_per_px: échelle issue de la calibration.
    :param min_area_mm2: aire minimale pour ignorer poussières et reflets.
    :param exclude_quad_px: quadrilatère de la feuille A4 à exclure de la
        détection (la feuille elle-même n'est pas un objet).
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # Objets sombres sur fond clair → seuillage inversé.
    _, thresh = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    # Nettoyage morphologique : supprime le bruit, rebouche les petits trous.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # RETR_TREE et non RETR_EXTERNAL : si le fond de la photo est sombre,
    # il forme un anneau englobant et les objets posés sur la feuille
    # claire deviennent des contours imbriqués (profondeur paire).
    contours, hierarchy = cv2.findContours(
        thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )
    height_px, width_px = thresh.shape[:2]

    detected: list[DetectedObject] = []
    for index, contour in enumerate(contours):
        if len(contour) < 3:
            continue
        # Seules les frontières extérieures de régions sombres (profondeur
        # paire dans la hiérarchie) sont des objets candidats.
        if _hierarchy_depth(hierarchy, index) % 2 != 0:
            continue
        # Un contour touchant le bord de l'image est du fond, pas un objet.
        if _touches_image_border(contour, width_px, height_px):
            continue
        area_mm2 = cv2.contourArea(contour) * mm_per_px**2
        if area_mm2 < min_area_mm2:
            continue
        if exclude_quad_px is not None and _is_sheet(contour, exclude_quad_px):
            continue
        polygon = _contour_to_polygon_mm(contour, mm_per_px)
        if polygon is None:
            continue
        detected.append(
            DetectedObject(
                polygon_mm=polygon,
                area_mm2=polygon.area,
                contour_px=contour,
            )
        )
    # Les plus gros objets d'abord : ce sont eux que l'utilisateur attend.
    detected.sort(key=lambda d: d.area_mm2, reverse=True)
    return detected


def _hierarchy_depth(hierarchy: np.ndarray | None, index: int) -> int:
    """Profondeur d'un contour dans la hiérarchie OpenCV (0 = racine)."""
    if hierarchy is None:
        return 0
    depth = 0
    parent = hierarchy[0][index][3]
    while parent != -1:
        depth += 1
        parent = hierarchy[0][parent][3]
    return depth


def _touches_image_border(
    contour: np.ndarray, width_px: int, height_px: int, margin_px: int = 2
) -> bool:
    """Vrai si le contour atteint le bord de l'image (= fond, pas objet)."""
    xs = contour[:, 0, 0]
    ys = contour[:, 0, 1]
    return bool(
        (xs <= margin_px).any()
        or (ys <= margin_px).any()
        or (xs >= width_px - 1 - margin_px).any()
        or (ys >= height_px - 1 - margin_px).any()
    )


def _is_sheet(contour: np.ndarray, quad_px: np.ndarray) -> bool:
    """Vrai si le contour correspond à la feuille de calibration."""
    sheet = Polygon(quad_px)
    candidate = Polygon(contour.reshape(-1, 2))
    if not candidate.is_valid:
        candidate = candidate.buffer(0)
    if candidate.is_empty or sheet.is_empty:
        return False
    overlap = candidate.intersection(sheet).area
    return overlap > 0.8 * sheet.area


def _contour_to_polygon_mm(
    contour: np.ndarray, mm_per_px: float
) -> Polygon | None:
    """Convertit un contour OpenCV (px) en polygone Shapely propre (mm)."""
    points = contour.reshape(-1, 2).astype(np.float64) * mm_per_px
    polygon = Polygon(points)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    if polygon.is_empty:
        return None
    if polygon.geom_type == "MultiPolygon":
        polygon = max(polygon.geoms, key=lambda g: g.area)
    # Simplification puis lissage des marches de pixellisation.
    polygon = polygon.simplify(_SIMPLIFY_TOLERANCE_MM, preserve_topology=True)
    smoothed = polygon.buffer(_SMOOTH_RADIUS_MM, quad_segs=8).buffer(
        -_SMOOTH_RADIUS_MM, quad_segs=8
    )
    if not smoothed.is_empty and smoothed.geom_type == "Polygon":
        polygon = smoothed
    return polygon


def detected_to_shape(
    detected: DetectedObject,
    name: str = "Objet photo",
    margin_mm: float = 2.0,
    depth_mm: float = 30.0,
) -> PolygonShape:
    """Convertit un objet détecté en forme de projet avec marge de découpe."""
    spec = CutoutSpec(
        name=name,
        margin_mm=margin_mm,
        depth_mm=depth_mm,
        cut_type=CutType.POCKET,
    )
    return PolygonShape.from_polygon(detected.polygon_mm, spec=spec)
