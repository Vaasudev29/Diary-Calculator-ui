"""Application facade for source refresh and verified price imports."""

from price_intelligence.clients import PublicPriceClient
from price_intelligence.pipeline import (
    import_bls_series_config,
    import_verified_csv,
    seed_product_catalog,
    sync_exchange_rates,
)


def initialize_price_store(connection):
    seed_product_catalog(connection)


def refresh_exchange_rates(connection):
    return sync_exchange_rates(connection, PublicPriceClient())


def import_public_price_csv(connection, file_handle, source_name, source_url, source_tier, license_note):
    return import_verified_csv(
        connection,
        file_handle,
        source_name,
        source_url,
        source_tier,
        license_note,
    )


def import_bls_series(connection, config_file, start_year, end_year):
    return import_bls_series_config(connection, config_file, start_year, end_year)
