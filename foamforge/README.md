# FoamForge

Application desktop de conception de **mousses de protection sur mesure**
pour valises de transport : astronomie, optique, photographie, drones,
électronique fragile, matériel scientifique.

Dessinez les logements de vos objets, validez automatiquement la solidité
de la conception (parois minimales, distances au bord, profondeurs), puis
exportez des fichiers **SVG/DXF propres pour découpe laser ou CNC**.
Toutes les unités sont en millimètres.

La mousse ne sert pas qu'à protéger : grâce au **fond contrasté** (mousse
noire sur fond rouge) et à la **checklist générée**, un logement vide se
voit immédiatement — vous ne laissez plus jamais un oculaire sur le terrain.

---

## Installation

Prérequis : **Python 3.11 ou plus récent** (3.12 recommandé).

```bash
# 1. Cloner le dépôt puis, depuis sa racine :
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate

# 2. Installer les dépendances
pip install -r foamforge/requirements.txt
```

## Lancer le logiciel

Depuis la racine du dépôt :

```bash
python -m foamforge.app.main
```

Ouvrir directement un projet :

```bash
python -m foamforge.app.main foamforge/examples/valise_astro_demo.foamforge.json
```

### Premiers pas (mode débutant)

1. **Projet → Nouveau…** : nom, dimensions de la valise, plaque de mousse
   (largeur × hauteur × épaisseur), type de mousse, couleurs.
2. Choisissez un outil à gauche (**R**ectangle, **C**ercle, **E**llipse,
   **T**exte) et tracez les logements sur la grille millimétrique.
   La molette zoome, le clic milieu déplace la vue, **F** recadre.
3. Sélectionnez une forme (**S**) : le panneau de droite règle nom,
   dimensions, profondeur et **marge de tolérance** (+1, +2, +3 mm…).
4. Le panneau du bas affiche les **contrôles de sécurité** en continu :
   ⛔ rouge = bloquant, ⚠️ orange = recommandation, ✅ vert = valide.
   Cliquer sur une alerte sélectionne les formes concernées.
5. **Outils → Placement automatique** propose plusieurs dispositions
   (compacité, pièces longues, répartition du poids).
6. **Projet → Exporter** : SVG (laser), DXF (CNC), PDF de contrôle,
   PNG, checklist HTML. L'export fabrication est bloqué tant qu'il
   reste une erreur rouge.

Le **mode expert** (menu Affichage) révèle rotation, rayon d'arrondi,
ordre de découpe, poids et commentaires.

## Tests

```bash
python -m pytest foamforge/tests
```

## Générer le projet d'exemple

```bash
python -m foamforge.examples.create_demo_project
```

Produit dans `foamforge/examples/` : le projet « Valise astro » et tous
ses exports (SVG, DXF, PNG, PDF, checklist HTML).

---

## Architecture

```
foamforge/
├── app/                 Point d'entrée et fenêtre principale
│   ├── main.py
│   └── main_window.py
├── core/                Cœur métier (sans dépendance UI)
│   ├── project.py       Modèle de projet + persistance JSON versionnée
│   ├── geometry.py      Formes, marges, arrondis (Shapely)
│   ├── validation.py    Contrôles de sécurité (rouge/orange/vert)
│   ├── nesting.py       Placement automatique (glouton bottom-left)
│   └── units.py         Unités mm, snapping, précision d'export
├── ui/                  Composants PySide6
│   ├── canvas.py        Canvas 2D : grille mm, zoom, dessin, magnétisme
│   ├── toolbars.py      Barre d'outils de dessin
│   ├── property_panel.py Panneau de propriétés (modes débutant/expert)
│   ├── alerts_panel.py  Panneau d'alertes de validation
│   └── dialogs.py       Nouveau projet, choix de nesting
├── vision/              Import photo (OpenCV)
│   ├── image_import.py  Session d'import (orchestration)
│   ├── calibration.py   Échelle par feuille A4 ou règle
│   └── contour_detection.py  Détection/nettoyage/vectorisation
├── export/              Fabrication (calques CUT_FULL, CUT_POCKET, …)
│   ├── svg_exporter.py  SVG mm pour laser
│   ├── dxf_exporter.py  DXF R2010 mm pour CNC (ezdxf)
│   └── pdf_exporter.py  PDF de contrôle, PNG, checklist HTML
├── database/            Bibliothèque d'objets (SQLite)
│   ├── db.py            Connexion, schéma versionné, catégories
│   └── object_library.py CRUD, recherche, import/export JSON
├── examples/            Projet de démonstration
└── tests/               Suite pytest (cœur, exports, vision, BDD, UI)
```

