"""Fenêtre principale : assemble canvas, panneaux, menus et validation.

Disposition (cf. cahier des charges UX) :
- barre d'outils de dessin à gauche ;
- canvas central ;
- panneau de propriétés à droite (dock) ;
- panneau d'alertes en bas (dock) ;
- menus projet/édition/affichage/outils en haut ;
- barre d'état : position curseur en mm + feu tricolore de validation.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
)

from foamforge import __version__
from foamforge.core.booleans import (
    BooleanOperationError,
    intersect_shapes,
    merge_shapes,
    subtract_shapes,
)
from foamforge.core.nesting import propose_layouts
from foamforge.core.project import FILE_EXTENSION, Project
from foamforge.core.validation import (
    Issue,
    Severity,
    validate_project,
    worst_severity,
)
from foamforge.export.dxf_exporter import export_dxf
from foamforge.export.pdf_exporter import (
    export_checklist_html,
    export_pdf,
    export_png,
)
from foamforge.export.svg_exporter import export_svg
from foamforge.export.xtool_exporter import (
    XTOOL_P2S,
    MachineExportError,
    export_layers_svg,
    export_xtool_svg,
)
from foamforge.ui.alerts_panel import AlertsPanel
from foamforge.ui.canvas import FoamCanvas
from foamforge.ui.dialogs import NestingDialog, ProjectSettingsDialog
from foamforge.ui.layers_panel import LayersPanel
from foamforge.ui.property_panel import PropertyPanel
from foamforge.ui.toolbars import build_tool_toolbar
from foamforge.ui.view3d import FoamView3D

_PROJECT_FILTER = f"Projet FoamForge (*{FILE_EXTENSION})"


class MainWindow(QMainWindow):
    """Fenêtre principale de FoamForge."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"FoamForge {__version__}")
        self.resize(1280, 800)
        self._project_path: Path | None = None
        self._dirty = False

        # --- Centre : canvas 2D + vue 3D commutables --------------------- #
        from PySide6.QtWidgets import QStackedWidget

        self.canvas = FoamCanvas(self)
        self.view3d = FoamView3D(self)
        self._center_stack = QStackedWidget(self)
        self._center_stack.addWidget(self.canvas)
        self._center_stack.addWidget(self.view3d)
        self.setCentralWidget(self._center_stack)

        # --- Barre d'outils gauche -------------------------------------- #
        self.addToolBar(
            Qt.ToolBarArea.LeftToolBarArea, build_tool_toolbar(self.canvas)
        )

        # --- Panneau de propriétés (droite) ------------------------------ #
        self.property_panel = PropertyPanel(self)
        dock_props = QDockWidget("Propriétés", self)
        dock_props.setWidget(self.property_panel)
        dock_props.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_props)

        # --- Panneau couches de mousse (droite, onglet avec propriétés) -- #
        self.layers_panel = LayersPanel(self)
        dock_layers = QDockWidget("Couches de mousse", self)
        dock_layers.setWidget(self.layers_panel)
        dock_layers.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_layers)
        self.tabifyDockWidget(dock_props, dock_layers)
        dock_props.raise_()

        # --- Panneau d'alertes (bas) ------------------------------------- #
        self.alerts_panel = AlertsPanel(self)
        dock_alerts = QDockWidget("Contrôles de sécurité", self)
        dock_alerts.setWidget(self.alerts_panel)
        dock_alerts.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock_alerts)

        # --- Barre d'état ------------------------------------------------ #
        self._cursor_label = QLabel("x: — , y: —")
        self._status_light = QLabel("")
        self.statusBar().addWidget(self._cursor_label)
        self.statusBar().addPermanentWidget(self._status_light)

        # --- Validation différée (évite de recalculer à chaque pixel) ---- #
        self._validation_timer = QTimer(self)
        self._validation_timer.setSingleShot(True)
        self._validation_timer.setInterval(350)
        self._validation_timer.timeout.connect(self.run_validation)

        self._build_menus()
        self._connect_signals()
        self.set_project(Project())

    # ------------------------------------------------------------------ #
    # Menus
    # ------------------------------------------------------------------ #
    def _build_menus(self) -> None:
        menu_file = self.menuBar().addMenu("&Projet")
        self._add_action(menu_file, "Nouveau…", QKeySequence.StandardKey.New,
                         self.new_project)
        self._add_action(menu_file, "Ouvrir…", QKeySequence.StandardKey.Open,
                         self.open_project)
        self._add_action(menu_file, "Enregistrer",
                         QKeySequence.StandardKey.Save, self.save_project)
        self._add_action(menu_file, "Enregistrer sous…",
                         QKeySequence.StandardKey.SaveAs,
                         self.save_project_as)
        menu_file.addSeparator()
        self._add_action(menu_file, "Paramètres du projet…", "Ctrl+,",
                         self.edit_project_settings)
        menu_file.addSeparator()
        menu_export = menu_file.addMenu("Exporter")
        self._add_action(menu_export, "Exporter pour xTool P2S…", "Ctrl+E",
                         self.export_xtool)
        self._add_action(menu_export, "Exporter par couche (xTool P2S)…",
                         None, self.export_per_layer)
        menu_export.addSeparator()
        self._add_action(menu_export, "SVG (découpe laser)…", None,
                         lambda: self._export("svg"))
        self._add_action(menu_export, "DXF (CNC)…", None,
                         lambda: self._export("dxf"))
        self._add_action(menu_export, "PDF de contrôle…", None,
                         lambda: self._export("pdf"))
        self._add_action(menu_export, "PNG (prévisualisation)…", None,
                         lambda: self._export("png"))
        self._add_action(menu_export, "Checklist HTML…", None,
                         lambda: self._export("html"))
        menu_file.addSeparator()
        self._add_action(menu_file, "Quitter",
                         QKeySequence.StandardKey.Quit, self.close)

        menu_edit = self.menuBar().addMenu("&Édition")
        self._add_action(menu_edit, "Dupliquer", "Ctrl+Shift+D",
                         self.canvas.duplicate_selection)
        self._add_action(menu_edit, "Supprimer", "Backspace",
                         self.canvas.delete_selection)
        menu_edit.addSeparator()
        self._add_action(menu_edit, "Fusionner les formes", "Ctrl+M",
                         self.merge_selection)
        self._add_action(menu_edit, "Soustraire de la première forme",
                         "Ctrl+Shift+M", self.subtract_selection)
        self._add_action(menu_edit, "Intersection des formes", None,
                         self.intersect_selection)

        menu_view = self.menuBar().addMenu("&Affichage")
        self._add_action(menu_view, "Ajuster à la plaque", "Ctrl+0",
                         self.canvas.fit_sheet)
        self._view3d_action = QAction("Vue 3D", self)
        self._view3d_action.setCheckable(True)
        self._view3d_action.setShortcut("Ctrl+3")
        self._view3d_action.toggled.connect(self._toggle_3d)
        menu_view.addAction(self._view3d_action)
        menu_view.addSeparator()
        self._expert_action = QAction("Mode expert", self)
        self._expert_action.setCheckable(True)
        self._expert_action.toggled.connect(self._set_expert_mode)
        menu_view.addAction(self._expert_action)

        menu_tools = self.menuBar().addMenu("&Outils")
        self._add_action(menu_tools, "Placement automatique…", "Ctrl+L",
                         self.run_nesting)
        self._add_action(menu_tools, "Valider maintenant", "F5",
                         self.run_validation)

    def _add_action(self, menu, text: str, shortcut, slot) -> QAction:
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def _connect_signals(self) -> None:
        self.canvas.model_changed.connect(self._on_model_changed)
        self.canvas.selection_changed.connect(self._on_selection_changed)
        self.canvas.cursor_moved.connect(self._on_cursor_moved)
        self.property_panel.shape_edited.connect(self.canvas.refresh_shape)
        self.alerts_panel.issue_activated.connect(self._select_shapes)
        self.layers_panel.layers_changed.connect(self._on_model_changed)

    # ------------------------------------------------------------------ #
    # Cycle de vie du projet
    # ------------------------------------------------------------------ #
    def set_project(self, project: Project, path: Path | None = None) -> None:
        self._project_path = path
        self.canvas.set_project(project)
        self.view3d.set_project(project)
        self.layers_panel.set_project(project)
        self.property_panel.set_shape(None)
        self._dirty = False
        self._update_title()
        self.run_validation()

    def new_project(self) -> None:
        if not self._confirm_discard():
            return
        dialog = ProjectSettingsDialog(parent=self)
        if dialog.exec():
            self.set_project(dialog.build_project())

    def edit_project_settings(self) -> None:
        """Modifie les dimensions de valise et réglages après création."""
        project = self.canvas.project
        dialog = ProjectSettingsDialog(project=project, parent=self)
        if not dialog.exec():
            return
        dialog.apply_to(project)
        # Si un empilement existait, il peut ne plus correspondre à la
        # nouvelle profondeur : la validation le signalera en rouge.
        self.canvas.rebuild_scene()
        self.canvas.fit_sheet()
        self.layers_panel.refresh()
        self._on_model_changed()

    def open_project(self) -> None:
        if not self._confirm_discard():
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir un projet", "", _PROJECT_FILTER
        )
        if not filename:
            return
        try:
            project = Project.load(filename)
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.critical(
                self, "Ouverture impossible",
                f"Le fichier n'a pas pu être lu :\n{exc}",
            )
            return
        self.set_project(project, Path(filename))

    def save_project(self) -> bool:
        if self._project_path is None:
            return self.save_project_as()
        self.canvas.project.save(self._project_path)
        self._dirty = False
        self._update_title()
        self.statusBar().showMessage("Projet enregistré.", 3000)
        return True

    def save_project_as(self) -> bool:
        suggested = f"{self.canvas.project.name}{FILE_EXTENSION}"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer le projet", suggested, _PROJECT_FILTER
        )
        if not filename:
            return False
        if not filename.endswith(FILE_EXTENSION):
            filename += FILE_EXTENSION
        self._project_path = Path(filename)
        return self.save_project()

    def _confirm_discard(self) -> bool:
        """Propose d'enregistrer les modifications avant de continuer."""
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self, "Modifications non enregistrées",
            "Enregistrer les modifications du projet courant ?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save_project()
        return answer == QMessageBox.StandardButton.Discard

    def closeEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()

    def _update_title(self) -> None:
        name = self.canvas.project.name
        marker = " *" if self._dirty else ""
        self.setWindowTitle(f"FoamForge {__version__} — {name}{marker}")

    # ------------------------------------------------------------------ #
    # Exports
    # ------------------------------------------------------------------ #
    _EXPORTERS = {
        "svg": ("SVG (*.svg)", export_svg),
        "dxf": ("DXF (*.dxf)", export_dxf),
        "pdf": ("PDF (*.pdf)", export_pdf),
        "png": ("PNG (*.png)", export_png),
        "html": ("HTML (*.html)", export_checklist_html),
    }

    def _export(self, kind: str) -> None:
        # Bloque l'export fabrication si la conception comporte une erreur.
        if kind in ("svg", "dxf") and not self._block_if_errors():
            return
        file_filter, exporter = self._EXPORTERS[kind]
        suggested = f"{self.canvas.project.name}.{kind}"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Exporter", suggested, file_filter
        )
        if not filename:
            return
        try:
            exporter(self.canvas.project, filename)
        except OSError as exc:
            QMessageBox.critical(
                self, "Export impossible", f"Écriture impossible :\n{exc}"
            )
            return
        self.statusBar().showMessage(f"Exporté : {filename}", 5000)

    # ------------------------------------------------------------------ #
    # Formes composées (fusion / soustraction / intersection)
    # ------------------------------------------------------------------ #
    def _run_boolean(self, operation: str) -> None:
        shapes = self.canvas.selected_shapes_ordered()
        try:
            if len(shapes) < 2:
                raise BooleanOperationError(
                    "Sélectionnez au moins deux formes (pour une "
                    "soustraction, la première sélectionnée est la base)."
                )
            if operation == "merge":
                compound = merge_shapes(shapes)
            elif operation == "subtract":
                compound = subtract_shapes(shapes[0], shapes[1:])
            else:
                compound = intersect_shapes(shapes)
        except BooleanOperationError as exc:
            QMessageBox.warning(self, "Forme composée", str(exc))
            return

        answer = QMessageBox.question(
            self, "Forme composée",
            "Supprimer les formes sources ?\n\n"
            "Oui : seule la forme composée reste.\n"
            "Non : les sources sont conservées (la composée s'ajoute).",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return
        if answer == QMessageBox.StandardButton.Yes:
            for shape in shapes:
                self.canvas.project.remove_shape(shape.id)
            self.canvas.rebuild_scene()
        self.canvas.add_shape(compound)
        self.statusBar().showMessage(
            f"Forme composée « {compound.spec.name} » créée.", 4000
        )

    def merge_selection(self) -> None:
        self._run_boolean("merge")

    def subtract_selection(self) -> None:
        self._run_boolean("subtract")

    def intersect_selection(self) -> None:
        self._run_boolean("intersect")

    # ------------------------------------------------------------------ #
    # Vue 3D
    # ------------------------------------------------------------------ #
    def _toggle_3d(self, enabled: bool) -> None:
        self._center_stack.setCurrentWidget(
            self.view3d if enabled else self.canvas
        )
        if enabled:
            self.view3d.refresh()

    # ------------------------------------------------------------------ #
    # Exports xTool P2S
    # ------------------------------------------------------------------ #
    def export_xtool(self) -> None:
        """SVG global prêt pour xTool Creative Space."""
        if not self._block_if_errors():
            return
        suggested = f"{self.canvas.project.name}_xtool.svg"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Exporter pour xTool P2S", suggested, "SVG (*.svg)"
        )
        if not filename:
            return
        try:
            export_xtool_svg(self.canvas.project, filename, XTOOL_P2S)
        except (MachineExportError, OSError) as exc:
            QMessageBox.critical(self, "Export xTool impossible", str(exc))
            return
        self.statusBar().showMessage(f"Exporté pour xTool P2S : {filename}", 5000)

    def export_per_layer(self) -> None:
        """Un SVG par couche de mousse (empilement requis)."""
        if not self._block_if_errors():
            return
        directory = QFileDialog.getExistingDirectory(
            self, "Dossier d'export des couches"
        )
        if not directory:
            return
        try:
            files = export_layers_svg(self.canvas.project, directory, XTOOL_P2S)
        except (MachineExportError, OSError) as exc:
            QMessageBox.critical(self, "Export par couche impossible", str(exc))
            return
        self.statusBar().showMessage(
            f"{len(files)} couche(s) exportée(s) dans {directory}", 5000
        )

    def _block_if_errors(self) -> bool:
        """Refuse les exports fabrication si la validation est rouge."""
        issues = validate_project(self.canvas.project)
        if worst_severity(issues) is Severity.ERROR:
            QMessageBox.warning(
                self, "Export bloqué",
                "La conception comporte des erreurs bloquantes (alertes "
                "rouges). Corrigez-les avant d'exporter pour fabrication.",
            )
            return False
        return True

    # ------------------------------------------------------------------ #
    # Nesting
    # ------------------------------------------------------------------ #
    def run_nesting(self) -> None:
        project = self.canvas.project
        if not project.shapes:
            QMessageBox.information(
                self, "Placement automatique",
                "Ajoutez d'abord des formes à placer.",
            )
            return
        proposals = propose_layouts(project)
        dialog = NestingDialog(proposals, self)
        if dialog.exec():
            proposal = dialog.selected_proposal()
            if proposal is not None:
                proposal.apply(project)
                self.canvas.rebuild_scene()
                self._on_model_changed()

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def run_validation(self) -> None:
        issues = validate_project(self.canvas.project)
        self.alerts_panel.set_issues(issues)
        self._apply_issue_highlights(issues)
        worst = worst_severity(issues)
        text = {
            Severity.ERROR: "⛔ Erreurs bloquantes",
            Severity.WARNING: "⚠️ Améliorations recommandées",
            Severity.OK: "✅ Conception valide",
        }[worst]
        self._status_light.setText(text)
        self._status_light.setStyleSheet(
            f"color: {worst.color}; font-weight: bold;"
        )

    def _apply_issue_highlights(self, issues: list[Issue]) -> None:
        severities: dict[str, Severity] = {}
        for issue in issues:
            for shape_id in issue.shape_ids:
                current = severities.get(shape_id)
                if current is None or issue.severity is Severity.ERROR:
                    severities[shape_id] = issue.severity
        self.canvas.apply_severities(severities)

    # ------------------------------------------------------------------ #
    # Slots divers
    # ------------------------------------------------------------------ #
    def _on_model_changed(self) -> None:
        self._dirty = True
        self._update_title()
        # Le déplacement à la souris doit se refléter dans le panneau,
        # sinon la prochaine édition réappliquerait l'ancienne position.
        self.property_panel.sync_position()
        # La vue 3D suit toutes les modifications (repaint léger).
        self.view3d.refresh()
        self._validation_timer.start()

    def _on_selection_changed(self, shapes: list) -> None:
        self.property_panel.set_shape(shapes[0] if len(shapes) == 1 else None)

    def _on_cursor_moved(self, x_mm: float, y_mm: float) -> None:
        self._cursor_label.setText(f"x: {x_mm:.1f} mm , y: {y_mm:.1f} mm")

    def _select_shapes(self, shape_ids: list[str]) -> None:
        self.canvas.scene().clearSelection()
        for shape_id in shape_ids:
            item = self.canvas.item_for(shape_id)
            if item is not None:
                item.setSelected(True)

    def _set_expert_mode(self, expert: bool) -> None:
        self.property_panel.set_expert_mode(expert)
        self.statusBar().showMessage(
            "Mode expert activé : tous les réglages sont visibles."
            if expert else "Mode débutant : réglages essentiels uniquement.",
            4000,
        )
