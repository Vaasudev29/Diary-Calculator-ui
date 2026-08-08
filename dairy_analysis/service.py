"""Country dairy-sector analysis calculated from imported official observations."""

from collections import defaultdict
from datetime import datetime, timezone


RAW_MILK_PRODUCT = "liquid_milk"
FOOD_BALANCE_ITEM = "Milk - Excluding Butter"


def country_options(connection):
    return connection.execute(
        "SELECT iso3, iso2, country_name, region FROM countries ORDER BY country_name"
    ).fetchall()


def analyze_country(connection, iso3, forecast_years=5):
    country = _country(connection, iso3)
    if country is None:
        return None
    production = _production_by_year(connection, iso3)
    trade = _trade_by_year(connection, iso3)
    food_balance = _food_balance_by_year(connection, iso3)
    population = _population_by_year(connection, iso3)
    livestock = _livestock_by_year(connection, iso3)
    trend = _build_trend(production, trade, food_balance, population, livestock)
    latest = trend[-1] if trend else None
    kpis = _kpis(latest, trend)
    forecast = _forecast(trend, forecast_years)
    sources = _source_status(connection, iso3)
    evidence = _country_evidence(connection, iso3)
    prices = _price_summary(connection, iso3)
    risks = _risks(kpis, sources)
    return {
        "country": country,
        "trend": trend,
        "latest": latest,
        "kpis": kpis,
        "forecast": forecast,
        "prices": prices,
        "sources": sources,
        "evidence": evidence,
        "risks": risks,
        "swot": _swot(kpis, sources),
        "insights": _insights(country, kpis, latest, forecast, sources),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _country(connection, iso3):
    row = connection.execute(
        """
        SELECT c.iso3, c.iso2, c.country_name, c.region, c.income_level,
               p.population, p.year AS population_year,
               e.gdp_current_usd, e.year AS gdp_year
        FROM countries c
        LEFT JOIN population p ON p.country_iso3 = c.iso3
          AND p.year = (SELECT MAX(year) FROM population WHERE country_iso3 = c.iso3)
        LEFT JOIN country_economics e ON e.country_iso3 = c.iso3
          AND e.year = (SELECT MAX(year) FROM country_economics WHERE country_iso3 = c.iso3)
        WHERE c.iso3 = ?
        """,
        (iso3,),
    ).fetchone()
    return dict(row) if row else None


def _production_by_year(connection, iso3):
    values = defaultdict(lambda: {"total_milk_tonnes": 0})
    for row in connection.execute(
        """
        SELECT year, milk_type, quantity_tonnes
        FROM dairy_production WHERE country_iso3 = ? ORDER BY year
        """,
        (iso3,),
    ):
        entry = values[row["year"]]
        entry["total_milk_tonnes"] += row["quantity_tonnes"]
        entry[f"{row['milk_type'].casefold().replace(' ', '_')}_tonnes"] = row["quantity_tonnes"]
    return values


def _trade_by_year(connection, iso3):
    values = defaultdict(dict)
    for row in connection.execute(
        """
        SELECT year, flow, SUM(quantity_kg) AS quantity_kg, SUM(value_usd) AS value_usd
        FROM trade_history
        WHERE country_iso3 = ? AND product_code = ? AND partner_code = '0'
        GROUP BY year, flow
        """,
        (iso3, RAW_MILK_PRODUCT),
    ):
        values[row["year"]][f"{row['flow'].casefold()}_tonnes"] = (
            row["quantity_kg"] / 1000 if row["quantity_kg"] is not None else None
        )
        values[row["year"]][f"{row['flow'].casefold()}_value_usd"] = row["value_usd"]
    return values


def _food_balance_by_year(connection, iso3):
    values = defaultdict(dict)
    for row in connection.execute(
        """
        SELECT year, element, value, unit
        FROM food_balance
        WHERE country_iso3 = ? AND item = ?
        ORDER BY year
        """,
        (iso3, FOOD_BALANCE_ITEM),
    ):
        if row["element"] == "Domestic supply quantity (tonnes)" and row["unit"] == "t":
            values[row["year"]]["official_demand_tonnes"] = row["value"]
        elif row["element"] == "Food supply quantity (kg/capita/yr)":
            values[row["year"]]["official_per_capita_kg"] = row["value"]
    return values


def _population_by_year(connection, iso3):
    return {
        row["year"]: row["population"]
        for row in connection.execute(
            "SELECT year, population FROM population WHERE country_iso3 = ?",
            (iso3,),
        )
    }


def _livestock_by_year(connection, iso3):
    values = defaultdict(float)
    for row in connection.execute(
        """
        SELECT year, value FROM livestock_indicators
        WHERE country_iso3 = ? AND indicator LIKE '%dairy%'
        """,
        (iso3,),
    ):
        values[row["year"]] += row["value"]
    return values


def _build_trend(production, trade, food_balance, population, livestock):
    years = sorted(set(production) | set(trade) | set(food_balance) | set(population) | set(livestock))
    trend = []
    for year in years:
        data = {"year": year, **production.get(year, {}), **trade.get(year, {}), **food_balance.get(year, {})}
        data["population"] = population.get(year)
        data["dairy_animals"] = livestock.get(year)
        production_tonnes = data.get("total_milk_tonnes")
        imports_tonnes = data.get("import_tonnes")
        exports_tonnes = data.get("export_tonnes")
        if data.get("official_demand_tonnes") is not None:
            data["demand_tonnes"] = data["official_demand_tonnes"]
            data["demand_method"] = "FAOSTAT Food Balance Sheets domestic supply"
        elif production_tonnes is not None and imports_tonnes is not None and exports_tonnes is not None:
            data["demand_tonnes"] = production_tonnes + imports_tonnes - exports_tonnes
            data["demand_method"] = "Apparent consumption: production + imports - exports"
        else:
            data["demand_tonnes"] = None
            data["demand_method"] = "Insufficient compatible official inputs"
        demand = data["demand_tonnes"]
        data["self_sufficiency_pct"] = production_tonnes / demand * 100 if production_tonnes is not None and demand not in (None, 0) else None
        data["import_dependency_pct"] = imports_tonnes / demand * 100 if imports_tonnes is not None and demand not in (None, 0) else None
        data["export_ratio_pct"] = exports_tonnes / production_tonnes * 100 if exports_tonnes is not None and production_tonnes not in (None, 0) else None
        data["per_capita_consumption_kg"] = (
            demand * 1000 / data["population"] if demand is not None and data["population"] else data.get("official_per_capita_kg")
        )
        data["milk_yield_kg_per_animal"] = (
            production_tonnes * 1000 / data["dairy_animals"] if production_tonnes is not None and data["dairy_animals"] else None
        )
        data["trade_balance_tonnes"] = (
            exports_tonnes - imports_tonnes if imports_tonnes is not None and exports_tonnes is not None else None
        )
        data["trade_balance_value_usd"] = (
            data.get("export_value_usd", 0) - data.get("import_value_usd", 0)
            if data.get("export_value_usd") is not None and data.get("import_value_usd") is not None
            else None
        )
        trend.append(data)
    return trend


def _kpis(latest, trend):
    if not latest:
        return {"data_available": False}
    previous = trend[-2] if len(trend) > 1 else None
    return {
        "data_available": True,
        "production_growth_pct": _growth(latest.get("total_milk_tonnes"), previous.get("total_milk_tonnes") if previous else None),
        "demand_growth_pct": _growth(latest.get("demand_tonnes"), previous.get("demand_tonnes") if previous else None),
        "import_growth_pct": _growth(latest.get("import_tonnes"), previous.get("import_tonnes") if previous else None),
        "export_growth_pct": _growth(latest.get("export_tonnes"), previous.get("export_tonnes") if previous else None),
        "production_cagr_pct": _cagr([row.get("total_milk_tonnes") for row in trend]),
        "demand_cagr_pct": _cagr([row.get("demand_tonnes") for row in trend]),
        "import_cagr_pct": _cagr([row.get("import_tonnes") for row in trend]),
        "export_cagr_pct": _cagr([row.get("export_tonnes") for row in trend]),
        **{key: latest.get(key) for key in (
            "total_milk_tonnes", "demand_tonnes", "import_tonnes", "export_tonnes",
            "self_sufficiency_pct", "import_dependency_pct", "export_ratio_pct",
            "per_capita_consumption_kg", "milk_yield_kg_per_animal",
            "trade_balance_tonnes", "trade_balance_value_usd", "demand_method",
        )},
    }


def _forecast(trend, years):
    history = [row for row in trend if row.get("total_milk_tonnes") is not None]
    if len(history) < 2:
        return {"available": False, "assumption": "At least two annual production observations are required."}
    start, end = history[0], history[-1]
    production_rate = _cagr([row["total_milk_tonnes"] for row in history])
    demand_history = [row for row in trend if row.get("demand_tonnes") is not None]
    demand_rate = _cagr([row["demand_tonnes"] for row in demand_history]) if len(demand_history) >= 2 else None
    import_history = [row for row in trend if row.get("import_tonnes") is not None]
    import_rate = _cagr([row["import_tonnes"] for row in import_history]) if len(import_history) >= 2 else None
    projections = []
    for offset in range(1, years + 1):
        projections.append(
            {
                "year": end["year"] + offset,
                "production_tonnes": _project(end["total_milk_tonnes"], production_rate, offset),
                "demand_tonnes": _project(demand_history[-1]["demand_tonnes"], demand_rate, offset) if demand_rate is not None else None,
                "import_tonnes": _project(import_history[-1]["import_tonnes"], import_rate, offset) if import_rate is not None else None,
            }
        )
    return {
        "available": True,
        "production_cagr_pct": production_rate,
        "demand_cagr_pct": demand_rate,
        "import_cagr_pct": import_rate,
        "assumption": (
            f"Constant CAGR projection using imported annual observations from {start['year']} to {end['year']}; "
            "not a causal forecast and does not model weather, feed, policy, disease, or structural change."
        ),
        "projections": projections,
    }


def _price_summary(connection, iso3):
    rows = connection.execute(
        """
        SELECT rp.product_name, p.currency_code, p.price_per_normalized_unit, p.observation_date,
               s.source_name, s.source_url
        FROM retail_prices p JOIN retail_products rp ON rp.product_code = p.product_code
        JOIN price_sources s ON s.source_id = p.source_id
        WHERE p.country_iso3 = ? ORDER BY p.observation_date DESC
        """,
        (iso3,),
    ).fetchall()
    return [dict(row) for row in rows]


def _source_status(connection, iso3):
    return {
        "production": bool(connection.execute("SELECT 1 FROM dairy_production WHERE country_iso3 = ? LIMIT 1", (iso3,)).fetchone()),
        "trade": bool(connection.execute("SELECT 1 FROM trade_history WHERE country_iso3 = ? LIMIT 1", (iso3,)).fetchone()),
        "food_balance": bool(connection.execute("SELECT 1 FROM food_balance WHERE country_iso3 = ? LIMIT 1", (iso3,)).fetchone()),
        "population": bool(connection.execute("SELECT 1 FROM population WHERE country_iso3 = ? LIMIT 1", (iso3,)).fetchone()),
        "livestock": bool(connection.execute("SELECT 1 FROM livestock_indicators WHERE country_iso3 = ? LIMIT 1", (iso3,)).fetchone()),
        "retail_prices": bool(_price_summary(connection, iso3)),
        "companies": _has_evidence(connection, iso3, "companies"),
        "policies": _has_evidence(connection, iso3, "policies"),
        "climate_feed_disease": any(
            _has_evidence(connection, iso3, category) for category in ("climate", "feed", "disease", "veterinary")
        ),
    }


def _has_evidence(connection, iso3, category):
    return bool(
        connection.execute(
            "SELECT 1 FROM country_evidence WHERE country_iso3 = ? AND category = ? LIMIT 1",
            (iso3, category),
        ).fetchone()
    )


def _country_evidence(connection, iso3):
    records = connection.execute(
        """
        SELECT category, metric, numeric_value, text_value, unit, data_year, source_title,
               source_url, source_tier, source_type, published_at, extraction_method, notes
        FROM country_evidence
        WHERE country_iso3 = ?
        ORDER BY category, data_year DESC, metric
        """,
        (iso3,),
    ).fetchall()
    grouped = defaultdict(list)
    for record in records:
        grouped[record["category"]].append(dict(record))
    return dict(grouped)


def _risks(kpis, sources):
    risks = []
    if kpis.get("import_dependency_pct") is not None and kpis["import_dependency_pct"] >= 20:
        risks.append("Trade exposure: imported liquid-milk dependency is at least 20% of measured demand.")
    if kpis.get("self_sufficiency_pct") is not None and kpis["self_sufficiency_pct"] < 100:
        risks.append("Supply exposure: domestic production is below measured demand.")
    if not sources["climate_feed_disease"]:
        risks.append("Climate, feed availability, veterinary, and disease surveillance data have not been imported.")
    if not sources["policies"]:
        risks.append("Government policy, subsidy, and regulation sources have not been imported.")
    return risks


def _swot(kpis, sources):
    strengths = ["Official production data is available."] if sources["production"] else ["Production data is not loaded."]
    opportunities = (
        ["Measured import dependency suggests an import-substitution or export-supply opportunity."]
        if kpis.get("import_dependency_pct") not in (None, 0)
        else ["Trade opportunity cannot be assessed until compatible import records are loaded."]
    )
    weaknesses = ["Food Balance Sheet demand is not loaded."] if not sources["food_balance"] else []
    threats = _risks(kpis, sources)
    return {"strengths": strengths, "weaknesses": weaknesses, "opportunities": opportunities, "threats": threats}


def _insights(country, kpis, latest, forecast, sources):
    insights = [f"{country['country_name']} analysis uses only currently imported official observations."]
    if latest and latest.get("total_milk_tonnes") is not None:
        insights.append(f"Latest fresh-milk production: {latest['total_milk_tonnes']:,.0f} tonnes ({latest['year']}).")
    if kpis.get("self_sufficiency_pct") is not None:
        insights.append(f"Measured self-sufficiency: {kpis['self_sufficiency_pct']:.1f}% ({kpis['demand_method']}).")
    if forecast["available"]:
        insights.append(f"Five-year production outlook uses a constant historical CAGR of {forecast['production_cagr_pct']:.2f}%.")
    if not sources["trade"]:
        insights.append("Trade imports/exports and partner analysis are unavailable until UN Comtrade records are loaded.")
    return insights


def _growth(current, previous):
    return (current - previous) / previous * 100 if current is not None and previous not in (None, 0) else None


def _cagr(values):
    valid = [value for value in values if value is not None and value >= 0]
    if len(valid) < 2 or valid[0] == 0:
        return None
    return ((valid[-1] / valid[0]) ** (1 / (len(valid) - 1)) - 1) * 100


def _project(value, rate_pct, offset):
    return value * ((1 + rate_pct / 100) ** offset) if value is not None and rate_pct is not None else None
