"""Unités et constantes géométriques.

Toute la géométrie interne de FoamForge est exprimée en millimètres (mm).
Ce module centralise les conversions et l'arrondi/snapping afin de garantir
une précision constante dans tout le logiciel (contrainte fabrication).
"""

from __future__ import annotations

# Formats papier utilisés pour la calibration photo (mm).
A4_WIDTH_MM: float = 210.0
A4_HEIGHT_MM: float = 297.0

# Précision géométrique : tout est arrondi au centième de mm pour les exports.
EXPORT_PRECISION_DECIMALS: int = 2

INCH_MM: float = 25.4


def mm_to_px(value_mm: float, dpi: float) -> float:
    """Convertit des millimètres en pixels pour un rendu à ``dpi`` donné."""
    return value_mm * dpi / INCH_MM


def px_to_mm(value_px: float, dpi: float) -> float:
    """Convertit des pixels en millimètres pour un rendu à ``dpi`` donné."""
    return value_px * INCH_MM / dpi


def snap(value_mm: float, step_mm: float) -> float:
    """Aligne ``value_mm`` sur la grille de pas ``step_mm`` (magnétisme).

    Un pas nul ou négatif désactive le magnétisme.
    """
    if step_mm <= 0:
        return value_mm
    return round(value_mm / step_mm) * step_mm


def clean(value_mm: float) -> float:
    """Arrondit une coordonnée à la précision d'export (0.01 mm).

    Retourne toujours un ``float`` (``round(int)`` rendrait un ``int``,
    ce qui changerait le format des exports texte).
    """
    return float(round(value_mm, EXPORT_PRECISION_DECIMALS))


def fmt_mm(value_mm: float, decimals: int = 1) -> str:
    """Formate une dimension pour affichage utilisateur, ex. ``'42.5 mm'``."""
    return f"{value_mm:.{decimals}f} mm"
