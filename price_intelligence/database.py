"""SQLite persistence for sourced retail-price observations and update audits."""

from datetime import datetime, timezone


def initialize(connection):
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS price_sources (
            source_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            source_tier TEXT NOT NULL,
            license_note TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(source_name, source_url)
        );

        CREATE TABLE IF NOT EXISTS retail_products (
            product_code TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            normalized_unit TEXT NOT NULL CHECK (normalized_unit IN ('kg', 'liter'))
        );

        CREATE TABLE IF NOT EXISTS retail_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_iso3 TEXT NOT NULL REFERENCES countries(iso3),
            product_code TEXT NOT NULL REFERENCES retail_products(product_code),
            observation_date TEXT NOT NULL,
            package_description TEXT NOT NULL,
            package_quantity REAL NOT NULL CHECK (package_quantity > 0),
            package_unit TEXT NOT NULL CHECK (package_unit IN ('kg', 'g', 'liter', 'ml')),
            price_low_local REAL NOT NULL CHECK (price_low_local >= 0),
            price_high_local REAL NOT NULL CHECK (price_high_local >= price_low_local),
            average_price_local REAL NOT NULL CHECK (average_price_local >= price_low_local),
            price_per_normalized_unit REAL NOT NULL CHECK (price_per_normalized_unit >= 0),
            currency_code TEXT NOT NULL,
            source_id INTEGER NOT NULL REFERENCES price_sources(source_id),
            source_record_url TEXT NOT NULL,
            published_at TEXT,
            loaded_at TEXT NOT NULL,
            UNIQUE (
                country_iso3, product_code, observation_date, package_description,
                currency_code, source_id, source_record_url
            )
        );

        CREATE TABLE IF NOT EXISTS exchange_rates (
            rate_date TEXT NOT NULL,
            base_currency TEXT NOT NULL,
            quote_currency TEXT NOT NULL,
            rate REAL NOT NULL CHECK (rate > 0),
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (rate_date, base_currency, quote_currency, source_name)
        );

        CREATE TABLE IF NOT EXISTS price_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL,
            dataset TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('started', 'completed', 'failed')),
            records_loaded INTEGER NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            detail TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_retail_prices_country_product_date
        ON retail_prices(country_iso3, product_code, observation_date DESC);
        CREATE INDEX IF NOT EXISTS idx_retail_prices_coverage
        ON retail_prices(country_iso3, observation_date DESC);
        """
    )
    connection.commit()


def utc_now():
    return datetime.now(timezone.utc).isoformat()
