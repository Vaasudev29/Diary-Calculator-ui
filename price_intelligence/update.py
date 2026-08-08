"""Command-line updater for permitted, verified public retail-price records."""

import argparse
from pathlib import Path

from market_opportunities.database import connect, initialize
from price_intelligence import api
from price_intelligence.database import initialize as initialize_prices


def main():
    parser = argparse.ArgumentParser(description="Update Global Dairy Retail Price Intelligence.")
    parser.add_argument("--exchange-rates", action="store_true", help="Refresh USD/EUR/INR display conversion rates.")
    parser.add_argument("--csv", help="Path to an authorized compatible public-source price CSV.")
    parser.add_argument("--source-name", help="Publisher/source name required with --csv.")
    parser.add_argument("--source-url", help="Original public source URL required with --csv.")
    parser.add_argument("--source-tier", default="Official government statistics")
    parser.add_argument("--license-note", help="License or permitted-use note required with --csv.")
    parser.add_argument("--bls-config", help="BLS series mapping JSON with no price values.")
    parser.add_argument("--start-year", type=int, default=2024)
    parser.add_argument("--end-year", type=int, default=2026)
    arguments = parser.parse_args()
    if not arguments.exchange_rates and not arguments.csv and not arguments.bls_config:
        raise SystemExit("Choose --exchange-rates, provide --csv, and/or provide --bls-config.")
    if arguments.csv and not all((arguments.source_name, arguments.source_url, arguments.license_note)):
        raise SystemExit("--csv requires --source-name, --source-url, and --license-note.")
    connection = connect()
    initialize(connection)
    initialize_prices(connection)
    try:
        if arguments.exchange_rates:
            print({"exchange_rates_loaded": api.refresh_exchange_rates(connection)})
        if arguments.csv:
            with Path(arguments.csv).open("r", encoding="utf-8-sig", newline="") as source_file:
                print(
                    {
                        "retail_prices_loaded": api.import_public_price_csv(
                            connection,
                            source_file,
                            arguments.source_name,
                            arguments.source_url,
                            arguments.source_tier,
                            arguments.license_note,
                        )
                    }
                )
        if arguments.bls_config:
            with Path(arguments.bls_config).open("r", encoding="utf-8") as config_file:
                print(
                    {
                        "bls_price_observations_loaded": api.import_bls_series(
                            connection, config_file, arguments.start_year, arguments.end_year
                        )
                    }
                )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
