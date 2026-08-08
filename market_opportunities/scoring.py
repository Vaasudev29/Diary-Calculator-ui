"""Transparent scoring based only on compatible, normalized official observations."""

from datetime import datetime, timezone

from market_opportunities.catalog import PRODUCT_BY_CODE


def _score_component(value, maximum):
    if value is None or maximum in (None, 0):
        return None
    return min(max(value / maximum * 100, 0), 100)


def _weighted_score(components):
    available = [(weight, value) for weight, value in components if value is not None]
    if not available:
        return 0.0, "No current official import observation is available."
    weight_total = sum(weight for weight, _ in available)
    score = sum(weight * value for weight, value in available) / weight_total
    omitted = 100 - weight_total
    method = "Import value 45%, import growth 25%, supply gap 15%, import dependency 15%."
    if omitted:
        method += f" Missing compatible inputs ({omitted}%) were reweighted across available official inputs."
    return round(score, 2), method


def _latest_trade_year(connection, product_code):
    row = connection.execute(
        """
        SELECT MAX(year) AS year
        FROM trade_history
        WHERE product_code = ? AND flow = 'Import' AND partner_code = '0'
        """,
        (product_code,),
    ).fetchone()
    return row["year"] if row else None


def recalculate_scores(connection, product_code=None):
    """Persist scores using the most recent import year for each supported product."""
    products = [PRODUCT_BY_CODE[product_code]] if product_code else PRODUCT_BY_CODE.values()
    calculated_at = datetime.now(timezone.utc).isoformat()
    scores_written = 0

    for product in products:
        year = _latest_trade_year(connection, product.code)
        if year is None:
            continue

        imports = connection.execute(
            """
            SELECT country_iso3, quantity_kg, value_usd
            FROM trade_history
            WHERE product_code = ? AND flow = 'Import' AND year = ? AND partner_code = '0'
            """,
            (product.code, year),
        ).fetchall()
        previous_imports = {
            row["country_iso3"]: row["value_usd"]
            for row in connection.execute(
                """
                SELECT country_iso3, value_usd
                FROM trade_history
                WHERE product_code = ? AND flow = 'Import' AND year = ? AND partner_code = '0'
                """,
                (product.code, year - 1),
            ).fetchall()
        }

        enriched = []
        for trade in imports:
            demand, production = _compatible_supply_inputs(connection, trade["country_iso3"], year, product)
            import_value = trade["value_usd"] or 0.0
            previous_value = previous_imports.get(trade["country_iso3"])
            import_growth = (
                (import_value - previous_value) / previous_value * 100
                if previous_value not in (None, 0)
                else None
            )
            supply_gap = demand - production if demand is not None and production is not None else None
            self_sufficiency = production / demand if demand not in (None, 0) and production is not None else None
            import_dependency = (
                (trade["quantity_kg"] / 1000) / ((trade["quantity_kg"] / 1000) + production)
                if trade["quantity_kg"] is not None and production not in (None, 0)
                else None
            )
            enriched.append(
                {
                    "country_iso3": trade["country_iso3"],
                    "quantity_kg": trade["quantity_kg"],
                    "value_usd": import_value,
                    "growth": import_growth,
                    "demand": demand,
                    "production": production,
                    "gap": supply_gap,
                    "self_sufficiency": self_sufficiency,
                    "dependency": import_dependency,
                }
            )

        maximum_value = max((entry["value_usd"] for entry in enriched), default=0)
        maximum_growth = max((max(entry["growth"], 0) for entry in enriched if entry["growth"] is not None), default=0)
        maximum_gap = max((max(entry["gap"], 0) for entry in enriched if entry["gap"] is not None), default=0)

        for entry in enriched:
            market_growth_score = _score_component(max(entry["growth"] or 0, 0), maximum_growth)
            score, method = _weighted_score(
                (
                    (45, _score_component(entry["value_usd"], maximum_value)),
                    (25, market_growth_score),
                    (15, _score_component(max(entry["gap"] or 0, 0), maximum_gap)),
                    (15, entry["dependency"] * 100 if entry["dependency"] is not None else None),
                )
            )
            connection.execute(
                """
                INSERT INTO market_scores (
                    country_iso3, product_code, year, demand_tonnes, production_tonnes,
                    import_quantity_kg, import_value_usd, import_growth_pct, supply_gap_tonnes,
                    self_sufficiency_ratio, import_dependency_ratio, market_growth_score,
                    opportunity_score, score_method, calculated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(country_iso3, product_code, year) DO UPDATE SET
                    demand_tonnes = excluded.demand_tonnes,
                    production_tonnes = excluded.production_tonnes,
                    import_quantity_kg = excluded.import_quantity_kg,
                    import_value_usd = excluded.import_value_usd,
                    import_growth_pct = excluded.import_growth_pct,
                    supply_gap_tonnes = excluded.supply_gap_tonnes,
                    self_sufficiency_ratio = excluded.self_sufficiency_ratio,
                    import_dependency_ratio = excluded.import_dependency_ratio,
                    market_growth_score = excluded.market_growth_score,
                    opportunity_score = excluded.opportunity_score,
                    score_method = excluded.score_method,
                    calculated_at = excluded.calculated_at
                """,
                (
                    entry["country_iso3"],
                    product.code,
                    year,
                    entry["demand"],
                    entry["production"],
                    entry["quantity_kg"],
                    entry["value_usd"],
                    entry["growth"],
                    entry["gap"],
                    entry["self_sufficiency"],
                    entry["dependency"],
                    market_growth_score,
                    score,
                    method,
                    calculated_at,
                ),
            )
            scores_written += 1

    connection.commit()
    return scores_written


def _compatible_supply_inputs(connection, country_iso3, year, product):
    """Return comparable demand/production only for raw-milk proxy products."""
    if not product.production_types:
        return None, None

    demand_row = connection.execute(
        """
        SELECT value, unit
        FROM food_balance
        WHERE country_iso3 = ? AND year = ? AND item IN ({})
        AND element = 'Domestic supply quantity (tonnes)'
        ORDER BY item LIMIT 1
        """.format(",".join("?" for _ in product.food_balance_items)),
        (country_iso3, year, *product.food_balance_items),
    ).fetchone()
    production_row = connection.execute(
        """
        SELECT SUM(quantity_tonnes) AS quantity_tonnes
        FROM dairy_production
        WHERE country_iso3 = ? AND year = ?
        """,
        (country_iso3, year),
    ).fetchone()
    demand = demand_row["value"] if demand_row and demand_row["unit"] == "t" else None
    production = production_row["quantity_tonnes"] if production_row else None
    return demand, production
