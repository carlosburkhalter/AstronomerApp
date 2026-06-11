"""Génère le projet d'exemple « Valise astro » et ses exports.

Usage (depuis la racine du dépôt) ::

    python -m foamforge.examples.create_demo_project [dossier_sortie]

Produit : le projet ``.foamforge.json``, les exports SVG/DXF/PNG/PDF et
la checklist HTML, dans le dossier de sortie (par défaut
``foamforge/examples``).
"""

from __future__ import annotations

import sys
from pathlib import Path

from foamforge.core.geometry import (
    CircleShape,
    CutoutSpec,
    CutType,
    RectShape,
    TextShape,
)
from foamforge.core.project import FoamSheet, Project
from foamforge.core.validation import validate_project
from foamforge.export.dxf_exporter import export_dxf
from foamforge.export.pdf_exporter import export_checklist_html, export_pdf, export_png
from foamforge.export.svg_exporter import export_svg


def build_demo_project() -> Project:
    """Valise d'imagerie astro typique : caméra, roue à filtres, oculaires."""
    project = Project(
        name="Valise astro — démo",
        case_width_mm=460, case_height_mm=360, case_depth_mm=180,
        sheet=FoamSheet(width_mm=440, height_mm=340, thickness_mm=60),
        layer_count=1,
        foam_type="Plastazote",
        notes="Vérifier la dessicant-box avant chaque sortie.",
    )
    project.add_shape(RectShape(
        width_mm=90, height_mm=90, x_mm=90, y_mm=95,
        spec=CutoutSpec(name="Caméra ASI2600MC", depth_mm=50, margin_mm=2,
                        corner_radius_mm=6, weight_g=700,
                        comment="Connectique vers le haut"),
    ))
    project.add_shape(CircleShape(
        diameter_mm=110, x_mm=240, y_mm=95,
        spec=CutoutSpec(name="Roue à filtres EFW", depth_mm=30, margin_mm=2,
                        weight_g=550),
    ))
    project.add_shape(RectShape(
        width_mm=70, height_mm=130, x_mm=370, y_mm=110,
        spec=CutoutSpec(name="Guide caméra + OAG", depth_mm=40, margin_mm=2,
                        corner_radius_mm=5, weight_g=350),
    ))
    for i, x in enumerate((70, 150, 230)):
        project.add_shape(CircleShape(
            diameter_mm=45, x_mm=x, y_mm=250,
            spec=CutoutSpec(name=f"Oculaire {i + 1}", depth_mm=45,
                            margin_mm=1.5, weight_g=200),
        ))
    project.add_shape(RectShape(
        width_mm=80, height_mm=55, x_mm=360, y_mm=255,
        spec=CutoutSpec(name="Boîte à filtres", depth_mm=35, margin_mm=1,
                        corner_radius_mm=4, weight_g=250,
                        cut_type=CutType.POCKET),
    ))
    project.add_shape(TextShape(
        text="ASTRO KIT", x_mm=222, y_mm=320, font_height_mm=10,
        spec=CutoutSpec(name="Étiquette", depth_mm=1),
    ))
    return project


def main(output_dir: str | Path | None = None) -> Path:
    out = Path(output_dir) if output_dir else Path(__file__).parent
    out.mkdir(parents=True, exist_ok=True)
    project = build_demo_project()

    issues = validate_project(project)
    print(f"Validation : {len(issues)} alerte(s)")
    for issue in issues:
        print(f"  [{issue.severity.value}] {issue.message}")

    base = out / "valise_astro_demo"
    project.save(f"{base}.foamforge.json")
    export_svg(project, f"{base}.svg")
    export_dxf(project, f"{base}.dxf")
    export_png(project, f"{base}.png")
    export_pdf(project, f"{base}.pdf")
    export_checklist_html(project, f"{base}_checklist.html")
    print(f"Fichiers générés dans : {out}")
    return out


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
