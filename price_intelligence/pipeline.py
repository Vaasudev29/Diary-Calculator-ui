"""ETL pipeline for verified retail price records and exchange rates."""

import csv
import json
from contextlib import contextmanager
from datetime import datetime, timezone

import requests

from price_intelligence.catalog import RETAIL_PRODUCT_BY_CODE
from price_intelligence.clients import PublicPriceClient
from price_intelligence.database import utc_now


@contextmanager
def update_audit(connection, source_name, dataset):
    started_at = utc_now()
    cursor = connection.execute(
        "INSERT INTO price_updates (source_name, dataset, status, started_at) VALUES (?, ?, 'started', ?)",
        (source_name, dataset, started_at),
    )
    connection.commit()
    update_id = cursor.lastrowid
    count = [0]
    try:
        yield count
    except (requests.RequestException, ValueError, KeyError, TypeError, OSError, csv.Error) as error:
        connection.execute(
            """
            UPDATE price_updates SET status = 'failed', records_loaded = ?, completed_at = ?, detail = ?
            WHERE id = ?
            """,
            (count[0], utc_now(), str(error), update_id),
        )
        connection.commit()
        raise
    else:
        connection.execute(
            "UPDATE price_updates SET status = 'completed', records_loaded = ?, completed_at = ? WHERE id = ?",
            (count[0], utc_now(), update_id),
        )
        connection.commit()


def seed_product_catalog(connection):
    for product in RETAIL_PRODUCT_BY_CODE.values():
        connection.execute(
            """
            INSERT INTO retail_products (product_code, product_name, normalized_unit)
            VALUES (?, ?, ?)
            ON CONFLICT(product_code) DO UPDATE SET
                product_name = excluded.product_name, normalized_unit = excluded.normalized_unit
            """,
            (product.code, product.name, product.normalized_unit),
        )
    connection.commit()


def import_verified_csv(connection, file_handle, source_name, source_url, source_tier, license_note):
    """Import an authorized public-source CSV after strict normalization and validation."""
    if not source_name.strip() or not source_url.strip() or not license_note.strip():
        raise ValueError("Source name, original source URL, and license/permitted-use note are required.")
    required = {
        "country_iso3",
        "product_code",
        "observation_date",
        "package_description",
        "package_quantity",
        "package_unit",
        "price_low_local",
        "price_high_local",
        "currency_code",
        "source_record_url",
    }
    seed_product_catalog(connection)
    with update_audit(connection, source_name, "Verified retail price CSV") as count:
        source_id = _upsert_source(connection, source_name, source_url, source_tier, license_note)
        reader = csv.DictReader(file_handle)
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            missing = required - set(reader.fieldnames or [])
            raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}.")
        known_countries = {row["iso3"] for row in connection.execute("SELECT iso3 FROM countries")}
        for row in reader:
            normalized = _normalize_csv_row(row, known_countries)
            connection.execute(
                """
                INSERT INTO retail_prices (
                    country_iso3, product_code, observation_date, package_description,
                    package_quantity, package_unit, price_low_local, price_high_local,
                    average_price_local, price_per_normalized_unit, currency_code, source_id,
                    source_record_url, published_at, loaded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(
                    country_iso3, product_code, observation_date, package_description,
                    currency_code, source_id, source_record_url
                ) DO UPDATE SET
                    price_low_local = excluded.price_low_local,
                    price_high_local = excluded.price_high_local,
                    average_price_local = excluded.average_price_local,
                    price_per_normalized_unit = excluded.price_per_normalized_unit,
                    published_at = excluded.published_at,
                    loaded_at = excluded.loaded_at
                """,
                (*normalized[:11], source_id, *normalized[11:], utc_now()),
            )
            count[0] += 1
        connection.commit()
    return count[0]


def sync_exchange_rates(connection, client):
    with update_audit(connection, "Frankfurter", "USD/EUR/INR exchange rates") as count:
        currencies = ("EUR", "INR")
        rates = client.fetch_exchange_rates("USD", currencies)
        for currency, record in rates.items():
            connection.execute(
                """
                INSERT INTO exchange_rates (
                    rate_date, base_currency, quote_currency, rate, source_name, source_url, loaded_at
                ) VALUES (?, 'USD', ?, ?, 'Frankfurter', 'https://frankfurter.dev/', ?)
                ON CONFLICT(rate_date, base_currency, quote_currency, source_name) DO UPDATE SET
                    rate = excluded.rate, loaded_at = excluded.loaded_at
                """,
                (record["date"], currency, record["rate"], utc_now()),
            )
            count[0] += 1
        connection.commit()
    return count[0]


