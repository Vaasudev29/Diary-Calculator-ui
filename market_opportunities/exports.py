"""Traceable consolidated exports for locally imported dairy-intelligence facts."""

import csv
import json
from pathlib import Path

from market_opportunities.reports import build_xlsx


def consolidated_facts(connection):
    countries = {
        row["iso3"]: row["country_name"]
        for row in connection.execute("SELECT iso3, country_name FROM countries")
    }
    facts = []
    _append_rows(
        facts,
        connection.execute("SELECT country_iso3, year, population, source, loaded_at FROM population"),
        countries,
        "Demographics",
        "Population",
        "population",
        "people",
        "https://data.worldbank.org/indicator/SP.POP.TOTL",
    )
    _append_rows(
        facts,
        connection.execute("SELECT country_iso3, year, gdp_current_usd, source, loaded_at FROM country_economics"),
        countries,
        "Economics",
        "GDP (current US$)",
        "gdp_current_usd",
        "current US$",
        "https://data.worldbank.org/indicator/NY.GDP.MKTP.CD",
    )
    _append_rows(
        facts,
        connection.execute(
            "SELECT country_iso3, year, indicator_name, indicator_code, value, unit, source, source_url, loaded_at "
            "FROM country_indicators"
        ),
        countries,
        "Indicator",
        None,
        "value",
        None,
        None,
        metric_column="indicator_name",
        source_url_column="source_url",
    )
    _append_rows(
        facts,
        connection.execute("SELECT country_iso3, year, milk_type, quantity_tonnes, source, loaded_at FROM dairy_production"),
        countries,
        "Production",
        None,
        "quantity_tonnes",
        "tonnes",
        "https://www.fao.org/faostat/",
        metric_column="milk_type",
    )
    _append_rows(
        facts,
        connection.execute("SELECT country_iso3, year, indicator, value, unit, source, loaded_at FROM livestock_indicators"),
        countries,
        "Livestock",
        None,
        "value",
        None,
        "https://www.fao.org/faostat/",
        metric_column="indicator",
    )
    _append_rows(
        facts,
        connection.execute("SELECT country_iso3, year, item, value, unit, source, loaded_at FROM food_balance"),
        countries,
        "Food balance",
        None,
        "value",
        None,
        "https://www.fao.org/faostat/",
        metric_column="item",
    )
    _append_rows(
        facts,
        connection.execute(
            "SELECT country_iso3, year, flow, product_name, quantity_kg, source, loaded_at FROM trade_history "
            "WHERE quantity_kg IS NOT NULL"
        ),
        countries,
        "Trade",
        None,
        "quantity_kg",
        "kg",
        "https://comtradeplus.un.org/",
        metric_column="product_name",
        metric_prefix_column="flow",
    )
    _append_rows(
        facts,
        connection.execute(
            "SELECT country_iso3, year, flow, product_name, value_usd, source, loaded_at FROM trade_history "
            "WHERE value_usd IS NOT NULL"
        ),
        countries,
        "Trade",
        None,
        "value_usd",
        "current US$",
        "https://comtradeplus.un.org/",
        metric_column="product_name",
        metric_prefix_column="flow",
    )
    _append_rows(
        facts,
        connection.execute(
            "SELECT country_iso3, data_year AS year, metric, COALESCE(numeric_value, text_value) AS value, "
            "unit, source_title AS source, source_url, loaded_at FROM country_evidence"
        ),
        countries,
        "Cited evidence",
        None,
        "value",
        None,
        None,
        source_url_column="source_url",
    )
    return sorted(facts, key=lambda fact: (fact["Country ISO3"], fact["Year"], fact["Domain"], fact["Metric"]))


def write_consolidated_exports(connection, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    facts = consolidated_facts(connection)
    csv_path = destination / "dairy_intelligence_facts.csv"
    json_path = destination / "dairy_intelligence_facts.json"
    xlsx_path = destination / "dairy_intelligence_facts.xlsx"
    headers = list(_empty_fact())
    with csv_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        writer.writerows(facts)
    json_path.write_text(json.dumps(facts, indent=2, ensure_ascii=False), encoding="utf-8")
    xlsx_path.write_bytes(build_xlsx(facts, "Dairy intelligence"))
    return {"facts": len(facts), "csv": str(csv_path), "json": str(json_path), "xlsx": str(xlsx_path)}


def _append_rows(
    facts,
    rows,
    countries,
    domain,
    metric,
    value_column,
    unit,
    source_url,
    metric_column=None,
    metric_prefix_column=None,
    source_url_column=None,
):
    for row in rows:
        resolved_metric = row[metric_column] if metric_column else metric
        if metric_prefix_column:
            resolved_metric = f"{row[metric_prefix_column]} {resolved_metric}"
        facts.append(
            {
                **_empty_fact(),
                "Country ISO3": row["country_iso3"],
                "Country": countries.get(row["country_iso3"], row["country_iso3"]),
                "Year": row["year"],
                "Domain": domain,
                "Metric": resolved_metric,
                "Value": row[value_column],
                "Unit": row["unit"] if unit is None else unit,
                "Source": row["source"],
                "Source URL": row[source_url_column] if source_url_column else source_url,
                "Loaded at": row["loaded_at"],
            }
        )


def _empty_fact():
    return {
        "Country ISO3": "",
        "Country": "",
        "Year": "",
        "Domain": "",
        "Metric": "",
        "Value": "",
        "Unit": "",
        "Source": "",
        "Source URL": "",
        "Loaded at": "",
    }
