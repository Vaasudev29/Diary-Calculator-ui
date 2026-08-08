"""Business rules for retail-price coverage, conversion, and user-facing records."""

from price_intelligence import repository


def country_flag(iso2):
    return "".join(chr(127397 + ord(letter.upper())) for letter in iso2) if iso2 and len(iso2) == 2 else ""


def coverage_level(product_count):
    if product_count >= 12:
        return "Excellent"
    if product_count >= 5:
        return "Moderate"
    if product_count:
        return "Limited"
    return "No verified data"


def map_countries(connection, query=None, region=None, continent=None):
    regions_to_continents = {
        "East Asia & Pacific": "Asia & Oceania",
        "Europe & Central Asia": "Europe & Asia",
        "Latin America & Caribbean ": "Americas",
        "Middle East, North Africa, Afghanistan & Pakistan": "Africa & Asia",
        "North America": "Americas",
        "South Asia": "Asia",
        "Sub-Saharan Africa ": "Africa",
    }
    countries = []
    for row in repository.countries_with_coverage(connection, query, region):
        geographic_group = regions_to_continents.get(row["region"], "Other")
        if continent and continent != "All continents" and geographic_group != continent:
            continue
        countries.append(
            {
                **dict(row),
                "flag": country_flag(row["iso2"]),
                "continent": geographic_group,
                "coverage_level": coverage_level(row["available_products"]),
            }
        )
    return countries


def country_prices(connection, iso3, display_currency, product_code=None, currency=None, price_min=None, price_max=None):
    dashboard = repository.country_price_dashboard(
        connection, iso3, product_code, currency, price_min, price_max
    )
    if dashboard is None:
        return None
    rates, rate_date = repository.latest_exchange_rates(connection)
    rows = []
    for price in dashboard["prices"]:
        converted = _convert(price["price_per_normalized_unit"], price["currency_code"], display_currency, rates)
        rows.append(
            {
                **price,
                "display_price_per_unit": converted,
                "display_currency": display_currency,
                "range_label": f"{price['price_low_local']:,.2f}-{price['price_high_local']:,.2f} {price['currency_code']}",
            }
        )
    return {
        **dashboard,
        "prices": rows,
        "currency": display_currency,
        "exchange_rate_date": rate_date,
        "coverage_level": coverage_level(dashboard["country"]["available_products"]),
    }


def trends(connection, iso3, product_code, display_currency):
    rates, rate_date = repository.latest_exchange_rates(connection)
    result = []
    for record in repository.price_history(connection, iso3, product_code):
        result.append(
            {
                **record,
                "display_price_per_unit": _convert(
                    record["price_per_normalized_unit"], record["currency_code"], display_currency, rates
                ),
                "display_currency": display_currency,
            }
        )
    return result, rate_date


def _convert(value, source_currency, target_currency, rates):
    if source_currency == target_currency:
        return value
    if source_currency == "USD":
        return value * rates.get(target_currency) if target_currency in rates else None
    if target_currency == "USD":
        return value / rates.get(source_currency) if source_currency in rates else None
    source_to_usd = value / rates.get(source_currency) if source_currency in rates else None
    return source_to_usd * rates.get(target_currency) if source_to_usd is not None and target_currency in rates else None
