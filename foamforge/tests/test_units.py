"""Tests des utilitaires d'unités."""

from __future__ import annotations

import pytest

from foamforge.core.units import clean, fmt_mm, mm_to_px, px_to_mm, snap


def test_snap() -> None:
    assert snap(12.3, 1.0) == 12.0
    assert snap(12.6, 1.0) == 13.0
    assert snap(12.6, 5.0) == 15.0
    # Pas nul : magnétisme désactivé.
    assert snap(12.34, 0.0) == 12.34


def test_mm_px_roundtrip() -> None:
    assert px_to_mm(mm_to_px(42.5, dpi=150), dpi=150) == pytest.approx(42.5)
    assert mm_to_px(25.4, dpi=300) == pytest.approx(300)


def test_clean_and_format() -> None:
    assert clean(12.3456) == 12.35
    assert fmt_mm(42.0) == "42.0 mm"
    assert fmt_mm(42.456, decimals=2) == "42.46 mm"
