"""Read models for dashboard, country details, comparisons, and search."""

from market_opportunities.catalog import PRODUCT_BY_CODE


def product_scores(connection, product_code, limit=100, search=None):
    year = latest_score_year(connection, product_code)
    if year is None:
        return []
    parameters = [product_code, year]
    search_filter = ""
    if search:
        search_filter = "AND lower(c.country_name) LIKE ?"
        parameters.append(f"%{search.casefold()}%")
    parameters.append(limit)
    return connection.execute(
        f"""
        SELECT c.iso3, c.country_name, c.region, c.income_level, c.latitude, c.longitude,
               s.year, s.import_value_usd, s.import_quantity_kg, s.import_growth_pct,
               s.supply_gap_tonnes, s.self_sufficiency_ratio, s.import_dependency_ratio,
               s.market_growth_score, s.opportunity_score, s.score_method
        FROM market_scores s
        JOIN countries c ON c.iso3 = s.country_iso3
        WHERE s.product_code = ? AND s.year = ? {search_filter}
        ORDER BY s.opportunity_score DESC, s.import_value_usd DESC
        LIMIT ?
        """,
        tuple(parameters),
    ).fetchall()


def latest_score_year(connection, product_code):
    row = connection.execute(
        "SELECT MAX(year) AS year FROM market_scores WHERE product_code = ?",
        (product_code,),
    ).fetchone()
    return row["year"] if row and row["year"] else None


def latest_data_year(connection):
    row = connection.execute("SELECT MAX(year) AS year FROM trade_history").fetchone()
    return row["year"] if row and row["year"] else None


def country_options(connection):
    return connection.execute(
        "SELECT iso3, country_name FROM countries ORDER BY country_name"
    ).fetchall()


def country_overview(connection, iso3):
    return connection.execute(
        """
        SELECT c.*, p.population, p.year AS population_year
        FROM countries c
        LEFT JOIN population p ON p.country_iso3 = c.iso3
            AND p.year = (SELECT MAX(year) FROM population WHERE country_iso3 = c.iso3)
        WHERE c.iso3 = ?
        """,
        (iso3,),
    ).fetchone()


def country_scores(connection, iso3):
    return connection.execute(
        """
        SELECT s.*, c.country_name
        FROM market_scores s JOIN countries c ON c.iso3 = s.country_iso3
        WHERE s.country_iso3 = ?
        AND s.year = (
            SELECT MAX(year) FROM market_scores inner_scores
            WHERE inner_scores.country_iso3 = s.country_iso3
            AND inner_scores.product_code = s.product_code
        )
        ORDER BY s.opportunity_score DESC
        """,
        (iso3,),
    ).fetchall()


def country_trade_history(connection, iso3, product_code, flow):
    return connection.execute(
        """
        SELECT year, quantity_kg, value_usd
        FROM trade_history
        WHERE country_iso3 = ? AND product_code = ? AND flow = ? AND partner_code = '0'
        ORDER BY year
        """,
        (iso3, product_code, flow),
    ).fetchall()


def country_production_history(connection, iso3):
    return connection.execute(
        """
        SELECT year, milk_type, quantity_tonnes
        FROM dairy_production
        WHERE country_iso3 = ?
        ORDER BY year, milk_type
        """,
        (iso3,),
    ).fetchall()


def country_food_balance(connection, iso3, product):
    return connection.execute(
        """
        SELECT year, item, element, value, unit
        FROM food_balance
        WHERE country_iso3 = ? AND item IN ({})
        ORDER BY year DESC, item, element
        """.format(",".join("?" for _ in product.food_balance_items)),
        (iso3, *product.food_balance_items),
    ).fetchall()


def country_indicators(connection, iso3):
    return connection.execute(
        """
        SELECT year, indicator_name, value, unit, source, source_url
        FROM country_indicators AS ci
        WHERE ci.country_iso3 = ?
        AND ci.year = (SELECT MAX(inner_ci.year) FROM country_indicators AS inner_ci WHERE inner_ci.country_iso3 = ci.country_iso3)
        ORDER BY indicator_name
        """,
        (iso3,),
    ).fetchall()


def major_partners(connection, iso3, product_code, flow, limit=10):
    return connection.execute(
        """
        SELECT partner_name, quantity_kg, value_usd, year
        FROM trade_history
        WHERE country_iso3 = ? AND product_code = ? AND flow = ?
        AND partner_code != '0'
        AND year = (
            SELECT MAX(year) FROM trade_history
            WHERE country_iso3 = ? AND product_code = ? AND flow = ? AND partner_code != '0'
        )
        ORDER BY value_usd DESC
        LIMIT ?
        """,
        (iso3, product_code, flow, iso3, product_code, flow, limit),
    ).fetchall()


def product_from_search(search_text):
    normalized_search = search_text.casefold()
    matches = [
        product
        for product in PRODUCT_BY_CODE.values()
        if product.name.casefold() in normalized_search
        or any(alias in normalized_search for alias in product.aliases)
    ]
    return matches[0] if matches else None


def update_statuses(connection):
    return connection.execute(
        """
        SELECT source, dataset, status, records_loaded, completed_at, detail
        FROM data_updates
        WHERE id IN (
            SELECT MAX(id) FROM data_updates GROUP BY source, dataset
        )
        ORDER BY source, dataset
        """
    ).fetchall()