Séparation stricte : `core/`, `export/`, `vision/` et `database/` ne
dépendent jamais de Qt — ils sont testables sans écran et réutilisables
(CLI, traitement par lots, futur service web).

### Format de fichier

`*.foamforge.json` — JSON lisible et versionné (`schema_version`),
adapté au suivi git et aux migrations futures.

### Convention de calques (SVG et DXF)

| Calque        | Contenu                          |
|---------------|----------------------------------|
| `FOAM_BORDER` | contour de la plaque             |
| `CUT_FULL`    | découpes traversantes            |
| `CUT_POCKET`  | poches partielles                |
| `ENGRAVE`     | gravures                         |
| `TEXT`        | textes gravés                    |
| `REFERENCE`   | croix de calage machine          |

Le DXF est exporté en repère machine (axe Y vers le haut, `$INSUNITS=4`).

---

## État du MVP

Fonctionnel dès maintenant :

- création de projet (valise, plaque, épaisseur, couches, type, couleurs) ;
- canvas 2D : grille mm, zoom, pan, sélection, magnétisme, dimensions réelles ;
- rectangle, cercle, ellipse, texte gravé ; déplacement, duplication,
  suppression ; rotation et redimensionnement par le panneau de propriétés ;
- paramètres de découpe complets par logement (profondeur, marge, arrondi,
  type, ordre, commentaire, poids) ;
- validation continue : chevauchements, parois fines, bords, profondeurs,
  répartition du poids — avec blocage des exports fabrication en erreur ;
- placement automatique (3 stratégies) ;
- sauvegarde/ouverture JSON ; exports SVG, DXF, PDF, PNG, checklist HTML ;
- bibliothèque d'objets SQLite (API complète + import/export) ;
- import photo (calibration A4/règle + détection de contours, API testée).

## Feuille de route vers une version commerciale

**v0.2 — Confort d'édition**
- annuler/rétablir (pile de commandes), groupes d'objets,
  poignées de redimensionnement/rotation sur le canvas,
  alignement automatique et guides magnétiques,
  outil polygone/forme libre au canvas.

**v0.3 — Bibliothèque et photo dans l'UI**
- panneau bibliothèque (recherche, glisser-déposer vers le canvas),
  assistant d'import photo en 3 étapes avec prévisualisation et
  ajustement interactif des contours,
  catalogue d'objets fournis (caméras ZWO/QHY, oculaires courants…).

**v0.4 — Multi-couches et fabrication avancée**
- gestion des couches de mousse (une découpe par couche, vue par couche),
  export par couche, ordre/sens de découpe optimisé,
  compensation du trait de coupe (kerf), ponts/attaches optionnels.

**v0.5 — Nesting et checklist pro**
- nesting avec rotations et métaheuristique (recuit simulé),
  checklist PDF avec vignettes des logements,
  étiquettes QR de valise reliant la checklist.

**v1.0 — Distribution commerciale**
- installeurs signés (Windows/macOS/Linux, PyInstaller + notarisation),
  mises à jour automatiques, télémétrie opt-in, documentation utilisateur,
  localisation EN/FR, licences et activation,
  profils machine (LightBurn, Trotec, Epilog…) avec presets matériaux.
