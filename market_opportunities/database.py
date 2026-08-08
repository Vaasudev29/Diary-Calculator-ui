"""SQLite persistence for raw market facts, score outputs, and update audit records."""

import os
from pathlib import Path
import sys

# Conda on Windows can omit this directory from PATH for direct `python -m` update commands.
_dll_directory = None
if os.name == "nt" and hasattr(os, "add_dll_directory"):
    conda_dll_directory = Path(sys.prefix) / "Library" / "bin"
    if conda_dll_directory.is_dir():
        os.environ["PATH"] = str(conda_dll_directory) + os.pathsep + os.environ.get("PATH", "")
        _dll_directory = os.add_dll_directory(str(conda_dll_directory))

import sqlite3


def default_database_path():
    return Path(__file__).resolve().parent.parent / "data" / "market_opportunities.db"


def connect(database_path=None):
    path = Path(database_path or default_database_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(os.fspath(path), timeout=60)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 60000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    return connection


def initialize(connection):
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS countries (
            iso3 TEXT PRIMARY KEY,
            iso2 TEXT,
            m49_code TEXT UNIQUE,
            country_name TEXT NOT NULL,
            region TEXT,
            income_level TEXT,
            latitude REAL,
            longitude REAL,
            source TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS population (
            country_iso3 TEXT NOT NULL REFERENCES countries(iso3),
            year INTEGER NOT NULL,
            population INTEGER NOT NULL CHECK (population >= 0),
            source TEXT NOT NULL,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (country_iso3, year, source)
        );

        CREATE TABLE IF NOT EXISTS country_economics (
            country_iso3 TEXT NOT NULL REFERENCES countries(iso3),
            year INTEGER NOT NULL,
            gdp_current_usd REAL NOT NULL CHECK (gdp_current_usd >= 0),
            source TEXT NOT NULL,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (country_iso3, year, source)
        );

        CREATE TABLE IF NOT EXISTS country_indicators (
            country_iso3 TEXT NOT NULL REFERENCES countries(iso3),
            year INTEGER NOT NULL,
            indicator_code TEXT NOT NULL,
            indicator_name TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            source TEXT NOT NULL,
            source_url TEXT NOT NULL,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (country_iso3, year, indicator_code, source)
        );

        CREATE TABLE IF NOT EXISTS dairy_production (
            country_iso3 TEXT NOT NULL REFERENCES countries(iso3),
            year INTEGER NOT NULL,
            milk_type TEXT NOT NULL,
            quantity_tonnes REAL NOT NULL CHECK (quantity_tonnes >= 0),
            source TEXT NOT NULL,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (country_iso3, year, milk_type, source)
        );

        CREATE TABLE IF NOT EXISTS livestock_indicators (
            country_iso3 TEXT NOT NULL REFERENCES countries(iso3),
            year INTEGER NOT NULL,
            indicator TEXT NOT NULL,
            value REAL NOT NULL CHECK (value >= 0),
            unit TEXT NOT NULL,
            source TEXT NOT NULL,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (country_iso3, year, indicator, source)
        );

        CREATE TABLE IF NOT EXISTS country_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_iso3 TEXT NOT NULL REFERENCES countries(iso3),
            category TEXT NOT NULL,
            metric TEXT NOT NULL,
            numeric_value REAL,
            text_value TEXT,
            unit TEXT,
            data_year INTEGER NOT NULL CHECK (data_year BETWEEN 1900 AND 2100),
            source_title TEXT NOT NULL,
            source_url TEXT NOT NULL,
            source_tier TEXT NOT NULL,
            source_type TEXT NOT NULL,
            license_note TEXT NOT NULL,
            published_at TEXT,
            extraction_method TEXT NOT NULL,
            notes TEXT,
            loaded_at TEXT NOT NULL,
            CHECK (numeric_value IS NOT NULL OR text_value IS NOT NULL),
            UNIQUE (
                country_iso3, category, metric, data_year, source_url,
                source_title, numeric_value, text_value
            )
        );

        CREATE TABLE IF NOT EXISTS food_balance (
            country_iso3 TEXT NOT NULL REFERENCES countries(iso3),
            year INTEGER NOT NULL,
            item TEXT NOT NULL,
            element TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            source TEXT NOT NULL,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (country_iso3, year, item, element, source)
        );

        CREATE TABLE IF NOT EXISTS trade_history (
            country_iso3 TEXT NOT NULL REFERENCES countries(iso3),
            year INTEGER NOT NULL,
            flow TEXT NOT NULL CHECK (flow IN ('Import', 'Export')),
            product_code TEXT NOT NULL,
            product_name TEXT NOT NULL,
            partner_code TEXT NOT NULL,
            partner_name TEXT NOT NULL,
            quantity_kg REAL,
            value_usd REAL,
            source TEXT NOT NULL,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (
                country_iso3, year, flow, product_code, partner_code, source
            )
        );

        CREATE TABLE IF NOT EXISTS market_scores (
            country_iso3 TEXT NOT NULL REFERENCES countries(iso3),
            product_code TEXT NOT NULL,
            year INTEGER NOT NULL,
            demand_tonnes REAL,
            production_tonnes REAL,
            import_quantity_kg REAL,
            import_value_usd REAL,
            import_growth_pct REAL,
            supply_gap_tonnes REAL,
            self_sufficiency_ratio REAL,
            import_dependency_ratio REAL,
            market_growth_score REAL,
            opportunity_score REAL NOT NULL,
            score_method TEXT NOT NULL,
            calculated_at TEXT NOT NULL,
            PRIMARY KEY (country_iso3, product_code, year)
        );

        CREATE TABLE IF NOT EXISTS data_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            dataset TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('started', 'completed', 'failed')),
            records_loaded INTEGER NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            detail TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_trade_market
        ON trade_history(product_code, flow, year, country_iso3);
        CREATE INDEX IF NOT EXISTS idx_scores_rank
        ON market_scores(product_code, year, opportunity_score DESC);
        CREATE INDEX IF NOT EXISTS idx_economics_country
        ON country_economics(country_iso3, year DESC);
        CREATE INDEX IF NOT EXISTS idx_indicators_country
        ON country_indicators(country_iso3, indicator_code, year DESC);
        CREATE INDEX IF NOT EXISTS idx_livestock_country
        ON livestock_indicators(country_iso3, year DESC);
        CREATE INDEX IF NOT EXISTS idx_evidence_country_category
        ON country_evidence(country_iso3, category, data_year DESC);
        """
    )
    connection.commit()