def import_bls_series_config(connection, config_file, start_year, end_year, client=None):
    """Load configured BLS consumer-price series without embedding any retail values in code."""
    client = client or PublicPriceClient()
    seed_product_catalog(connection)
    config = json.load(config_file)
    if not isinstance(config, list) or not config:
        raise ValueError("BLS configuration must be a non-empty JSON list.")
    with update_audit(connection, "U.S. Bureau of Labor Statistics", "Consumer average price series") as count:
        source_id = _upsert_source(
            connection,
            "U.S. Bureau of Labor Statistics Public Data API",
            "https://www.bls.gov/developers/api_signature_v2.htm",
            "Official government statistics",
            "BLS public data API terms apply.",
        )
        known_countries = {row["iso3"] for row in connection.execute("SELECT iso3 FROM countries")}
        for definition in config:
            _validate_bls_definition(definition, known_countries)
            observations = client.fetch_bls_series(definition["series_id"], start_year, end_year)
            for observation in observations:
                period = observation.get("period", "")
                if not period.startswith("M") or period == "M13":
                    continue
                value = float(observation["value"])
                observation_date = f"{observation['year']}-{period[1:]}-01"
                normalized = _normalize_csv_row(
                    {
                        "country_iso3": definition["country_iso3"],
                        "product_code": definition["product_code"],
                        "observation_date": observation_date,
                        "package_description": definition["package_description"],
                        "package_quantity": str(definition["package_quantity"]),
                        "package_unit": definition["package_unit"],
                        "price_low_local": str(value),
                        "price_high_local": str(value),
                        "currency_code": definition.get("currency_code", "USD"),
                        "source_record_url": definition.get(
                            "source_record_url",
                            f"https://api.bls.gov/publicAPI/v2/timeseries/data/{definition['series_id']}",
                        ),
                        "published_at": observation_date,
                    },
                    known_countries,
                )
                connection.execute(
                    """
                    INSERT INTO retail_prices (
                        country_iso3, product_code, observation_date, package_description,
                        package_quantity, package_unit, price_low_local, price_high_local,
                        average_price_local, price_per_normalized_unit, currency_code, source_id,
                        source_record_url, published_at, loaded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(
                        country_iso3, product_code, observation_date, package_description,
                        currency_code, source_id, source_record_url
                    ) DO UPDATE SET
                        price_low_local = excluded.price_low_local,
                        price_high_local = excluded.price_high_local,
                        average_price_local = excluded.average_price_local,
                        price_per_normalized_unit = excluded.price_per_normalized_unit,
                        published_at = excluded.published_at,
                        loaded_at = excluded.loaded_at
                    """,
                    (*normalized[:11], source_id, *normalized[11:], utc_now()),
                )
                count[0] += 1
        connection.commit()
    return count[0]


def _validate_bls_definition(definition, known_countries):
    required = {"series_id", "country_iso3", "product_code", "package_description", "package_quantity", "package_unit"}
    missing = required - set(definition)
    if missing:
        raise ValueError(f"BLS series configuration missing: {', '.join(sorted(missing))}.")
    _normalize_csv_row(
        {
            "country_iso3": definition["country_iso3"],
            "product_code": definition["product_code"],
            "observation_date": "2000-01-01",
            "package_description": definition["package_description"],
            "package_quantity": str(definition["package_quantity"]),
            "package_unit": definition["package_unit"],
            "price_low_local": "0",
            "price_high_local": "0",
            "currency_code": definition.get("currency_code", "USD"),
            "source_record_url": definition.get("source_record_url", "https://www.bls.gov/"),
        },
        known_countries,
    )


def _upsert_source(connection, name, url, tier, license_note):
    connection.execute(
        """
        INSERT INTO price_sources (source_name, source_url, source_tier, license_note, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(source_name, source_url) DO UPDATE SET
            source_tier = excluded.source_tier, license_note = excluded.license_note
        """,
        (name, url, tier, license_note, utc_now()),
    )
    return connection.execute(
        "SELECT source_id FROM price_sources WHERE source_name = ? AND source_url = ?",
        (name, url),
    ).fetchone()["source_id"]


def _normalize_csv_row(row, known_countries):
    country_iso3 = row["country_iso3"].strip().upper()
    product_code = row["product_code"].strip()
    package_unit = row["package_unit"].strip().casefold()
    package_quantity = float(row["package_quantity"])
    price_low = float(row["price_low_local"])
    price_high = float(row["price_high_local"])
    currency = row["currency_code"].strip().upper()
    if country_iso3 not in known_countries:
        raise ValueError(f"Unknown country ISO3 code: {country_iso3}. Load reference countries first.")
    if product_code not in RETAIL_PRODUCT_BY_CODE:
        raise ValueError(f"Unsupported retail product code: {product_code}.")
    if package_unit not in ("kg", "g", "liter", "ml") or package_quantity <= 0:
        raise ValueError(f"Invalid package unit or quantity for {product_code}.")
    if price_low < 0 or price_high < price_low:
        raise ValueError(f"Invalid price range for {product_code}.")
    product = RETAIL_PRODUCT_BY_CODE[product_code]
    normalized_quantity = _normalized_quantity(package_quantity, package_unit, product.normalized_unit)
    average = (price_low + price_high) / 2
    published_at = row.get("published_at", "").strip() or None
    return (
        country_iso3,
        product_code,
        row["observation_date"].strip(),
        row["package_description"].strip(),
        package_quantity,
        package_unit,
        price_low,
        price_high,
        average,
        average / normalized_quantity,
        currency,
        row["source_record_url"].strip(),
        published_at,
    )


def _normalized_quantity(quantity, source_unit, target_unit):
    if target_unit == "kg" and source_unit == "kg":
        return quantity
    if target_unit == "kg" and source_unit == "g":
        return quantity / 1000
    if target_unit == "liter" and source_unit == "liter":
        return quantity
    if target_unit == "liter" and source_unit == "ml":
        return quantity / 1000
    raise ValueError(f"Cannot normalize {source_unit} package to {target_unit} price.")
