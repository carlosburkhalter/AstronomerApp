"""Connexion et schéma de la base SQLite locale.

La base vit dans le dossier de données utilisateur (``~/.foamforge``)
et contient la bibliothèque d'objets. Le schéma est créé à la volée et
versionné via ``PRAGMA user_version`` pour permettre des migrations.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_SCHEMA_VERSION = 1

DEFAULT_CATEGORIES = [
    "caméras astro",
    "roues à filtres",
    "oculaires",
    "filtres",
    "montures",
    "accessoires photo",
    "objectifs photo",
    "drones",
    "batteries",
    "câbles",
    "outils",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS objects (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    name                 TEXT NOT NULL,
    brand                TEXT NOT NULL DEFAULT '',
    category_id          INTEGER REFERENCES categories(id),
    width_mm             REAL NOT NULL DEFAULT 0,
    height_mm            REAL NOT NULL DEFAULT 0,
    depth_mm             REAL NOT NULL DEFAULT 0,
    weight_g             REAL NOT NULL DEFAULT 0,
    -- Contour 2D : JSON [[x, y], ...] en mm, centré sur l'origine.
    -- NULL = utiliser le rectangle width_mm × height_mm.
    contour_json         TEXT,
    recommended_depth_mm REAL NOT NULL DEFAULT 0,
    recommended_margin_mm REAL NOT NULL DEFAULT 1.0,
    tags                 TEXT NOT NULL DEFAULT '',
    created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_objects_category ON objects(category_id);
CREATE INDEX IF NOT EXISTS idx_objects_name ON objects(name);
"""


def default_db_path() -> Path:
    """Chemin par défaut de la base utilisateur."""
    directory = Path.home() / ".foamforge"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "library.sqlite3"


def get_connection(path: str | Path | None = None) -> sqlite3.Connection:
    """Ouvre la base (créée et initialisée si nécessaire).

    ``path=':memory:'`` est supporté pour les tests.
    """
    target = str(path) if path is not None else str(default_db_path())
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    _init_schema(connection)
    return connection


def _init_schema(connection: sqlite3.Connection) -> None:
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version >= DB_SCHEMA_VERSION:
        return
    connection.executescript(_SCHEMA)
    for name in DEFAULT_CATEGORIES:
        connection.execute(
            "INSERT OR IGNORE INTO categories(name) VALUES (?)", (name,)
        )
    connection.execute(f"PRAGMA user_version = {DB_SCHEMA_VERSION}")
    connection.commit()
