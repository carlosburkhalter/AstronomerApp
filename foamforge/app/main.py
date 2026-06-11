"""Lancement de FoamForge.

Usage::

    python -m foamforge.app.main [projet.foamforge.json]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from foamforge import __version__
from foamforge.app.main_window import MainWindow
from foamforge.core.project import Project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="foamforge",
        description="FoamForge — conception de mousses de protection.",
    )
    parser.add_argument(
        "project",
        nargs="?",
        help="Projet à ouvrir (.foamforge.json)",
    )
    parser.add_argument(
        "--version", action="version", version=f"FoamForge {__version__}"
    )
    args = parser.parse_args(argv)

    app = QApplication(sys.argv[:1])
    app.setApplicationName("FoamForge")
    app.setOrganizationName("FoamForge")

    window = MainWindow()
    if args.project:
        try:
            window.set_project(
                Project.load(args.project), Path(args.project)
            )
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.critical(
                window, "Ouverture impossible",
                f"Le projet n'a pas pu être chargé :\n{exc}",
            )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
