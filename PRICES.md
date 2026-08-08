# Prices

## Global Dairy Retail Price Intelligence

The Prices module shows only retail-price records that include a verifiable source URL, source tier, published/observation date, package size, local currency, and permitted-use note. It does not create prices or estimate unavailable products.

## Architecture

| Layer | Location | Responsibility |
| --- | --- | --- |
| Source client | `price_intelligence/clients.py` | Public BLS and Frankfurter request clients. |
| ETL | `price_intelligence/pipeline.py` | Validates, normalizes, stores, and audits authorized retail-price CSV observations. |
| Database | `price_intelligence/database.py` | Sources, products, prices, exchange rates, and update history. |
| Repository/service | `price_intelligence/repository.py`, `service.py` | Coverage map, country records, trends, and display conversions. |
| UI/API | `price_intelligence/ui.py`, `api_server.py` | Dashboard, source-aware imports, exports, and read-only REST endpoints. |

## Verified public sources

* **U.S. Bureau of Labor Statistics Public Data API:** permitted consumer-average-price time series when a source-specific series mapping is supplied.
* **Frankfurter:** no-key display conversion API backed by central-bank rates; it loads USD/EUR/INR display rates.
* **ECB:** official EUR-based reference-rate feed documented in the Sources panel.
* **Government / official open-data CSV downloads:** must be manually downloaded when a portal requires CAPTCHA, account access, or prohibits automated retrieval.

The application intentionally does not automate CAPTCHA-protected portals or scrape retail sites whose terms prohibit it.

## Loading verified retail prices

First load the country catalogue through **Market Opportunities → Data Updates**. Then use **Prices → Data Updates** to upload an authorized CSV with this header:

```csv
country_iso3,product_code,observation_date,package_description,package_quantity,package_unit,price_low_local,price_high_local,currency_code,source_record_url,published_at
```

Example format only (the values below are placeholders, not data to import):

```csv
USA,butter,YYYY-MM-DD,Package description,0.0,g,0.0,0.0,USD,https://official-source.example/record,YYYY-MM-DD
```

Supported package units are `kg`, `g`, `liter`, and `ml`. The importer converts packages to the retail product's comparable kg or liter unit. It rejects unrecognized country/product IDs, invalid ranges, absent source metadata, and incompatible units.

For automated import jobs:

```powershell
python -m price_intelligence.update --exchange-rates
python -m price_intelligence.update --csv .\official-retail-prices.csv --source-name "Publisher" --source-url "https://publisher.example/dataset" --license-note "Public-use terms reviewed"
```

The BLS connector is metadata-driven: it imports values only from BLS series identifiers that you explicitly map to an approved retail product/package. The JSON configuration contains no price values:

```json
[
  {
    "series_id": "BLS_SERIES_ID",
    "country_iso3": "USA",
    "product_code": "butter",
    "package_description": "Source-defined package",
    "package_quantity": 1,
    "package_unit": "kg",
    "currency_code": "USD"
  }
]
```

```powershell
python -m price_intelligence.update --bls-config .\bls-series-map.json --start-year 2024 --end-year 2026
```

## REST API

```powershell
python -m price_intelligence.api_server
```

* `GET /health`
* `GET /api/v1/prices/countries?search=India`
* `GET /api/v1/prices/countries/IND?currency=USD`
