"""Command-line entry point for scheduled official-data updates."""

import argparse
from datetime import datetime, timezone

from market_opportunities import api
from market_opportunities.catalog import PRODUCT_BY_CODE
from market_opportunities.database import connect, initialize
from market_opportunities.exports import write_consolidated_exports


def build_parser():
    parser = argparse.ArgumentParser(description="Refresh Dairy Market Opportunities official datasets.")
    parser.add_argument("--reference", action="store_true", help="Refresh World Bank and UN country/population data.")
    parser.add_argument("--faostat", action="store_true", help="Refresh FAOSTAT production and Food Balance Sheet data.")
    parser.add_argument("--no-food-balance", action="store_true", help="Skip FAOSTAT Food Balance Sheets.")
    parser.add_argument("--trade", action="store_true", help="Refresh UN Comtrade dairy trade data.")
    parser.add_argument("--climate", action="store_true", help="Refresh NASA POWER country-coordinate climate context.")
    parser.add_argument("--countries", help="Comma-separated ISO3 countries required for --trade.")
    parser.add_argument("--products", default="butter,ghee,paneer", help="Comma-separated product codes.")
    parser.add_argument("--years", help="Comma-separated annual trade years; defaults to the prior two years.")
    parser.add_argument("--partners", action="store_true", help="Include partner-country trade routes.")
    parser.add_argument("--climate-countries", help="Comma-separated ISO3 countries required for --climate.")
    parser.add_argument("--climate-years", help="Inclusive start:end range for --climate; defaults to the prior five complete years.")
    parser.add_argument("--export-dir", help="Write the locally imported consolidated facts as CSV, JSON, and XLSX.")
    return parser


def main():
    arguments = build_parser().parse_args()
    if not any((arguments.reference, arguments.faostat, arguments.trade, arguments.climate, arguments.export_dir)):
        raise SystemExit("Choose at least one update option: --reference, --faostat, --trade, or --climate.")
    connection = connect()
    initialize(connection)
    try:
        if arguments.reference:
            print(api.refresh_reference_data(connection))
        if arguments.faostat:
            print(api.refresh_faostat_data(connection, not arguments.no_food_balance))
        if arguments.trade:
            if not arguments.countries:
                raise SystemExit("--countries is required with --trade.")
            product_codes = arguments.products.split(",")
            invalid_products = set(product_codes) - set(PRODUCT_BY_CODE)
            if invalid_products:
                raise SystemExit(f"Unsupported products: {', '.join(sorted(invalid_products))}.")
            current_year = datetime.now(timezone.utc).year
            years = [int(year) for year in arguments.years.split(",")] if arguments.years else [current_year - 2, current_year - 1]
            countries = [country.strip().upper() for country in arguments.countries.split(",") if country.strip()]
            print(api.refresh_trade_data(connection, countries, years, product_codes, arguments.partners))
        if arguments.climate:
            if not arguments.climate_countries:
                raise SystemExit("--climate-countries is required with --climate.")
            current_year = datetime.now(timezone.utc).year
            start_year, end_year = (
                (int(value) for value in arguments.climate_years.split(":", 1))
                if arguments.climate_years
                else (current_year - 6, current_year - 1)
            )
            if start_year > end_year:
                raise SystemExit("--climate-years must be formatted as start:end with start less than or equal to end.")
            countries = [country.strip().upper() for country in arguments.climate_countries.split(",") if country.strip()]
            print(api.refresh_climate_data(connection, countries, start_year, end_year))
        if arguments.export_dir:
            print(write_consolidated_exports(connection, arguments.export_dir))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
