# Market Opportunities

## Purpose

This module ranks dairy export opportunities from **official public data only**. It stores normalized, historical source facts in a local SQLite database at `data/market_opportunities.db`; the database is intentionally excluded from Git.

## Sources

| Source | Data used | Why it is used | Update approach |
| --- | --- | --- | --- |
| UN Comtrade public API | Annual HS import/export quantity, value, and optional partner routes | Official cross-border trade source with global HS coverage | The user starts a dated, rate-paced import from **Data Updates**. |
| FAOSTAT bulk downloads | Cow, buffalo, goat, and sheep milk production; Food Balance Sheet supply and per-capita indicators | Authoritative agricultural production and food supply context | The pipeline requests FAOSTAT's official guest token, resolves the current bulk-download URL, then downloads, validates, and filters the archive on demand. |
| World Bank Open Data | Country metadata, coordinates, region, income group, population, GDP, GDP per capita, urbanization, and inflation | Open country and economic context for market analysis | The pipeline refreshes metadata plus the latest ten annual indicator observations on demand. |
| UN Statistics M49 API | Numeric geographic codes | Official bridge from World Bank ISO3 countries to UN Comtrade reporters | Refreshed alongside the World Bank country catalogue. |
| NASA POWER | Monthly 2 m temperature and corrected precipitation at the selected country's reference coordinate | Public satellite-derived climate context for risk review | The pipeline requests selected country/year ranges on demand and retains annual means with the exact API URL. |

## Product classification

Trade queries use official HS headings. `Paneer` is proxied by HS 040610 (fresh cheese, including curd); `Ghee` by HS 040590 (other dairy fats and oils). Customs reporting may include related products within those headings, so results should be reviewed against destination-market tariffs and local product definitions before commercial use.

## Scoring

The opportunity score combines:

* import value: 45%
* annual import growth: 25%
* compatible FAOSTAT supply gap: 15%
* import dependency: 15%

If an authoritative component is unavailable, the remaining components are reweighted. No missing facts are imputed. Supply gaps are calculated only for the **Liquid Milk & Cream** raw-milk proxy, where FAOSTAT fresh-milk production and the `Milk - Excluding Butter` food-balance category are comparable enough for directional analysis. The module never infers processed-product output from raw milk production.

## Update and history behavior

Each update creates an auditable `data_updates` record with source, dataset, timestamp, status, record count, and failure details. Imports upsert observations by country, year, commodity, flow, partner, and source, preserving prior years for trend analysis.

For large global refreshes, first initialize the country catalogue. Then select the desired countries, years, products, and optional partner routes in **Market Opportunities → Data Updates**. Global all-country imports are intentionally presented as a long-running option because the public UN Comtrade API must be used responsibly and rate limited.

For unattended refreshes, run the official updater from a scheduler:

```powershell
python -m market_opportunities.update --reference
python -m market_opportunities.update --trade --countries AUS,NZL,IND --products butter,ghee,paneer --years 2023,2024
python -m market_opportunities.update --faostat
python -m market_opportunities.update --climate --climate-countries IND,MAR --climate-years 2020:2024
python -m market_opportunities.update --export-dir .\exports
```

## Source discovery and collection boundaries

The source catalog in the application prioritizes official APIs, open downloads, and public government datasets. Automated collection is limited to documented APIs or downloadable data whose terms permit it. The module does **not** circumvent authentication, CAPTCHAs, robots exclusions, paywalls, rate limits, or copyrighted-report access controls. Sources such as national open-data portals, USDA publications, OECD, IMF, WOAH, dairy boards, company annual reports, and public research can be added as cited evidence when their specific terms allow collection.

The consolidated export command writes normalized local facts to CSV, JSON, and XLSX. Every row includes country, year, metric, unit, source, source URL, and local load time. It exports only facts actually imported into the local database; it never inserts estimates for unavailable sources.
