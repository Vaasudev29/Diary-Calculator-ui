"""ETL pipeline for official datasets with validation and update audit records."""

import csv
import io
import math
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone

import requests

from market_opportunities.catalog import (
    FAOSTAT_FOOD_BALANCE_DOMAIN,
    FAOSTAT_FOOD_BALANCE_URL,
    FAOSTAT_MILK_ITEMS,
    FAOSTAT_PRODUCTION_DOMAIN,
    FAOSTAT_PRODUCTION_URL,
    PRODUCT_BY_CODE,
)
from market_opportunities.clients import OfficialDataClient


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def normalized_name(value):
    return "".join(character for character in value.casefold() if character.isalnum())


@contextmanager
def update_audit(connection, source, dataset):
    started_at = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO data_updates (source, dataset, status, started_at)
        VALUES (?, ?, 'started', ?)
        """,
        (source, dataset, started_at),
    )
    connection.commit()
    update_id = cursor.lastrowid
    records_loaded = [0]
    try:
        yield records_loaded
    except (requests.RequestException, ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as error:
        connection.execute(
            """
            UPDATE data_updates
            SET status = 'failed', records_loaded = ?, completed_at = ?, detail = ?
            WHERE id = ?
            """,
            (records_loaded[0], utc_now(), str(error), update_id),
        )
        connection.commit()
        raise
    else:
        connection.execute(
            """
            UPDATE data_updates
            SET status = 'completed', records_loaded = ?, completed_at = ?
            WHERE id = ?
            """,
            (records_loaded[0], utc_now(), update_id),
        )
        connection.commit()


def sync_reference_data(connection, client=None):
    client = client or OfficialDataClient()
    with update_audit(connection, "World Bank Open Data", "Country metadata") as count:
        countries = client.fetch_world_bank_countries()
        m49_areas = client.fetch_un_m49_areas()
        m49_by_name = {
            normalized_name(area["geoAreaName"]): str(area["geoAreaCode"])
            for area in m49_areas
            if area.get("geoAreaCode") and area.get("geoAreaName")
        }
        loaded_at = utc_now()
        for country in countries:
            if country["region"]["id"] == "NA":
                continue
            iso3 = country["id"]
            if not iso3 or len(iso3) != 3:
                continue
            country_name = country["name"]
            connection.execute(
                """
                INSERT INTO countries (
                    iso3, iso2, m49_code, country_name, region, income_level,
                    latitude, longitude, source, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(iso3) DO UPDATE SET
                    iso2 = excluded.iso2,
                    m49_code = excluded.m49_code,
                    country_name = excluded.country_name,
                    region = excluded.region,
                    income_level = excluded.income_level,
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    source = excluded.source,
                    updated_at = excluded.updated_at
                """,
                (
                    iso3,
                    country["iso2Code"],
                    m49_by_name.get(normalized_name(country_name)),
                    country_name,
                    country["region"]["value"],
                    country["incomeLevel"]["value"],
                    float(country["latitude"]) if country["latitude"] else None,
                    float(country["longitude"]) if country["longitude"] else None,
                    "World Bank Open Data + UN Statistics M49",
                    loaded_at,
                ),
            )
            count[0] += 1
        connection.commit()
    return count[0]


def sync_population(connection, start_year, end_year, client=None):
    client = client or OfficialDataClient()
    with update_audit(connection, "World Bank Open Data", "Population") as count:
        observations = client.fetch_world_bank_population(start_year, end_year)
        loaded_at = utc_now()
        known_countries = {row["iso3"] for row in connection.execute("SELECT iso3 FROM countries")}
        for observation in observations:
            iso3 = observation.get("countryiso3code")
            value = observation.get("value")
            year = observation.get("date")
            if iso3 not in known_countries or value is None or not year:
                continue
            population = int(value)
            if population < 0:
                raise ValueError(f"World Bank population is negative for {iso3} in {year}.")
            connection.execute(
                """
                INSERT INTO population (country_iso3, year, population, source, loaded_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(country_iso3, year, source) DO UPDATE SET
                    population = excluded.population, loaded_at = excluded.loaded_at
                """,
                (iso3, int(year), population, "World Bank Open Data", loaded_at),
            )
            count[0] += 1
        connection.commit()
    return count[0]


def sync_gdp(connection, start_year, end_year, client=None):
    client = client or OfficialDataClient()
    with update_audit(connection, "World Bank Open Data", "GDP (current US$)") as count:
        observations = client.fetch_world_bank_gdp(start_year, end_year)
        loaded_at = utc_now()
        known_countries = {row["iso3"] for row in connection.execute("SELECT iso3 FROM countries")}
        for observation in observations:
            iso3 = observation.get("countryiso3code")
            value = observation.get("value")
            year = observation.get("date")
            if iso3 not in known_countries or value is None or not year:
                continue
            gdp = float(value)
            if gdp < 0:
                raise ValueError(f"World Bank GDP is negative for {iso3} in {year}.")
            connection.execute(
                """
                INSERT INTO country_economics (country_iso3, year, gdp_current_usd, source, loaded_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(country_iso3, year, source) DO UPDATE SET
                    gdp_current_usd = excluded.gdp_current_usd, loaded_at = excluded.loaded_at
                """,
                (iso3, int(year), gdp, "World Bank Open Data", loaded_at),
            )
            count[0] += 1
        connection.commit()
    return count[0]


WORLD_BANK_INDICATORS = {
    "SP.URB.TOTL.IN.ZS": ("Urban population (% of total population)", "%"),
    "FP.CPI.TOTL.ZG": ("Inflation, consumer prices (annual %)", "%"),
    "NY.GDP.PCAP.CD": ("GDP per capita (current US$)", "current US$"),
}


def sync_world_bank_indicators(connection, start_year, end_year, client=None):
    """Load selected annual WDI indicators without replacing dedicated population/GDP facts."""
    client = client or OfficialDataClient()
    known_countries = {row["iso3"] for row in connection.execute("SELECT iso3 FROM countries")}
    with update_audit(connection, "World Bank Open Data", "WDI economic and demographic indicators") as count:
        loaded_at = utc_now()
        for indicator_code, (indicator_name, unit) in WORLD_BANK_INDICATORS.items():
            for observation in client.fetch_world_bank_indicator(indicator_code, start_year, end_year):
                iso3 = observation.get("countryiso3code")
                value = observation.get("value")
                year = observation.get("date")
                if iso3 not in known_countries or value is None or not year:
                    continue
                numeric_value = float(value)
                if not math.isfinite(numeric_value):
                    raise ValueError(f"World Bank {indicator_code} is not finite for {iso3} in {year}.")
                _upsert_indicator(
                    connection,
                    iso3,
                    int(year),
                    indicator_code,
                    indicator_name,
                    numeric_value,
                    unit,
                    "World Bank Open Data",
                    f"https://api.worldbank.org/v2/country/all/indicator/{indicator_code}",
                    loaded_at,
                )
                count[0] += 1
        connection.commit()
    return count[0]


def sync_nasa_power_climate(connection, country_iso3_codes, start_year, end_year, client=None):
    """Load country-coordinate climate context from NASA POWER's public monthly endpoint."""
    client = client or OfficialDataClient()
    countries = {
        row["iso3"]: (row["latitude"], row["longitude"])
        for row in connection.execute(
            "SELECT iso3, latitude, longitude FROM countries WHERE iso3 IN ({})".format(
                ",".join("?" for _ in country_iso3_codes)
            ),
            tuple(country_iso3_codes),
        )
    }
    unknown = set(country_iso3_codes) - set(countries)
    if unknown:
        raise ValueError(f"Unknown country ISO3 codes: {', '.join(sorted(unknown))}.")
    without_coordinates = [iso3 for iso3, coordinates in countries.items() if None in coordinates]
    if without_coordinates:
        raise ValueError(f"Countries without coordinates: {', '.join(sorted(without_coordinates))}.")
    with update_audit(connection, "NASA POWER", "Monthly climate context") as count:
        loaded_at = utc_now()
        for iso3, (latitude, longitude) in countries.items():
            parameters = client.fetch_nasa_power_monthly(latitude, longitude, start_year, end_year)
            source_url = (
                "https://power.larc.nasa.gov/api/temporal/monthly/point"
                f"?parameters=T2M,PRECTOTCORR&community=AG&longitude={longitude:.4f}"
                f"&latitude={latitude:.4f}&format=JSON&start={start_year}&end={end_year}"
            )
            for year in range(int(start_year), int(end_year) + 1):
                temperatures = _nasa_monthly_values(parameters["T2M"], year)
                precipitation = _nasa_monthly_values(parameters["PRECTOTCORR"], year)
                if temperatures:
                    _upsert_indicator(
                        connection,
                        iso3,
                        year,
                        "nasa_power_t2m_mean",
                        "Mean 2 m air temperature",
                        sum(temperatures) / len(temperatures),
                        "degC",
                        "NASA POWER",
                        source_url,
                        loaded_at,
                    )
                    count[0] += 1
                if precipitation:
                    _upsert_indicator(
                        connection,
                        iso3,
                        year,
                        "nasa_power_prectotcorr_mean",
                        "Mean corrected precipitation",
                        sum(precipitation) / len(precipitation),
                        "mm/day",
                        "NASA POWER",
                        source_url,
                        loaded_at,
                    )
                    count[0] += 1
        connection.commit()
    return count[0]


def _nasa_monthly_values(monthly_values, year):
    values = []
    for month in range(1, 13):
        value = monthly_values.get(f"{year}{month:02d}")
        if value is None:
            continue
        numeric_value = float(value)
        if math.isfinite(numeric_value) and numeric_value > -900:
            values.append(numeric_value)
    return values


def _upsert_indicator(
    connection,
    country_iso3,
    year,
    indicator_code,
    indicator_name,
    value,
    unit,
    source,
    source_url,
    loaded_at,
):
    connection.execute(
        """
        INSERT INTO country_indicators (
            country_iso3, year, indicator_code, indicator_name, value, unit, source, source_url, loaded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(country_iso3, year, indicator_code, source) DO UPDATE SET
            indicator_name = excluded.indicator_name,
            value = excluded.value,
            unit = excluded.unit,
            source_url = excluded.source_url,
            loaded_at = excluded.loaded_at
        """,
        (country_iso3, year, indicator_code, indicator_name, value, unit, source, source_url, loaded_at),
    )


def sync_trade(
    connection,
    country_iso3_codes,
    years,
    product_codes,
    include_partners=False,
    client=None,
    progress_callback=None,
):
    """Import annual Comtrade totals; partner rows are optional due to API volume."""
    client = client or OfficialDataClient()
    countries = {
        row["iso3"]: row["m49_code"]
        for row in connection.execute(
            "SELECT iso3, m49_code FROM countries WHERE iso3 IN ({})".format(
                ",".join("?" for _ in country_iso3_codes)
            ),
            tuple(country_iso3_codes),
        )
    }
    unknown = set(country_iso3_codes) - set(countries)
    if unknown:
        raise ValueError(f"Unknown country ISO3 codes: {', '.join(sorted(unknown))}.")
    no_m49 = [iso3 for iso3, m49_code in countries.items() if not m49_code]
    if no_m49:
        raise ValueError(
            "These World Bank countries could not be matched to a UN M49 reporter code: "
            + ", ".join(sorted(no_m49))
        )

    products = [PRODUCT_BY_CODE[code] for code in product_codes]
    expected_requests = len(countries) * len(years) * len(products) * 2 * (2 if include_partners else 1)
    completed_requests = 0
    with update_audit(connection, "UN Comtrade", "Annual dairy trade") as count:
        loaded_at = utc_now()
        for iso3, m49_code in countries.items():
            for year in years:
                for product in products:
                    for flow in ("Import", "Export"):
                        for partners in ((False, True) if include_partners else (False,)):
                            records = client.fetch_comtrade(year, m49_code, product.hs_code, flow, partners)
                            _load_trade_records(
                                connection,
                                records,
                                iso3,
                                int(year),
                                flow,
                                product.code,
                                product.name,
                                loaded_at,
                            )
                            count[0] += len(records)
                            completed_requests += 1
                            if progress_callback:
                                progress_callback(completed_requests, expected_requests)
        connection.commit()
    return count[0]


def _load_trade_records(
    connection,
    records,
    country_iso3,
    year,
    flow,
    product_code,
    product_name,
    loaded_at,
):
    for record in records:
        partner_code = str(record.get("partnerCode", "0"))
        partner_name = record.get("partnerDesc") or ("World" if partner_code == "0" else partner_code)
        quantity = record.get("netWgt")
        if quantity is None:
            quantity = record.get("qty")
        value = record.get("primaryValue")
        if quantity is not None and float(quantity) < 0:
            raise ValueError(f"UN Comtrade quantity is negative for {country_iso3}, {product_code}, {year}.")
        if value is not None and float(value) < 0:
            raise ValueError(f"UN Comtrade value is negative for {country_iso3}, {product_code}, {year}.")
        connection.execute(
            """
            INSERT INTO trade_history (
                country_iso3, year, flow, product_code, product_name, partner_code,
                partner_name, quantity_kg, value_usd, source, loaded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(country_iso3, year, flow, product_code, partner_code, source)
            DO UPDATE SET
                product_name = excluded.product_name,
                partner_name = excluded.partner_name,
                quantity_kg = excluded.quantity_kg,
                value_usd = excluded.value_usd,
                loaded_at = excluded.loaded_at
            """,
            (
                country_iso3,
                year,
                flow,
                product_code,
                product_name,
                partner_code,
                partner_name,
                float(quantity) if quantity is not None else None,
                float(value) if value is not None else None,
                "UN Comtrade",
                loaded_at,
            ),
        )


def sync_faostat_production(connection, url=None, progress_callback=None, client=None):
    """Stream official FAOSTAT livestock production data and load milk species rows."""
    client = client or OfficialDataClient()
    with update_audit(connection, "FAOSTAT", "Livestock Primary Production") as count:
        source_url = url or client.fetch_faostat_bulk_url(
            FAOSTAT_PRODUCTION_DOMAIN,
            FAOSTAT_PRODUCTION_URL.rsplit("/", 1)[-1],
        )
        countries_by_m49 = {
            row["m49_code"]: row["iso3"]
            for row in connection.execute("SELECT iso3, m49_code FROM countries WHERE m49_code IS NOT NULL")
        }
        loaded_at = utc_now()
        for row in _iter_faostat_rows(source_url, progress_callback, client.session):
            item = row.get("Item")
            iso3 = countries_by_m49.get(str(row.get("Area Code (M49)", "")).lstrip("0"))
            if (
                iso3
                and item
                and "dairy" in item.casefold()
                and row.get("Element") == "Producing Animals/Slaughtered"
                and row.get("Unit") in ("An", "1000 An")
            ):
                value = float(row["Value"])
                multiplier = 1000 if row["Unit"] == "1000 An" else 1
                if value < 0:
                    raise ValueError(f"FAOSTAT livestock count is negative for {iso3} in {row['Year']}.")
                connection.execute(
                    """
                    INSERT INTO livestock_indicators (
                        country_iso3, year, indicator, value, unit, source, loaded_at
                    ) VALUES (?, ?, ?, ?, 'An', ?, ?)
                    ON CONFLICT(country_iso3, year, indicator, source) DO UPDATE SET
                        value = excluded.value, loaded_at = excluded.loaded_at
                    """,
                    (
                        iso3,
                        int(row["Year"]),
                        item,
                        value * multiplier,
                        "FAOSTAT",
                        loaded_at,
                    ),
                )
                count[0] += 1
            if item not in FAOSTAT_MILK_ITEMS or row.get("Element") != "Production":
                continue
            if row.get("Unit") != "t":
                continue
            if not iso3:
                continue
            quantity = float(row["Value"])
            if quantity < 0:
                raise ValueError(f"FAOSTAT production is negative for {iso3} in {row['Year']}.")
            connection.execute(
                """
                INSERT INTO dairy_production (
                    country_iso3, year, milk_type, quantity_tonnes, source, loaded_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(country_iso3, year, milk_type, source) DO UPDATE SET
                    quantity_tonnes = excluded.quantity_tonnes, loaded_at = excluded.loaded_at
                """,
                (
                    iso3,
                    int(row["Year"]),
                    FAOSTAT_MILK_ITEMS[item],
                    quantity,
                    "FAOSTAT",
                    loaded_at,
                ),
            )
            count[0] += 1
        connection.commit()
    return count[0]


def sync_faostat_food_balance(connection, url=None, progress_callback=None, client=None):
    """Stream FAOSTAT food balance observations for dairy demand and per-capita context."""
    client = client or OfficialDataClient()
    relevant_items = {item for product in PRODUCT_BY_CODE.values() for item in product.food_balance_items}
    relevant_elements = {
        "Domestic supply quantity (tonnes)",
        "Food supply quantity (kg/capita/yr)",
    }
    with update_audit(connection, "FAOSTAT", "Food Balance Sheets") as count:
        source_url = url or client.fetch_faostat_bulk_url(
            FAOSTAT_FOOD_BALANCE_DOMAIN,
            FAOSTAT_FOOD_BALANCE_URL.rsplit("/", 1)[-1],
        )
        countries_by_m49 = {
            row["m49_code"]: row["iso3"]
            for row in connection.execute("SELECT iso3, m49_code FROM countries WHERE m49_code IS NOT NULL")
        }
        loaded_at = utc_now()
        for row in _iter_faostat_rows(source_url, progress_callback, client.session):
            if row.get("Item") not in relevant_items or row.get("Element") not in relevant_elements:
                continue
            iso3 = countries_by_m49.get(str(row.get("Area Code (M49)", "")).lstrip("0"))
            if not iso3:
                continue
            value = float(row["Value"])
            if value < 0:
                raise ValueError(f"FAOSTAT food balance is negative for {iso3} in {row['Year']}.")
            connection.execute(
                """
                INSERT INTO food_balance (
                    country_iso3, year, item, element, value, unit, source, loaded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(country_iso3, year, item, element, source) DO UPDATE SET
                    value = excluded.value, unit = excluded.unit, loaded_at = excluded.loaded_at
                """,
                (
                    iso3,
                    int(row["Year"]),
                    row["Item"],
                    row["Element"],
                    value,
                    row["Unit"],
                    "FAOSTAT",
                    loaded_at,
                ),
            )
            count[0] += 1
        connection.commit()
    return count[0]


def _iter_faostat_rows(url, progress_callback, session):
    response = session.get(url, stream=True, timeout=300)
    response.raise_for_status()
    with tempfile.TemporaryFile() as download_file:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                download_file.write(chunk)
        download_file.seek(0)
        with zipfile.ZipFile(download_file) as archive:
            csv_members = [
                member
                for member in archive.namelist()
                if member.casefold().endswith(".csv") and "flag" not in member.casefold()
            ]
            if len(csv_members) != 1:
                raise ValueError("FAOSTAT archive does not contain exactly one normalized CSV data file.")
            with archive.open(csv_members[0]) as binary_file:
                reader = csv.DictReader(io.TextIOWrapper(binary_file, encoding="utf-8-sig"))
                for index, row in enumerate(reader, start=1):
                    if progress_callback and index % 100000 == 0:
                        progress_callback(index, None)
                    yield row
