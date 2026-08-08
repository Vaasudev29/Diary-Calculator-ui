"""Read repository for retail-price map, country dashboard, and conversion views."""


def countries_with_coverage(connection, query=None, region=None):
    parameters = []
    conditions = []
    if query:
        conditions.append("lower(c.country_name) LIKE ?")
        parameters.append(f"%{query.casefold()}%")
    if region and region != "All regions":
        conditions.append("c.region = ?")
        parameters.append(region)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return connection.execute(
        f"""
        SELECT c.iso3, c.iso2, c.country_name, c.region, c.latitude, c.longitude,
               COUNT(DISTINCT p.product_code) AS available_products,
               MAX(p.observation_date) AS last_observation_date
        FROM countries c
        LEFT JOIN retail_prices p ON p.country_iso3 = c.iso3
        {where_clause}
        GROUP BY c.iso3
        ORDER BY available_products DESC, c.country_name
        """,
        tuple(parameters),
    ).fetchall()


def country_price_dashboard(connection, iso3, product_code=None, currency=None, price_min=None, price_max=None):
    country = connection.execute(
        """
        SELECT c.*, COUNT(DISTINCT p.product_code) AS available_products,
               MAX(p.observation_date) AS last_observation_date
        FROM countries c LEFT JOIN retail_prices p ON p.country_iso3 = c.iso3
        WHERE c.iso3 = ? GROUP BY c.iso3
        """,
        (iso3,),
    ).fetchone()
    if not country:
        return None
    conditions = ["p.country_iso3 = ?"]
    parameters = [iso3]
    if product_code and product_code != "All products":
        conditions.append("p.product_code = ?")
        parameters.append(product_code)
    if currency and currency != "All currencies":
        conditions.append("p.currency_code = ?")
        parameters.append(currency)
    if price_min is not None:
        conditions.append("p.price_per_normalized_unit >= ?")
        parameters.append(price_min)
    if price_max is not None:
        conditions.append("p.price_per_normalized_unit <= ?")
        parameters.append(price_max)
    prices = connection.execute(
        f"""
        SELECT p.*, rp.product_name, rp.normalized_unit, s.source_name, s.source_url, s.source_tier
        FROM retail_prices p
        JOIN retail_products rp ON rp.product_code = p.product_code
        JOIN price_sources s ON s.source_id = p.source_id
        WHERE {' AND '.join(conditions)}
        AND p.observation_date = (
            SELECT MAX(latest.observation_date)
            FROM retail_prices latest
            WHERE latest.country_iso3 = p.country_iso3
            AND latest.product_code = p.product_code
            AND latest.package_description = p.package_description
            AND latest.source_id = p.source_id
        )
        ORDER BY rp.product_name, p.price_per_normalized_unit
        """,
        tuple(parameters),
    ).fetchall()
    return {"country": dict(country), "prices": [dict(price) for price in prices]}


def price_history(connection, iso3, product_code):
    return [
        dict(row)
        for row in connection.execute(
            """
            SELECT observation_date, average_price_local, price_per_normalized_unit, currency_code
            FROM retail_prices
            WHERE country_iso3 = ? AND product_code = ?
            ORDER BY observation_date
            """,
            (iso3, product_code),
        ).fetchall()
    ]


def latest_exchange_rates(connection):
    rows = connection.execute(
        """
        SELECT quote_currency, rate, rate_date
        FROM exchange_rates
        WHERE base_currency = 'USD' AND source_name = 'Frankfurter'
        AND rate_date = (
            SELECT MAX(rate_date) FROM exchange_rates
            WHERE base_currency = 'USD' AND source_name = 'Frankfurter'
        )
        """
    ).fetchall()
    rates = {"USD": 1.0}
    rate_date = None
    for row in rows:
        rates[row["quote_currency"]] = row["rate"]
        rate_date = row["rate_date"]
    return rates, rate_date


def price_update_status(connection):
    return connection.execute(
        """
        SELECT source_name, dataset, status, records_loaded, completed_at, detail
        FROM price_updates
        WHERE id IN (SELECT MAX(id) FROM price_updates GROUP BY source_name, dataset)
        ORDER BY source_name, dataset
        """
    ).fetchall()
