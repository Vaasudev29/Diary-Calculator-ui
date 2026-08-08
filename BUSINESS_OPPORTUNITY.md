# Business Opportunity

## Purpose

Business Opportunity is the flagship country-intelligence layer in the Dairy Process Calculator Suite. It reuses the normalized official observations managed by **Market Opportunities**, but provides a distinct country-first business view and a read-only REST API.

## Architecture

| Layer | Location | Responsibility |
| --- | --- | --- |
| Data collection and ETL | `market_opportunities/clients.py`, `pipeline.py`, `update.py` | Download, validate, normalize, audit, and preserve official source records. |
| Database | `market_opportunities/database.py` | SQLite schema for countries, population, GDP, dairy production, food balance, trade history, scores, and update logs. |
| Business service | `business_opportunity/service.py` | Product opportunity matrix, competitor aggregation, business score, levels, and rules-based executive insights. |
| Dashboard | `business_opportunity/ui.py` | Country map, filters, country dashboard, charts, comparisons, and PDF/XLSX reports. |
| REST API | `business_opportunity/api_server.py` | Read-only standard-library HTTP endpoints. |

## Official inputs

* **UN Comtrade:** annual HS import/export value, quantity, and optional partner routes.
* **FAOSTAT:** cow, buffalo, goat, and sheep fresh-milk production plus compatible Food Balance Sheet indicators.
* **World Bank Open Data:** country metadata, population, and GDP in current USD.
* **UN Statistics M49:** bridges country reference records to UN Comtrade reporter codes.

The module does not create dummy data. Product measurements display `Not imported` until the associated official dataset is loaded.

## Product scope

The product matrix covers SMP, WMP, Butter, Cheese, Ghee, Whey Powder, Cream, Yogurt, and UHT Milk. Trade data is based on each product's mapped HS classification. The UHT Milk mapping is a relevant HS milk-and-cream line rather than a dedicated global UHT HS code, so users must validate country tariff classifications before a commercial decision.

## Business score

The country Business Opportunity score is the average of currently scored product opportunities, shown on a 0–10 scale. Individual product scores remain transparent:

* import value: 45%
* annual import growth: 25%
* compatible supply gap: 15%
* import dependency: 15%

Missing official components are reweighted; missing values are never estimated. Supply gaps appear only for compatible raw-milk observations.

## Running the API

```powershell
python -m business_opportunity.api_server
```

Endpoints:

* `GET /health`
* `GET /api/v1/business-opportunities/countries?search=Morocco`
* `GET /api/v1/business-opportunities/countries/MAR`
* `GET /api/v1/business-opportunities/products/butter`

The REST API is read-only and uses the same local SQLite database as the Streamlit dashboard.
