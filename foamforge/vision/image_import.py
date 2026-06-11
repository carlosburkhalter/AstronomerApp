"""Session d'import photo : orchestration calibration → détection → formes.

Flux utilisateur (assistant en 3 étapes côté UI) :

1. charger la photo (objets posés sur une feuille A4 blanche) ;
2. calibrer l'échelle (A4 automatique ou segment de référence manuel) ;
3. prévisualiser les contours détectés, ajuster la marge, valider les
   objets à ajouter au projet.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from foamforge.core.geometry import PolygonShape
from foamforge.vision.calibration import (
    CalibrationError,
    CalibrationResult,
    calibrate_with_a4,
    scale_from_reference,
)
from foamforge.vision.contour_detection import (
    DetectedObject,
    detect_object_contours,
    detected_to_shape,
)

# Les photos de smartphone sont surdimensionnées pour notre usage : on
# limite le grand côté pour des temps de traitement constants. L'échelle
# mm/px est calculée après ce redimensionnement, donc sans perte de cote.
_MAX_DIMENSION_PX = 2200


class ImageImportSession:
    """État d'un import photo en cours."""

    def __init__(self) -> None:
        self.image_bgr: np.ndarray | None = None
        self.calibration: CalibrationResult | None = None
        self.detected: list[DetectedObject] = []

    # ------------------------------------------------------------------ #
    # Étape 1 : chargement
    # ------------------------------------------------------------------ #
    def load_image(self, path: str | Path) -> None:
        """Charge la photo via Pillow (gère EXIF/format) puis convertit
        en matrice OpenCV BGR redimensionnée."""
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)  # respecte l'orientation photo
            rgb = img.convert("RGB")
        array = np.asarray(rgb)
        bgr = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
        height, width = bgr.shape[:2]
        largest = max(height, width)
        if largest > _MAX_DIMENSION_PX:
            scale = _MAX_DIMENSION_PX / largest
            bgr = cv2.resize(
                bgr, (int(width * scale), int(height * scale)),
                interpolation=cv2.INTER_AREA,
            )
        self.image_bgr = bgr
        self.calibration = None
        self.detected = []

    # ------------------------------------------------------------------ #
    # Étape 2 : calibration
    # ------------------------------------------------------------------ #
    def calibrate_a4(self) -> CalibrationResult:
        """Calibration automatique par feuille A4."""
        if self.image_bgr is None:
            raise CalibrationError("Aucune image chargée.")
        self.calibration = calibrate_with_a4(self.image_bgr)
        return self.calibration

    def calibrate_manual(
        self, length_px: float, length_mm: float
    ) -> CalibrationResult:
        """Calibration par segment tracé sur une règle visible."""
        self.calibration = scale_from_reference(length_px, length_mm)
        return self.calibration

    # ------------------------------------------------------------------ #
    # Étape 3 : détection et conversion
    # ------------------------------------------------------------------ #
    def detect(self, min_area_mm2: float = 400.0) -> list[DetectedObject]:
        """Détecte les objets ; nécessite image + calibration."""
        if self.image_bgr is None:
            raise CalibrationError("Aucune image chargée.")
        if self.calibration is None:
            raise CalibrationError("Calibrez l'échelle avant la détection.")
        self.detected = detect_object_contours(
            self.image_bgr,
            self.calibration.mm_per_px,
            min_area_mm2=min_area_mm2,
            exclude_quad_px=self.calibration.quad_px,
        )
        return self.detected

    def to_shapes(
        self, margin_mm: float = 2.0, depth_mm: float = 30.0
    ) -> list[PolygonShape]:
        """Convertit les objets détectés en formes prêtes à placer."""
        return [
            detected_to_shape(
                d,
                name=f"Objet photo {i + 1}",
                margin_mm=margin_mm,
                depth_mm=depth_mm,
            )
            for i, d in enumerate(self.detected)
        ]
