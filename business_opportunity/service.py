"""Business intelligence service layer over normalized official market data."""

from collections import defaultdict
from datetime import datetime, timezone

from market_opportunities.catalog import PRODUCT_BY_CODE

BUSINESS_PRODUCT_CODES = (
    "smp",
    "wmp",
    "butter",
    "cheese",
    "ghee",
    "whey_powder",
    "cream",
    "yogurt",
    "uht_milk",
)

CONTINENT_BY_WORLD_BANK_REGION = {
    "East Asia & Pacific": "Asia & Oceania",
    "Europe & Central Asia": "Europe & Asia",
    "Latin America & Caribbean ": "Americas",
    "Middle East, North Africa, Afghanistan & Pakistan": "Africa & Asia",
    "North America": "Americas",
    "South Asia": "Asia",
    "Sub-Saharan Africa ": "Africa",
}


def country_catalog(connection, query=None, region=None, continent=None):
    rows = connection.execute(
        """
        SELECT iso3, iso2, country_name, region, income_level, latitude, longitude
        FROM countries ORDER BY country_name
        """
    ).fetchall()
    result = []
    for row in rows:
        geography = CONTINENT_BY_WORLD_BANK_REGION.get(row["region"], "Other")
        if query and query.casefold() not in row["country_name"].casefold():
            continue
        if region and region != "All regions" and row["region"] != region:
            continue
        if continent and continent != "All continents" and geography != continent:
            continue
        result.append({**dict(row), "continent": geography, "flag": country_flag(row["iso2"])})
    return result


