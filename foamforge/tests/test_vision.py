"""Tests du module vision sur images synthétiques.

On génère des photos artificielles (feuille A4 claire + objets sombres)
pour vérifier calibration et détection sans dépendre de vraies photos.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from foamforge.vision.calibration import (
    CalibrationError,
    calibrate_with_a4,
    scale_from_reference,
)
from foamforge.vision.contour_detection import detect_object_contours
from foamforge.vision.image_import import ImageImportSession

# Échelle de la scène synthétique : 4 px par mm.
_PX_PER_MM = 4.0


def _synthetic_photo() -> np.ndarray:
    """Fond gris, feuille A4 blanche, un rectangle et un disque sombres."""
    image = np.full((1400, 1100, 3), 120, dtype=np.uint8)
    # Feuille A4 (210 × 297 mm) en portrait.
    w = int(210 * _PX_PER_MM)
    h = int(297 * _PX_PER_MM)
    x0, y0 = 100, 100
    cv2.rectangle(image, (x0, y0), (x0 + w, y0 + h), (250, 250, 250), -1)
    # Objet 1 : rectangle 80 × 40 mm.
    rx, ry = x0 + 80, y0 + 120
    cv2.rectangle(
        image, (rx, ry),
        (rx + int(80 * _PX_PER_MM), ry + int(40 * _PX_PER_MM)),
        (30, 30, 30), -1,
    )
    # Objet 2 : disque de 50 mm de diamètre.
    cv2.circle(
        image, (x0 + 400, y0 + 800), int(25 * _PX_PER_MM), (40, 40, 40), -1
    )
    return image


def test_a4_calibration_scale() -> None:
    result = calibrate_with_a4(_synthetic_photo())
    assert result.method == "a4"
    assert result.mm_per_px == pytest.approx(1 / _PX_PER_MM, rel=0.02)
    assert result.quad_px is not None and result.quad_px.shape == (4, 2)


def test_a4_calibration_fails_without_sheet() -> None:
    image = np.full((500, 500, 3), 120, dtype=np.uint8)
    with pytest.raises(CalibrationError):
        calibrate_with_a4(image)


def test_manual_calibration() -> None:
    result = scale_from_reference(length_px=400, length_mm=100)
    assert result.mm_per_px == pytest.approx(0.25)
    with pytest.raises(CalibrationError):
        scale_from_reference(length_px=0, length_mm=100)


def test_object_detection_dimensions() -> None:
    image = _synthetic_photo()
    calibration = calibrate_with_a4(image)
    detected = detect_object_contours(
        image,
        calibration.mm_per_px,
        min_area_mm2=400,
        exclude_quad_px=calibration.quad_px,
    )
    assert len(detected) == 2
    # Plus grand objet : rectangle 80 × 40 mm → aire ~3200 mm².
    rect = detected[0]
    assert rect.area_mm2 == pytest.approx(3200, rel=0.05)
    minx, miny, maxx, maxy = rect.polygon_mm.bounds
    assert maxx - minx == pytest.approx(80, abs=2)
    assert maxy - miny == pytest.approx(40, abs=2)
    # Second objet : disque ⌀50 mm → aire ~1963 mm².
    assert detected[1].area_mm2 == pytest.approx(1963, rel=0.05)


def test_import_session_full_flow(tmp_path) -> None:
    from PIL import Image

    image = _synthetic_photo()
    path = tmp_path / "photo.png"
    Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)).save(path)

    session = ImageImportSession()
    session.load_image(path)
    session.calibrate_a4()
    detected = session.detect()
    assert len(detected) == 2
    shapes = session.to_shapes(margin_mm=2.0, depth_mm=35.0)
    assert len(shapes) == 2
    assert shapes[0].spec.margin_mm == 2.0
    assert shapes[0].spec.depth_mm == 35.0
    # La marge agrandit la découpe par rapport à l'objet détecté.
    assert shapes[0].cut_polygon().area > shapes[0].object_polygon().area


def test_detection_requires_calibration() -> None:
    session = ImageImportSession()
    with pytest.raises(CalibrationError):
        session.detect()
