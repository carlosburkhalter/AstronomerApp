"""Exports fabrication : SVG, DXF, PDF de contrôle, prévisualisation PNG.

Tous les exports partagent la même convention de calques :

==============  =============================================
Calque          Contenu
==============  =============================================
FOAM_BORDER     contour extérieur de la plaque de mousse
CUT_FULL        découpes traversantes
CUT_POCKET      poches partielles (profondeur annotée)
ENGRAVE         gravures de surface
TEXT            textes gravés
REFERENCE       repères (origine, croix de centrage)
==============  =============================================
"""

LAYER_FOAM_BORDER = "FOAM_BORDER"
LAYER_CUT_FULL = "CUT_FULL"
LAYER_CUT_POCKET = "CUT_POCKET"
LAYER_ENGRAVE = "ENGRAVE"
LAYER_TEXT = "TEXT"
LAYER_REFERENCE = "REFERENCE"

ALL_LAYERS = [
    LAYER_FOAM_BORDER,
    LAYER_CUT_FULL,
    LAYER_CUT_POCKET,
    LAYER_ENGRAVE,
    LAYER_TEXT,
    LAYER_REFERENCE,
]

# Couleurs conventionnelles des calques (affichage et SVG).
LAYER_COLORS = {
    LAYER_FOAM_BORDER: "#000000",
    LAYER_CUT_FULL: "#d32f2f",
    LAYER_CUT_POCKET: "#1565c0",
    LAYER_ENGRAVE: "#2e7d32",
    LAYER_TEXT: "#6a1b9a",
    LAYER_REFERENCE: "#9e9e9e",
}
