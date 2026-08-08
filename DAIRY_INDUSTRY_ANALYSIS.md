# Dairy Industry Analysis

## Purpose

This module turns the official observations already imported through **Market Opportunities** and **Prices** into a country-level, reproducible dairy-sector analysis. It never estimates missing source records.

## Source order and coverage

| Area | Imported source | Module behavior |
| --- | --- | --- |
| Fresh-milk production by cow, buffalo, goat, and sheep | FAOSTAT Livestock Primary Production | Aggregates the imported species records into total milk production and five-year trends. |
| Dairy animals and milk yield | FAOSTAT Livestock Primary Production | Stores compatible `Producing Animals/Slaughtered` dairy-animal observations when published; yield is production / animals only when both exist. |
| Demand and consumption | FAOSTAT Food Balance Sheets | Uses domestic supply when available; otherwise uses apparent consumption only when compatible production, import, and export records all exist. |
| Imports, exports, trade values, and partners | UN Comtrade | Uses the loaded Liquid Milk & Cream HS proxy for country aggregate ratios and trade balance. Product-specific market analysis remains in Market Opportunities and Business Opportunity. |
| Population and GDP | World Bank Open Data | Provides per-capita consumption and economic context. |
| Retail prices | Prices module verified sources | Displays only imported source-aware retail records. |

## KPI formulas

* Apparent demand = production + imports - exports.
* Self-sufficiency = production / demand × 100.
* Import dependency = imports / demand × 100.
* Export ratio = exports / production × 100.
* Per-capita consumption = demand × 1,000 / population.
* Milk yield = production × 1,000 / dairy animals.
* Trade balance = exports - imports.
* CAGR = (last / first)^(1 / number of intervals) - 1.

Each result displays as unavailable if a compatible imported input is missing.

## Forecast

The five-year scenario applies the observed historical CAGR to the latest imported annual series. It is a transparent mechanical trend—not an econometric forecast—and excludes weather, feed, disease, policy, investment, and consumer-preference effects.

## Data not inferred

The module flags but does not manufacture company market shares, processing plants, brand portfolios, dairy-farm counts, feed costs, veterinary statistics, policy/subsidy data, climate risks, or disease outbreaks. Add licensed official country data for those subjects before using them in a recommendation.

## Source enrichment

The **Source Enrichment** tab supports permitted government, association, company, academic, and industry-publication evidence. It is deliberately citation-first rather than an unrestricted scraper: CAPTCHA-protected, login-gated, license-restricted, or terms-prohibited sites must not be automated.

Import an approved free-source CSV with:

```csv
country_iso3,category,metric,numeric_value,text_value,unit,data_year,source_title,source_url,source_tier,source_type,license_note,published_at,extraction_method,notes
```

Every row needs either `numeric_value` or `text_value`, a source URL, source tier/type, data year, and permitted-use/license note. The importer merges records without erasing other sources.

For scheduled imports:

```powershell
python -m dairy_analysis.update --evidence-csv .\country-dairy-evidence.csv
```

## REST API

```powershell
python -m dairy_analysis.api_server
```

* `GET /health`
* `GET /api/v1/dairy-analysis/countries`
* `GET /api/v1/dairy-analysis/countries/IND`
