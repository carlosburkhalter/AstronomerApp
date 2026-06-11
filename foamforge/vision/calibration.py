"""Calibration de l'échelle d'une photo (mm par pixel).

Deux méthodes :

1. **Feuille A4** : détection automatique du plus grand quadrilatère clair
   de l'image (la feuille posée sous/à côté des objets), dont le grand
   côté mesure 297 mm.
2. **Référence manuelle** : l'utilisateur trace un segment sur une règle
   visible dans la photo et saisit sa longueur réelle.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

from foamforge.core.units import A4_HEIGHT_MM, A4_WIDTH_MM


@dataclass
class CalibrationResult:
    """Échelle calculée pour une photo."""

    mm_per_px: float
    method: str  # "a4" ou "manual"
    # Quadrilatère détecté (px), pour affichage de contrôle. None si manuel.
    quad_px: np.ndarray | None = None


class CalibrationError(Exception):
    """Échec de la calibration automatique."""


def scale_from_reference(length_px: float, length_mm: float) -> CalibrationResult:
    """Calibration manuelle : segment tracé sur une règle connue."""
    if length_px <= 0 or length_mm <= 0:
        raise CalibrationError("Longueurs de référence invalides.")
    return CalibrationResult(mm_per_px=length_mm / length_px, method="manual")


def detect_a4_sheet(image_bgr: np.ndarray) -> np.ndarray:
    """Détecte la feuille A4 : plus grand quadrilatère convexe de l'image.

    Retourne les 4 coins en pixels (4, 2). Lève :class:`CalibrationError`
    si aucun quadrilatère plausible n'est trouvé.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # Seuillage Otsu : la feuille blanche se détache du fond.
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    image_area = image_bgr.shape[0] * image_bgr.shape[1]
    best: np.ndarray | None = None
    best_area = 0.0
    for contour in contours:
        area = cv2.contourArea(contour)
        # La feuille doit occuper une part significative de l'image.
        if area < image_area * 0.05 or area <= best_area:
            continue
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            best = approx.reshape(4, 2).astype(np.float64)
            best_area = area
    if best is None:
        raise CalibrationError(
            "Feuille A4 introuvable : assurez-vous que la feuille entière "
            "est visible et contraste avec le fond."
        )
    return best


def calibrate_with_a4(image_bgr: np.ndarray) -> CalibrationResult:
    """Calcule l'échelle mm/px à partir de la feuille A4 détectée.

    L'échelle moyenne les deux paires de côtés opposés (grand côté
    = 297 mm, petit côté = 210 mm), ce qui tolère une légère perspective.
    """
    quad = detect_a4_sheet(image_bgr)
    # Longueurs des 4 côtés du quadrilatère, ordonnées.
    sides = [
        math.dist(quad[i], quad[(i + 1) % 4]) for i in range(4)
    ]
    long_px = (sides[0] + sides[2]) / 2
    short_px = (sides[1] + sides[3]) / 2
    if short_px > long_px:
        long_px, short_px = short_px, long_px
    if short_px <= 0:
        raise CalibrationError("Quadrilatère dégénéré détecté.")
    scale_long = A4_HEIGHT_MM / long_px
    scale_short = A4_WIDTH_MM / short_px
    # Si la perspective est trop forte, les deux échelles divergent : la
    # photo doit être prise au-dessus, à plat.
    if abs(scale_long - scale_short) / scale_long > 0.15:
        raise CalibrationError(
            "Perspective trop marquée : photographiez la feuille bien à "
            "plat, appareil à la verticale."
        )
    return CalibrationResult(
        mm_per_px=(scale_long + scale_short) / 2,
        method="a4",
        quad_px=quad,
    )
