"""Application facade used by the Streamlit UI and future HTTP/API adapters."""

from datetime import datetime, timezone

from market_opportunities import pipeline
from market_opportunities.scoring import recalculate_scores


def refresh_reference_data(connection):
    year = datetime.now(timezone.utc).year
    countries = pipeline.sync_reference_data(connection)
    population = pipeline.sync_population(connection, year - 10, year)
    gdp = pipeline.sync_gdp(connection, year - 10, year)
    indicators = pipeline.sync_world_bank_indicators(connection, year - 10, year)
    return {
        "countries": countries,
        "population_observations": population,
        "gdp_observations": gdp,
        "indicator_observations": indicators,
    }


def refresh_trade_data(
    connection,
    country_iso3_codes,
    years,
    product_codes,
    include_partners=False,
    progress_callback=None,
):
    records = pipeline.sync_trade(
        connection,
        country_iso3_codes,
        years,
        product_codes,
        include_partners=include_partners,
        progress_callback=progress_callback,
    )
    scores = sum(recalculate_scores(connection, product_code) for product_code in product_codes)
    return {"trade_records": records, "scores_recalculated": scores}


def refresh_faostat_data(connection, include_food_balance, progress_callback=None):
    production = pipeline.sync_faostat_production(connection, progress_callback=progress_callback)
    food_balance = (
        pipeline.sync_faostat_food_balance(connection, progress_callback=progress_callback)
        if include_food_balance
        else 0
    )
    scores = recalculate_scores(connection)
    return {
        "production_records": production,
        "food_balance_records": food_balance,
        "scores_recalculated": scores,
    }


def refresh_climate_data(connection, country_iso3_codes, start_year, end_year):
    return {
        "climate_observations": pipeline.sync_nasa_power_climate(
            connection, country_iso3_codes, start_year, end_year
        )
    }