def country_dashboard(connection, iso3):
    country = _country_profile(connection, iso3)
    if not country:
        return None
    product_matrix = _product_matrix(connection, iso3)
    production = _production_summary(connection, iso3)
    overall_score = _overall_score(product_matrix)
    insights = _insights(country, product_matrix, production, overall_score)
    return {
        "country": country,
        "production": production,
        "products": product_matrix,
        "overall_score": overall_score,
        "opportunity_level": opportunity_level(overall_score * 10),
        "insights": insights,
        "last_data_updated": _last_data_updated(connection, iso3),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def country_comparison(connection, iso3_codes):
    comparisons = []
    for iso3 in iso3_codes:
        dashboard = country_dashboard(connection, iso3)
        if dashboard:
            comparisons.append(
                {
                    "country": dashboard["country"]["country_name"],
                    "iso3": iso3,
                    "overall_score": dashboard["overall_score"],
                    "opportunity_level": dashboard["opportunity_level"],
                    "population": dashboard["country"]["population"],
                    "gdp_current_usd": dashboard["country"]["gdp_current_usd"],
                    "top_product": dashboard["products"][0]["product"] if dashboard["products"] else "No trade data",
                }
            )
    return sorted(comparisons, key=lambda row: row["overall_score"], reverse=True)


def rank_countries_for_product(connection, product_code, limit=50):
    rows = connection.execute(
        """
        SELECT c.iso3, c.iso2, c.country_name, c.region, c.latitude, c.longitude,
               s.opportunity_score, s.import_value_usd, s.import_growth_pct,
               s.import_quantity_kg, s.supply_gap_tonnes
        FROM market_scores s JOIN countries c ON c.iso3 = s.country_iso3
        WHERE s.product_code = ? AND s.year = (
            SELECT MAX(year) FROM market_scores WHERE product_code = ?
        )
        ORDER BY s.opportunity_score DESC, s.import_value_usd DESC
        LIMIT ?
        """,
        (product_code, product_code, limit),
    ).fetchall()
    return [
        {
            **dict(row),
            "flag": country_flag(row["iso2"]),
            "continent": CONTINENT_BY_WORLD_BANK_REGION.get(row["region"], "Other"),
            "opportunity_level": opportunity_level(row["opportunity_score"]),
        }
        for row in rows
    ]


def country_flag(iso2):
    if not iso2 or len(iso2) != 2 or not iso2.isalpha():
        return ""
    return "".join(chr(127397 + ord(letter.upper())) for letter in iso2)


def opportunity_level(score):
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Strong"
    if score >= 40:
        return "Moderate"
    if score > 0:
        return "Emerging"
    return "Insufficient official data"


def _country_profile(connection, iso3):
    row = connection.execute(
        """
        SELECT c.iso3, c.iso2, c.country_name, c.region, c.income_level, c.latitude, c.longitude,
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
    if not row:
        return None
    return {
        **dict(row),
        "continent": CONTINENT_BY_WORLD_BANK_REGION.get(row["region"], "Other"),
        "flag": country_flag(row["iso2"]),
        "currency": "Not available from imported official sources",
    }


def _product_matrix(connection, iso3):
    rows = []
    for product_code in BUSINESS_PRODUCT_CODES:
        product = PRODUCT_BY_CODE[product_code]
        score = connection.execute(
            """
            SELECT *
            FROM market_scores
            WHERE country_iso3 = ? AND product_code = ?
            ORDER BY year DESC LIMIT 1
            """,
            (iso3, product_code),
        ).fetchone()
        imports = _latest_trade(connection, iso3, product_code, "Import")
        exports = _latest_trade(connection, iso3, product_code, "Export")
        demand, consumption = _food_balance_values(connection, iso3, product.food_balance_items)
        production = score["production_tonnes"] if score else None
        supply_gap = (
            score["supply_gap_tonnes"]
            if score and score["supply_gap_tonnes"] is not None
            else demand - production
            if demand is not None and production is not None
            else None
        )
        import_dependency = (
            score["import_dependency_ratio"]
            if score and score["import_dependency_ratio"] is not None
            else (imports["quantity_kg"] / 1000) / demand
            if imports["quantity_kg"] is not None and demand not in (None, 0)
            else None
        )
        score_value = score["opportunity_score"] if score else 0.0
        rows.append(
            {
                "product_code": product_code,
                "product": product.name,
                "year": score["year"]
                if score
                else max((year for year in (imports["year"], exports["year"]) if year is not None), default=None),
                "production_tonnes": production,
                "demand_tonnes": demand,
                "consumption_kg_per_capita": consumption,
                "import_quantity_kg": imports["quantity_kg"],
                "import_value_usd": imports["value_usd"],
                "export_quantity_kg": exports["quantity_kg"],
                "export_value_usd": exports["value_usd"],
                "average_import_price_usd_per_kg": _unit_price(imports["value_usd"], imports["quantity_kg"]),
                "supply_gap_tonnes": supply_gap,
                "import_dependency_ratio": import_dependency,
                "import_growth_pct": score["import_growth_pct"] if score else None,
                "opportunity_score": score_value,
                "opportunity_level": opportunity_level(score_value),
                "score_method": score["score_method"] if score else "No scored official import observation is loaded.",
                "import_trend": _trade_history(connection, iso3, product_code, "Import"),
                "export_trend": _trade_history(connection, iso3, product_code, "Export"),
                "top_suppliers": _supplier_analysis(connection, iso3, product_code),
                "top_destinations": _partner_analysis(connection, iso3, product_code, "Export"),
            }
        )
    return sorted(
        rows,
        key=lambda row: (row["opportunity_score"], row["import_value_usd"] or 0),
        reverse=True,
    )


def _production_summary(connection, iso3):
    rows = connection.execute(
        """
        SELECT year, milk_type, quantity_tonnes
        FROM dairy_production WHERE country_iso3 = ?
        ORDER BY year, milk_type
        """,
        (iso3,),
    ).fetchall()
    values = defaultdict(dict)
    for row in rows:
        values[row["year"]][row["milk_type"]] = row["quantity_tonnes"]
    latest_year = max(values, default=None)
    latest = values.get(latest_year, {})
    total = sum(latest.values())
    previous_total = sum(values.get(latest_year - 1, {}).values()) if latest_year else 0
    growth = (total - previous_total) / previous_total * 100 if previous_total else None
    trend = [
        {
            "year": year,
            "total_milk_tonnes": sum(types.values()),
            "cow_milk_tonnes": types.get("Cow milk"),
            "buffalo_milk_tonnes": types.get("Buffalo milk"),
            "goat_milk_tonnes": types.get("Goat milk"),
            "sheep_milk_tonnes": types.get("Sheep milk"),
        }
        for year, types in sorted(values.items())[-5:]
    ]
    return {
        "year": latest_year,
        "total_milk_tonnes": total if latest_year else None,
        "cow_milk_tonnes": latest.get("Cow milk"),
        "buffalo_milk_tonnes": latest.get("Buffalo milk"),
        "goat_milk_tonnes": latest.get("Goat milk"),
        "sheep_milk_tonnes": latest.get("Sheep milk"),
        "growth_pct": growth,
        "five_year_trend": trend,
    }


def _latest_trade(connection, iso3, product_code, flow):
    row = connection.execute(
        """
        SELECT year, quantity_kg, value_usd
        FROM trade_history
        WHERE country_iso3 = ? AND product_code = ? AND flow = ? AND partner_code = '0'
        ORDER BY year DESC LIMIT 1
        """,
        (iso3, product_code, flow),
    ).fetchone()
    return dict(row) if row else {"year": None, "quantity_kg": None, "value_usd": None}


def _trade_history(connection, iso3, product_code, flow):
    return [
        dict(row)
        for row in connection.execute(
            """
            SELECT year, quantity_kg, value_usd
            FROM trade_history
            WHERE country_iso3 = ? AND product_code = ? AND flow = ? AND partner_code = '0'
            ORDER BY year DESC LIMIT 5
            """,
            (iso3, product_code, flow),
        ).fetchall()[::-1]
    ]


def _food_balance_values(connection, iso3, item_names):
    row = connection.execute(
        """
        SELECT
          MAX(CASE WHEN element = 'Domestic supply quantity (tonnes)' AND unit = 't' THEN value END) AS demand_tonnes,
          MAX(CASE WHEN element = 'Food supply quantity (kg/capita/yr)' THEN value END) AS consumption_kg_per_capita
        FROM food_balance
        WHERE country_iso3 = ? AND item IN ({})
        """.format(",".join("?" for _ in item_names)),
        (iso3, *item_names),
    ).fetchone()
    return row["demand_tonnes"], row["consumption_kg_per_capita"]


def _supplier_analysis(connection, iso3, product_code):
    return _partner_analysis(connection, iso3, product_code, "Import")


def _partner_analysis(connection, iso3, product_code, flow):
    records = connection.execute(
        """
        SELECT partner_name, quantity_kg, value_usd, year
        FROM trade_history
        WHERE country_iso3 = ? AND product_code = ? AND flow = ? AND partner_code != '0'
        AND year = (
            SELECT MAX(year) FROM trade_history
            WHERE country_iso3 = ? AND product_code = ? AND flow = ? AND partner_code != '0'
        )
        ORDER BY value_usd DESC LIMIT 10
        """,
        (iso3, product_code, flow, iso3, product_code, flow),
    ).fetchall()
    total_value = sum(record["value_usd"] or 0 for record in records)
    return [
        {
            **dict(record),
            "market_share_pct": (record["value_usd"] or 0) / total_value * 100 if total_value else None,
        }
        for record in records
    ]


def _overall_score(products):
    scored = [row["opportunity_score"] for row in products if row["opportunity_score"] > 0]
    return round(sum(scored) / len(scored) / 10, 1) if scored else 0.0


def competitor_analysis(connection, iso3):
    """Aggregate latest available partner-import values across loaded business products."""
    results = []
    for product_code in BUSINESS_PRODUCT_CODES:
        product = PRODUCT_BY_CODE[product_code]
        for supplier in _supplier_analysis(connection, iso3, product_code):
            results.append(
                {
                    "supplier": supplier["partner_name"],
                    "product": product.name,
                    "value_usd": supplier["value_usd"] or 0,
                    "year": supplier["year"],
                }
            )
    by_supplier = defaultdict(lambda: {"value_usd": 0, "products": set(), "years": set()})
    for result in results:
        aggregate = by_supplier[result["supplier"]]
        aggregate["value_usd"] += result["value_usd"]
        aggregate["products"].add(result["product"])
        aggregate["years"].add(result["year"])
    market_total = sum(item["value_usd"] for item in by_supplier.values())
    return [
        {
            "supplier": supplier,
            "import_value_usd": values["value_usd"],
            "market_share_pct": values["value_usd"] / market_total * 100 if market_total else None,
            "product_categories": ", ".join(sorted(values["products"])),
            "latest_year": max(values["years"]),
        }
        for supplier, values in sorted(by_supplier.items(), key=lambda item: item[1]["value_usd"], reverse=True)
    ]


def _insights(country, products, production, overall_score):
    products_with_trade = [product for product in products if product["import_value_usd"] is not None]
    top = products_with_trade[0] if products_with_trade else None
    growing = max(
        (product for product in products if product["import_growth_pct"] is not None),
        key=lambda product: product["import_growth_pct"],
        default=None,
    )
    supplier = top["top_suppliers"][0] if top and top["top_suppliers"] else None
    sentences = [
        f"{country['country_name']} has an overall official-data business opportunity score of {overall_score:.1f}/10."
    ]
    if top:
        sentences.append(
            f"{top['product']} is the highest-ranked loaded product, with observed imports of "
            f"${top['import_value_usd']:,.0f} in {top['year']}."
        )
    if growing:
        sentences.append(
            f"{growing['product']} has the fastest loaded import growth at {growing['import_growth_pct']:.1f}% year over year."
        )
    if supplier:
        sentences.append(
            f"{supplier['partner_name']} is the leading loaded supplier for {top['product']}, "
            f"with {supplier['market_share_pct']:.1f}% of imported value among imported partner routes."
        )
    if production["total_milk_tonnes"] is not None:
        sentences.append(
            f"Latest loaded fresh-milk production is {production['total_milk_tonnes']:,.0f} tonnes."
        )
    if not top:
        sentences.append(
            "Import product records have not been loaded yet; use the official data updater before making market decisions."
        )
    return sentences


def _last_data_updated(connection, iso3):
    row = connection.execute(
        """
        SELECT MAX(loaded_at) AS loaded_at FROM (
            SELECT loaded_at FROM trade_history WHERE country_iso3 = ?
            UNION ALL SELECT loaded_at FROM dairy_production WHERE country_iso3 = ?
            UNION ALL SELECT loaded_at FROM food_balance WHERE country_iso3 = ?
            UNION ALL SELECT loaded_at FROM population WHERE country_iso3 = ?
            UNION ALL SELECT loaded_at FROM country_economics WHERE country_iso3 = ?
        )
        """,
        (iso3, iso3, iso3, iso3, iso3),
    ).fetchone()
    return row["loaded_at"] if row and row["loaded_at"] else None


def _unit_price(value_usd, quantity_kg):
    return value_usd / quantity_kg if value_usd is not None and quantity_kg not in (None, 0) else None
