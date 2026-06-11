"""PDF de contrôle, prévisualisation PNG et checklist HTML.

Le PDF de contrôle n'est pas destiné à la machine : c'est un document
de vérification humaine (rendu de la plaque + cartouche + checklist des
objets). Le rendu raster est produit avec Pillow à une résolution fixe,
puis encapsulé en PDF — simple, sans dépendance supplémentaire, et
suffisant pour un document de contrôle.
"""

from __future__ import annotations

import html
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from foamforge.core.geometry import CutType, ShapeKind, TextShape
from foamforge.core.project import Project
from foamforge.core.units import mm_to_px
from foamforge.export import LAYER_COLORS, LAYER_CUT_FULL, LAYER_CUT_POCKET

_PREVIEW_DPI = 150.0
_MARGIN_PX = 40


def _font(size_px: int) -> ImageFont.ImageFont:
    """Police de rendu ; repli sur la police bitmap par défaut de Pillow."""
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size_px)
    except OSError:
        return ImageFont.load_default()


def render_preview(
    project: Project, dpi: float = _PREVIEW_DPI
) -> Image.Image:
    """Rend la plaque en image Pillow (fond = couleur de fond du projet)."""
    sheet = project.sheet
    width_px = int(mm_to_px(sheet.width_mm, dpi)) + 2 * _MARGIN_PX
    height_px = int(mm_to_px(sheet.height_mm, dpi)) + 2 * _MARGIN_PX
    image = Image.new("RGB", (width_px, height_px), "#ffffff")
    draw = ImageDraw.Draw(image)

    def to_px(x_mm: float, y_mm: float) -> tuple[float, float]:
        return (
            _MARGIN_PX + mm_to_px(x_mm, dpi),
            _MARGIN_PX + mm_to_px(y_mm, dpi),
        )

    # Plaque de mousse (la couleur de fond révèle les découpes).
    draw.rectangle(
        [to_px(0, 0), to_px(sheet.width_mm, sheet.height_mm)],
        fill=project.foam_color,
        outline="#000000",
        width=2,
    )

    for shape in sorted(project.shapes, key=lambda s: s.spec.cut_order):
        if shape.kind is ShapeKind.TEXT:
            _draw_text(draw, shape, to_px, dpi)  # type: ignore[arg-type]
            continue
        polygon = shape.cut_polygon()
        points = [to_px(x, y) for x, y in polygon.exterior.coords]
        outline = (
            LAYER_COLORS[LAYER_CUT_FULL]
            if shape.spec.cut_type == CutType.FULL
            else LAYER_COLORS[LAYER_CUT_POCKET]
        )
        # Une découpe laisse voir le fond de la valise (découpe complète)
        # ou un fond de poche plus sombre que la surface.
        fill = (
            project.background_color
            if shape.spec.cut_type == CutType.FULL
            else _lighten(project.foam_color, 0.25)
        )
        draw.polygon(points, fill=fill, outline=outline)
        # Étiquette : nom + profondeur, centrée dans le logement.
        label = f"{shape.spec.name}\n{shape.spec.depth_mm:.0f} mm"
        font = _font(int(mm_to_px(4, dpi)))
        draw.multiline_text(
            to_px(shape.x_mm, shape.y_mm),
            label,
            fill="#ffffff",
            font=font,
            anchor="mm",
            align="center",
        )
    return image


def _lighten(hex_color: str, amount: float) -> str:
    """Éclaircit une couleur hexadécimale (mélange vers le blanc, 0..1)."""
    value = hex_color.lstrip("#")
    r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    mixed = tuple(int(c + (255 - c) * amount) for c in (r, g, b))
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def _draw_text(draw: ImageDraw.ImageDraw, shape: TextShape, to_px, dpi: float) -> None:
    font = _font(int(mm_to_px(shape.font_height_mm, dpi)))
    draw.text(
        to_px(shape.x_mm, shape.y_mm),
        shape.text,
        fill="#e0e0e0",
        font=font,
        anchor="mm",
    )


def export_png(project: Project, path: str | Path, dpi: float = _PREVIEW_DPI) -> Path:
    """Exporte la prévisualisation PNG de la plaque."""
    path = Path(path)
    render_preview(project, dpi).save(path, "PNG", dpi=(dpi, dpi))
    return path


def export_pdf(project: Project, path: str | Path) -> Path:
    """Exporte le PDF de contrôle : rendu + cartouche + checklist."""
    preview = render_preview(project)
    width, height = preview.size

    # Cartouche au-dessus du rendu.
    header_height = 220
    page = Image.new("RGB", (width, height + header_height), "#ffffff")
    draw = ImageDraw.Draw(page)
    title_font = _font(36)
    body_font = _font(22)
    sheet = project.sheet
    draw.text((40, 24), f"FoamForge — {project.name}", fill="#000000", font=title_font)
    lines = [
        f"Date : {date.today().isoformat()}",
        f"Plaque : {sheet.width_mm:.0f} × {sheet.height_mm:.0f} × "
        f"{sheet.thickness_mm:.0f} mm — {project.foam_type} — "
        f"{project.layer_count} couche(s)",
        f"Logements : {len(project.checklist_items())} — "
        f"Objets : {', '.join(project.checklist_items()) or 'aucun'}",
    ]
    y = 84
    for line in lines:
        draw.text((40, y), line, fill="#333333", font=body_font)
        y += 36
    page.paste(preview, (0, header_height))

    path = Path(path)
    page.save(path, "PDF", resolution=_PREVIEW_DPI)
    return path


def export_checklist_html(project: Project, path: str | Path) -> Path:
    """Exporte la checklist du projet en HTML imprimable.

    La checklist liste les objets attendus dans la valise : elle sert à
    vérifier que rien n'est oublié avant de partir sur le terrain.
    """
    items = project.checklist_items()
    rows = "\n".join(
        f'      <li><label><input type="checkbox"> '
        f"{html.escape(name)}</label></li>"
        for name in items
    )
    notes = html.escape(project.notes) or "—"
    content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>Checklist — {html.escape(project.name)}</title>
  <style>
    body {{ font-family: sans-serif; max-width: 700px; margin: 2rem auto; }}
    h1 {{ border-bottom: 2px solid #b3261e; padding-bottom: .3rem; }}
    li {{ margin: .4rem 0; font-size: 1.1rem; list-style: none; }}
    .notes {{ background: #f5f5f5; padding: 1rem; border-radius: 6px; }}
  </style>
</head>
<body>
  <h1>Checklist — {html.escape(project.name)}</h1>
  <p>{len(items)} objet(s) à emporter. Cochez chaque objet replacé
     dans la valise : un logement vide sur fond
     <strong style="color:{project.background_color}">coloré</strong>
     signale un objet manquant.</p>
  <ul>
{rows}
  </ul>
  <h2>Notes</h2>
  <p class="notes">{notes}</p>
</body>
</html>
"""
    path = Path(path)
    path.write_text(content, encoding="utf-8")
    return path
