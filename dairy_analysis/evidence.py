"""Validated ingestion for cited free dairy-information records."""

import csv
from contextlib import contextmanager
from datetime import datetime, timezone

from dairy_analysis.source_catalog import EVIDENCE_CATEGORIES


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def evidence_audit(connection, dataset):
    started_at = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO data_updates (source, dataset, status, started_at)
        VALUES ('Country evidence import', ?, 'started', ?)
        """,
        (dataset, started_at),
    )
    connection.commit()
    update_id = cursor.lastrowid
    count = [0]
    try:
        yield count
    except (ValueError, KeyError, TypeError, OSError, csv.Error) as error:
        connection.execute(
            """
            UPDATE data_updates SET status = 'failed', records_loaded = ?, completed_at = ?, detail = ?
            WHERE id = ?
            """,
            (count[0], utc_now(), str(error), update_id),
        )
        connection.commit()
        raise
    else:
        connection.execute(
            """
            UPDATE data_updates SET status = 'completed', records_loaded = ?, completed_at = ?
            WHERE id = ?
            """,
            (count[0], utc_now(), update_id),
        )
        connection.commit()


def import_evidence_csv(connection, file_handle, dataset_name="Country dairy evidence"):
    """Import evidence records with a value, source, year, and use-rights note for every row."""
    required = {
        "country_iso3",
        "category",
        "metric",
        "data_year",
        "source_title",
        "source_url",
        "source_tier",
        "source_type",
        "license_note",
    }
    reader = csv.DictReader(file_handle)
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        missing = required - set(reader.fieldnames or [])
        raise ValueError(f"Evidence CSV is missing required columns: {', '.join(sorted(missing))}.")
    countries = {row["iso3"] for row in connection.execute("SELECT iso3 FROM countries")}
    with evidence_audit(connection, dataset_name) as count:
        for row in reader:
            evidence = _normalize_row(row, countries)
            connection.execute(
                """
                INSERT INTO country_evidence (
                    country_iso3, category, metric, numeric_value, text_value, unit, data_year,
                    source_title, source_url, source_tier, source_type, license_note, published_at,
                    extraction_method, notes, loaded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(
                    country_iso3, category, metric, data_year, source_url,
                    source_title, numeric_value, text_value
                ) DO UPDATE SET
                    unit = excluded.unit, source_tier = excluded.source_tier,
                    source_type = excluded.source_type, license_note = excluded.license_note,
                    published_at = excluded.published_at, extraction_method = excluded.extraction_method,
                    notes = excluded.notes, loaded_at = excluded.loaded_at
                """,
                (*evidence, utc_now()),
            )
            count[0] += 1
        connection.commit()
    return count[0]


def _normalize_row(row, countries):
    iso3 = row["country_iso3"].strip().upper()
    category = row["category"].strip().casefold()
    metric = row["metric"].strip()
    data_year = int(row["data_year"])
    numeric_raw = row.get("numeric_value", "").strip()
    text_value = row.get("text_value", "").strip() or None
    numeric_value = float(numeric_raw) if numeric_raw else None
    if iso3 not in countries:
        raise ValueError(f"Unknown country ISO3 code: {iso3}. Load the country catalogue first.")
    if category not in EVIDENCE_CATEGORIES:
        raise ValueError(f"Unsupported evidence category: {category}.")
    if not metric:
        raise ValueError("Evidence metric is required.")
    if not 1900 <= data_year <= 2100:
        raise ValueError(f"Invalid evidence data year: {data_year}.")
    if numeric_value is None and text_value is None:
        raise ValueError(f"Evidence record {metric} needs numeric_value or text_value.")
    for field in ("source_title", "source_url", "source_tier", "source_type", "license_note"):
        if not row[field].strip():
            raise ValueError(f"Evidence {field} is required for {metric}.")
    return (
        iso3,
        category,
        metric,
        numeric_value,
        text_value,
        row.get("unit", "").strip() or None,
        data_year,
        row["source_title"].strip(),
        row["source_url"].strip(),
        row["source_tier"].strip(),
        row["source_type"].strip(),
        row["license_note"].strip(),
        row.get("published_at", "").strip() or None,
        row.get("extraction_method", "").strip() or "Manual source review",
        row.get("notes", "").strip() or None,
    )
