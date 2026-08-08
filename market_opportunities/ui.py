"""Streamlit presentation layer for the Market Opportunities module."""

import csv
from io import StringIO
import json
import sqlite3
import zipfile
from html import escape

import requests
import streamlit as st
import streamlit.components.v1 as components

from market_opportunities import api, repository
from market_opportunities.catalog import DAIRY_PRODUCTS, PRODUCT_BY_CODE, SOURCE_DESCRIPTIONS
from market_opportunities.database import connect, initialize
from market_opportunities.exports import consolidated_facts
from market_opportunities.reports import build_pdf, build_xlsx


def render_market_opportunities():
    connection = connect()
    initialize(connection)
    try:
        st.title("Market Opportunities")
        st.caption("Official-data intelligence for dairy export, manufacturing, and advisory decisions.")
        dashboard_tab, country_tab, search_tab, updates_tab, methodology_tab = st.tabs(
            ["Dashboard", "Country Details", "Opportunity Search", "Data Updates", "Methodology"]
        )
        with dashboard_tab:
            _render_dashboard(connection)
        with country_tab:
            _render_country_details(connection)
        with search_tab:
            _render_opportunity_search(connection)
        with updates_tab:
            _render_updates(connection)
        with methodology_tab:
            _render_methodology(connection)
    finally:
        connection.close()


def _render_dashboard(connection):
    product = _select_product("Dashboard product", key="market_dashboard_product")
    rows = repository.product_scores(connection, product.code)
    if not rows:
        _render_empty_state(product)
        return

    region_options = sorted({row["region"] for row in rows if row["region"]})
    filters, country_filter = st.columns([1, 2])
    selected_region = filters.selectbox("Region", ["All regions", *region_options], key="market_region")
    country_search = country_filter.text_input("Filter countries", key="market_country_filter")
    filtered_rows = [
        row
        for row in rows
        if (selected_region == "All regions" or row["region"] == selected_region)
        and country_search.casefold() in row["country_name"].casefold()
    ]
    _render_dashboard_kpis(filtered_rows, product.name)
    _render_world_map(filtered_rows, product.name)
    _render_rankings(filtered_rows, product)
    _render_country_comparison(filtered_rows, product)


def _render_dashboard_kpis(rows, product_name):
    total_value = sum(row["import_value_usd"] or 0 for row in rows)
    top_market = rows[0]["country_name"] if rows else "No current records"
    growth_candidates = [row for row in rows if row["import_growth_pct"] is not None]
    high_growth = max(growth_candidates, key=lambda row: row["import_growth_pct"]) if growth_candidates else None
    supply_candidates = [row for row in rows if row["supply_gap_tonnes"] is not None]
    largest_gap = max(supply_candidates, key=lambda row: row["supply_gap_tonnes"]) if supply_candidates else None
    market_count, import_value, leader, growth, gap = st.columns(5)
    market_count.metric("Ranked markets", len(rows))
    import_value.metric("Observed imports", _currency(total_value))
    leader.metric("Top opportunity", top_market)
    growth.metric("Highest import growth", _percent(high_growth["import_growth_pct"]) if high_growth else "Not available")
    gap.metric("Largest compatible supply gap", _tonnes(largest_gap["supply_gap_tonnes"]) if largest_gap else "Not available")
    st.caption(
        f"KPI values apply to imported official {product_name} records. "
        "Supply-gap metrics appear only when compatible FAOSTAT supply data is available."
    )


def _render_world_map(rows, product_name):
    map_rows = [
        {
            "country": row["country_name"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "score": row["opportunity_score"],
            "importValue": row["import_value_usd"] or 0,
        }
        for row in rows
        if row["latitude"] is not None and row["longitude"] is not None
    ]
    st.subheader("Global opportunity map")
    if not map_rows:
        st.info("Country coordinates are not available for the currently imported market records.")
        return
    serialized_rows = _safe_json(map_rows)
    components.html(
        f"""
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <div id="market-map" style="height:420px;border-radius:12px"></div>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
          const map = L.map('market-map', {{scrollWheelZoom:false}}).setView([20, 0], 2);
          L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; OpenStreetMap contributors'
          }}).addTo(map);
          const points = {serialized_rows};
          points.forEach(point => {{
            const radius = Math.max(5, Math.min(24, point.score / 4));
            L.circleMarker([point.latitude, point.longitude], {{
              radius: radius, color: '#087e8b', fillColor: '#17a2a8', fillOpacity: 0.72
            }}).bindPopup(`<strong>${{point.country}}</strong><br>{escape(product_name)} opportunity score: ${{point.score.toFixed(1)}}<br>Import value: $${{point.importValue.toLocaleString()}}`).addTo(map);
          }});
        </script>
        """,
        height=440,
    )


def _render_rankings(rows, product):
    st.subheader("Country ranking")
    ranking_rows = [
        {
            "Rank": index,
            "Country": row["country_name"],
            "Region": row["region"] or "Not classified",
            "Opportunity score": f"{row['opportunity_score']:.1f}",
            "Import value (USD)": _currency(row["import_value_usd"]),
            "Import growth": _percent(row["import_growth_pct"]),
            "Supply gap": _tonnes(row["supply_gap_tonnes"]),
        }
        for index, row in enumerate(rows[:50], start=1)
    ]
    _render_table(ranking_rows)
    _render_chart(
        f"Top {min(len(rows), 12)} {product.name} opportunity scores",
        "bar",
        [row["country_name"] for row in rows[:12]],
        [row["opportunity_score"] for row in rows[:12]],
        "Opportunity score",
    )
    importers = sorted(rows, key=lambda row: row["import_value_usd"] or 0, reverse=True)[:5]
    growers = sorted(
        [row for row in rows if row["import_growth_pct"] is not None],
        key=lambda row: row["import_growth_pct"],
        reverse=True,
    )[:5]
    gaps = sorted(
        [row for row in rows if row["supply_gap_tonnes"] is not None],
        key=lambda row: row["supply_gap_tonnes"],
        reverse=True,
    )[:5]
    importer_column, growth_column, gap_column = st.columns(3)
    with importer_column:
        st.markdown("**Top importers**")
        _render_table(
            [{"Country": row["country_name"], "Value": _currency(row["import_value_usd"])} for row in importers]
        )
    with growth_column:
        st.markdown("**Highest-growth markets**")
        _render_table(
            [{"Country": row["country_name"], "Growth": _percent(row["import_growth_pct"])} for row in growers]
        )
    with gap_column:
        st.markdown("**Largest compatible supply gaps**")
        _render_table(
            [{"Country": row["country_name"], "Supply gap": _tonnes(row["supply_gap_tonnes"])} for row in gaps]
        )


def _render_country_comparison(rows, product):
    countries_by_name = {row["country_name"]: row for row in rows}
    selected = st.multiselect(
        "Compare markets",
        list(countries_by_name),
        max_selections=5,
        key=f"comparison_{product.code}",
    )
    if len(selected) < 2:
        return
    comparison_rows = [countries_by_name[name] for name in selected]
    st.subheader("Country comparison")
    _render_chart(
        f"{product.name}: opportunity score comparison",
        "bar",
        [row["country_name"] for row in comparison_rows],
        [row["opportunity_score"] for row in comparison_rows],
        "Opportunity score",
    )
    _render_table(
        [
            {
                "Country": row["country_name"],
                "Opportunity score": f"{row['opportunity_score']:.1f}",
                "Import value": _currency(row["import_value_usd"]),
                "Import growth": _percent(row["import_growth_pct"]),
                "Import dependency": _percent(
                    row["import_dependency_ratio"] * 100 if row["import_dependency_ratio"] is not None else None
                ),
            }
            for row in comparison_rows
        ]
    )


def _render_country_details(connection):
    options = repository.country_options(connection)
    if not options:
        st.info("Initialize the country catalogue in Data Updates before opening country details.")
        return
    by_label = {f"{row['country_name']} ({row['iso3']})": row["iso3"] for row in options}
    selected_label = st.selectbox("Country", list(by_label), key="market_country_detail")
    iso3 = by_label[selected_label]
    country = repository.country_overview(connection, iso3)
    st.subheader(country["country_name"])
    region, income, population = st.columns(3)
    region.metric("Region", country["region"] or "Not classified")
    income.metric("Income group", country["income_level"] or "Not classified")
    population.metric("Population", f"{country['population']:,}" if country["population"] else "Not imported")

    product = _select_product("Product", key="market_country_product")
    scores = {row["product_code"]: row for row in repository.country_scores(connection, iso3)}
    score = scores.get(product.code)
    if score:
        score_card, import_value, growth, gap = st.columns(4)
        score_card.metric("Opportunity score", f"{score['opportunity_score']:.1f}/100")
        import_value.metric("Import value", _currency(score["import_value_usd"]))
        growth.metric("Import growth", _percent(score["import_growth_pct"]))
        gap.metric("Supply gap", _tonnes(score["supply_gap_tonnes"]))
        st.caption(score["score_method"])
    else:
        st.info(f"No scored {product.name} trade observation is imported for this country.")

    imports = repository.country_trade_history(connection, iso3, product.code, "Import")
    exports = repository.country_trade_history(connection, iso3, product.code, "Export")
    production = repository.country_production_history(connection, iso3)
    food_balance = repository.country_food_balance(connection, iso3, product)
    indicators = repository.country_indicators(connection, iso3)
    _render_indicator_context(indicators)
    _render_supply_context(production, food_balance)
    _render_trade_trends(imports, exports, product.name)
    import_partners = repository.major_partners(connection, iso3, product.code, "Import")
    export_partners = repository.major_partners(connection, iso3, product.code, "Export")
    left, right = st.columns(2)
    with left:
        st.subheader("Major import suppliers")
        _render_table(_partner_rows(import_partners), empty_message="Supplier routes have not been imported.")
    with right:
        st.subheader("Major export destinations")
        _render_table(_partner_rows(export_partners), empty_message="Destination routes have not been imported.")

    if country["m49_code"] and st.button("Refresh partner routes for this country and product"):
        _refresh_partner_routes(connection, iso3, product.code)
        st.rerun()

    report_rows = _country_report_rows(country, product, score, imports, exports)
    report_left, report_right = st.columns(2)
    report_left.download_button(
        "Download Excel report",
        build_xlsx(report_rows, f"{country['iso3']}-{product.code}"),
        f"{country['iso3']}-{product.code}-market-opportunity.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    report_right.download_button(
        "Download PDF report",
        build_pdf(f"{country['country_name']} - {product.name} Market Opportunity", report_rows),
        f"{country['iso3']}-{product.code}-market-opportunity.pdf",
        "application/pdf",
    )


def _render_trade_trends(imports, exports, product_name):
    st.subheader("Trade trends")
    years = sorted({row["year"] for row in imports} | {row["year"] for row in exports})
    if not years:
        st.info("No official import or export totals have been imported for this product.")
        return
    imports_by_year = {row["year"]: row["value_usd"] or 0 for row in imports}
    exports_by_year = {row["year"]: row["value_usd"] or 0 for row in exports}
    _render_chart(
        f"{product_name} trade value",
        "line",
        years,
        [imports_by_year.get(year, 0) for year in years],
        "Import value (USD)",
        secondary_values=[exports_by_year.get(year, 0) for year in years],
        secondary_label="Export value (USD)",
    )


def _render_supply_context(production, food_balance):
    st.subheader("Production and consumption context")
    latest_production_year = max((row["year"] for row in production), default=None)
    latest_production = [row for row in production if row["year"] == latest_production_year]
    latest_balance_year = max((row["year"] for row in food_balance), default=None)
    latest_balance = [row for row in food_balance if row["year"] == latest_balance_year]
    production_total = sum(row["quantity_tonnes"] for row in latest_production)
    domestic_supply = next(
        (
            row["value"]
            for row in latest_balance
            if row["element"] == "Domestic supply quantity (tonnes)"
        ),
        None,
    )
    per_capita = next(
        (
            row["value"]
            for row in latest_balance
            if row["element"] == "Food supply quantity (kg/capita/yr)"
        ),
        None,
    )
    production_metric, demand_metric, consumption_metric = st.columns(3)
    production_metric.metric(
        "Fresh milk production",
        _tonnes(production_total) if latest_production_year else "Not imported",
        help="FAOSTAT cow, buffalo, goat, and sheep milk production combined for the latest available year.",
    )
    demand_metric.metric(
        "Domestic supply",
        _tonnes(domestic_supply),
        help="Latest compatible FAOSTAT Food Balance Sheet domestic supply observation.",
    )
    consumption_metric.metric(
        "Per-capita food supply",
        f"{per_capita:.1f} kg/year" if per_capita is not None else "Not imported",
    )
    if production:
        annual_totals = {}
        for row in production:
            annual_totals[row["year"]] = annual_totals.get(row["year"], 0) + row["quantity_tonnes"]
        _render_chart(
            "Fresh milk production trend",
            "line",
            list(annual_totals),
            list(annual_totals.values()),
            "Production (tonnes)",
        )
        _render_table(
            [
                {
                    "Year": row["year"],
                    "Milk type": row["milk_type"],
                    "Production": _tonnes(row["quantity_tonnes"]),
                }
                for row in sorted(latest_production, key=lambda item: item["milk_type"])
            ],
            empty_message="No FAOSTAT production records are imported.",
        )


def _render_indicator_context(indicators):
    st.subheader("Economic and climate context")
    if not indicators:
        st.info("No World Bank or NASA POWER context indicators are imported for this country.")
        return
    _render_table(
        [
            {
                "Year": row["year"],
                "Indicator": row["indicator_name"],
                "Value": f"{row['value']:,.2f} {row['unit']}",
                "Source": row["source"],
                "Source URL": row["source_url"],
            }
            for row in indicators
        ]
    )


def _render_opportunity_search(connection):
    st.subheader("Ask for ranked export markets")
    query = st.text_input(
        "Search",
        placeholder="Countries importing Paneer",
        key="market_opportunity_search",
    )
    if not query:
        st.caption("Examples: Countries importing Ghee, Countries importing Butter, Countries importing Milk Powder.")
        return
    product = repository.product_from_search(query)
    if product is None:
        st.warning("No supported dairy product was recognized. Try Paneer, Ghee, Butter, Cheese, Whey Powder, SMP, WMP, Cream, Yogurt, or Milk Powder.")
        return
    rows = repository.product_scores(connection, product.code)
    if not rows:
        _render_empty_state(product)
        return
    st.success(f"Ranked {len(rows)} official-data opportunities for {product.name}.")
    _render_rankings(rows, product)


def _render_updates(connection):
    st.subheader("Official-data update pipeline")
    st.caption("Updates are on-demand, validated before storage, and historical observations are upserted by country, year, commodity, and source.")
    _render_update_status(connection)
    _render_consolidated_downloads(connection)

    st.markdown("#### 1. Reference and population data")
    if st.button("Initialize or refresh country catalogue and population"):
        try:
            with st.spinner("Downloading World Bank and UN reference data..."):
                result = api.refresh_reference_data(connection)
        except (requests.RequestException, sqlite3.Error, ValueError, OSError) as error:
            _render_update_error("Reference data refresh", error)
        else:
            st.success(
                f"Loaded {result['countries']} countries, {result['population_observations']} population "
                f"observations, {result['gdp_observations']} GDP observations, and "
                f"{result['indicator_observations']} WDI indicator observations."
            )

    st.markdown("#### 2. FAOSTAT production and food balance")
    include_food_balance = st.checkbox("Include Food Balance Sheets (large official download)", value=True)
    if st.button("Refresh FAOSTAT dairy production data"):
        progress = st.progress(0, text="Downloading and filtering official FAOSTAT archive...")
        callback = _progress_callback(progress, "Processing FAOSTAT records")
        try:
            with st.spinner("This can take several minutes because FAOSTAT publishes bulk archives."):
                result = api.refresh_faostat_data(connection, include_food_balance, callback)
        except (requests.RequestException, sqlite3.Error, ValueError, OSError, zipfile.BadZipFile) as error:
            _render_update_error("FAOSTAT refresh", error)
        else:
            st.success(
                f"Loaded {result['production_records']} production and "
                f"{result['food_balance_records']} food-balance observations; recalculated "
                f"{result['scores_recalculated']} scores."
            )
        finally:
            progress.empty()

    st.markdown("#### 4. NASA POWER climate context")
    climate_options = repository.country_options(connection)
    climate_countries = st.multiselect(
        "Climate countries",
        [f"{row['country_name']} ({row['iso3']})" for row in climate_options],
        key="market_climate_countries",
    )
    climate_years = st.slider(
        "Climate years",
        min_value=_current_year() - 15,
        max_value=_current_year() - 1,
        value=(_current_year() - 5, _current_year() - 1),
        key="market_climate_years",
    )
    st.caption(
        "NASA POWER supplies country-coordinate satellite-derived temperature and precipitation context. "
        "It is not farm-level weather, feed, or disease surveillance."
    )
    if st.button("Refresh NASA POWER climate context", disabled=not climate_options or not climate_countries):
        selected_climate_iso3 = [label.rsplit("(", 1)[1][:-1] for label in climate_countries]
        try:
            with st.spinner("Fetching NASA POWER monthly climate observations..."):
                result = api.refresh_climate_data(
                    connection, selected_climate_iso3, climate_years[0], climate_years[1]
                )
        except (requests.RequestException, sqlite3.Error, ValueError, OSError) as error:
            _render_update_error("NASA POWER refresh", error)
        else:
            st.success(f"Loaded {result['climate_observations']} NASA POWER climate observations.")

    st.markdown("#### 3. UN Comtrade dairy trade")
    countries = [row for row in repository.country_options(connection) if _country_has_m49(connection, row["iso3"])]
    if not countries:
        st.info("Initialize the country catalogue before importing UN Comtrade records.")
        return
    scope = st.radio("Trade import scope", ["Selected countries", "All available countries (long-running)"], horizontal=True)
    selected_labels = st.multiselect(
        "Countries",
        [f"{row['country_name']} ({row['iso3']})" for row in countries],
        default=[f"{countries[0]['country_name']} ({countries[0]['iso3']})"] if scope == "Selected countries" else [],
        disabled=scope != "Selected countries",
    )
    product_codes = st.multiselect(
        "Dairy products",
        [product.code for product in DAIRY_PRODUCTS],
        default=["butter", "ghee", "paneer"],
        format_func=lambda code: PRODUCT_BY_CODE[code].name,
    )
    current_year = _current_year()
    years = st.multiselect(
        "Trade years",
        list(range(current_year - 6, current_year + 1)),
        default=[current_year - 2, current_year - 1],
    )
    include_partners = st.checkbox("Also import partner-country routes (increases API calls)", value=False)
    if scope == "All available countries (long-running)":
        selected_iso3 = [row["iso3"] for row in countries]
    else:
        selected_iso3 = [label.rsplit("(", 1)[1][:-1] for label in selected_labels]
    request_multiplier = 4 if include_partners else 2
    st.caption(
        f"This selection will issue up to {len(selected_iso3) * len(product_codes) * len(years) * request_multiplier} "
        "UN Comtrade requests. The pipeline spaces calls by 0.75 seconds and retries temporary 429 "
        "rate limits with exponential backoff."
    )
    request_count = len(selected_iso3) * len(product_codes) * len(years) * request_multiplier
    if request_count > 40:
        st.warning(
            "This is a large public-API batch. To avoid rate limits, start with 1-3 countries, "
            "2 products, and 1-2 years; then load additional batches."
        )
    if st.button("Refresh UN Comtrade trade totals", disabled=not selected_iso3 or not product_codes or not years):
        progress = st.progress(0, text="Fetching official UN Comtrade observations...")
        callback = _progress_callback(progress, "UN Comtrade requests")
        try:
            with st.spinner("Fetching, validating, normalizing, and scoring official trade records..."):
                result = api.refresh_trade_data(
                    connection,
                    selected_iso3,
                    years,
                    product_codes,
                    include_partners=include_partners,
                    progress_callback=callback,
                )
        except (requests.RequestException, sqlite3.Error, ValueError, OSError) as error:
            _render_update_error("UN Comtrade refresh", error)
        else:
            st.success(
                f"Loaded {result['trade_records']} UN Comtrade records and recalculated "
                f"{result['scores_recalculated']} market scores."
            )
        finally:
            progress.empty()


def _render_methodology(connection):
    st.subheader("Sources, update policy, and limitations")
    for source, purpose, refresh in SOURCE_DESCRIPTIONS:
        with st.expander(source, expanded=True):
            st.write(purpose)
            st.caption(refresh)
    st.markdown("#### Opportunity score")
    st.write(
        "The score uses normalized official import value (45%), import growth (25%), compatible "
        "FAOSTAT supply gap (15%), and import dependency (15%). When an official component is "
        "unavailable, the available components are reweighted and the score method is shown on the record."
    )
    st.markdown("#### Important limitations")
    st.write(
        "UN Comtrade product classifications are HS customs lines; Paneer is represented by HS 040610 "
        "(fresh cheese, including curd), and Ghee by HS 040590 (other dairy fats and oils). "
        "They may include closely related products depending on reporter customs practice. "
        "FAOSTAT primary milk production is compatible with the Liquid Milk & Cream raw-milk proxy only; processed-product "
        "manufacturing output is not inferred. The module does not invent missing production, demand, "
        "supplier, or trade data."
    )
    statuses = repository.update_statuses(connection)
    if statuses:
        st.markdown("#### Latest loaded datasets")
        _render_table(
            [
                {
                    "Source": row["source"],
                    "Dataset": row["dataset"],
                    "Status": row["status"],
                    "Records": row["records_loaded"],
                    "Completed": row["completed_at"] or "In progress",
                }
                for row in statuses
            ]
        )


def _render_update_status(connection):
    statuses = repository.update_statuses(connection)
    if not statuses:
        st.info("No official data has been loaded yet. Start with reference data, then import the trade and FAOSTAT datasets required for your analysis.")
        return
    _render_table(
        [
            {
                "Source": row["source"],
                "Dataset": row["dataset"],
                "Status": row["status"],
                "Records loaded": row["records_loaded"],
                "Last completed": row["completed_at"] or "In progress",
                "Detail": row["detail"] or "",
            }
            for row in statuses
        ]
    )


def _render_consolidated_downloads(connection):
    st.markdown("#### Consolidated source-traceable exports")
    facts = consolidated_facts(connection)
    if not facts:
        st.caption("Exports will be available after at least one source update or permitted evidence import.")
        return
    headers = list(facts[0])
    csv_output = StringIO()
    writer = csv.DictWriter(csv_output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(facts)
    csv_column, json_column, xlsx_column = st.columns(3)
    csv_column.download_button(
        "Download CSV facts",
        csv_output.getvalue().encode("utf-8"),
        "dairy_intelligence_facts.csv",
        "text/csv",
    )
    json_column.download_button(
        "Download JSON facts",
        json.dumps(facts, indent=2).encode("utf-8"),
        "dairy_intelligence_facts.json",
        "application/json",
    )
    xlsx_column.download_button(
        "Download Excel facts",
        build_xlsx(facts, "Dairy intelligence"),
        "dairy_intelligence_facts.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _refresh_partner_routes(connection, iso3, product_code):
    latest_year = repository.latest_data_year(connection)
    if latest_year is None:
        st.warning("Import UN Comtrade trade totals before requesting partner routes.")
        return
    progress = st.progress(0, text="Refreshing partner routes from UN Comtrade...")
    try:
        result = api.refresh_trade_data(
            connection,
            [iso3],
            [latest_year],
            [product_code],
            include_partners=True,
            progress_callback=_progress_callback(progress, "UN Comtrade partner routes"),
        )
    except (requests.RequestException, sqlite3.Error, ValueError, OSError) as error:
        _render_update_error("UN Comtrade partner-route refresh", error)
    else:
        st.success(f"Loaded {result['trade_records']} partner-route records.")
    finally:
        progress.empty()


def _country_has_m49(connection, iso3):
    row = connection.execute("SELECT m49_code FROM countries WHERE iso3 = ?", (iso3,)).fetchone()
    return bool(row and row["m49_code"])


def _select_product(label, key):
    product_codes = [product.code for product in DAIRY_PRODUCTS]
    code = st.selectbox(label, product_codes, format_func=lambda item: PRODUCT_BY_CODE[item].name, key=key)
    return PRODUCT_BY_CODE[code]


def _render_empty_state(product):
    st.info(
        f"No official {product.name} market records are loaded yet. Open Data Updates to initialize "
        "country metadata and import UN Comtrade trade records."
    )


def _render_update_error(action, error):
    if isinstance(error, sqlite3.OperationalError) and "locked" in str(error).casefold():
        st.error(
            f"{action} could not start because the local database is busy. "
            "Wait for another update to finish, or stop duplicate Streamlit/updater processes before retrying."
        )
    else:
        st.error(f"{action} failed. The source failure was recorded in Data Updates.")
    st.caption(f"Source detail: {error}")


def _render_table(rows, empty_message="No official records are available for this selection."):
    if not rows:
        st.caption(empty_message)
        return
    headers = list(rows[0])
    header_cells = "".join(f"<th>{escape(str(header))}</th>" for header in headers)
    body_rows = "".join(
        "<tr>"
        + "".join(f"<td>{escape(str(row.get(header, '')))}</td>" for header in headers)
        + "</tr>"
        for row in rows
    )
    st.markdown(
        f'<div class="market-table-wrap"><table class="market-table"><thead><tr>{header_cells}</tr></thead>'
        f"<tbody>{body_rows}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _render_chart(title, chart_type, labels, values, label, secondary_values=None, secondary_label=None):
    if not labels:
        return
    datasets = [
        {
            "label": label,
            "data": values,
            "borderColor": "#087e8b",
            "backgroundColor": "rgba(8, 126, 139, 0.45)",
            "borderWidth": 2,
            "fill": chart_type == "line",
        }
    ]
    if secondary_values is not None:
        datasets.append(
            {
                "label": secondary_label,
                "data": secondary_values,
                "borderColor": "#123047",
                "backgroundColor": "rgba(18, 48, 71, 0.30)",
                "borderWidth": 2,
                "fill": False,
            }
        )
    chart_id = f"market-chart-{abs(hash((title, tuple(labels))))}"
    components.html(
        f"""
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
        <canvas id="{chart_id}" style="max-height:340px"></canvas>
        <script>
          new Chart(document.getElementById('{chart_id}'), {{
            type: '{chart_type}',
            data: {{labels: {_safe_json(labels)}, datasets: {_safe_json(datasets)}}},
            options: {{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {{title: {{display: true, text: {_safe_json(title)}}}, legend: {{display: true}}}},
              scales: {{y: {{beginAtZero: true}}}}
            }}
          }});
        </script>
        """,
        height=370,
    )


def _partner_rows(rows):
    return [
        {
            "Partner": row["partner_name"],
            "Year": row["year"],
            "Value (USD)": _currency(row["value_usd"]),
            "Quantity": _kilograms(row["quantity_kg"]),
        }
        for row in rows
    ]


def _country_report_rows(country, product, score, imports, exports):
    rows = [
        {"Metric": "Country", "Value": country["country_name"]},
        {"Metric": "Product", "Value": product.name},
        {"Metric": "Population", "Value": f"{country['population']:,}" if country["population"] else "Not imported"},
    ]
    if score:
        rows.extend(
            [
                {"Metric": "Opportunity score", "Value": f"{score['opportunity_score']:.1f}/100"},
                {"Metric": "Import value", "Value": _currency(score["import_value_usd"])},
                {"Metric": "Import growth", "Value": _percent(score["import_growth_pct"])},
                {"Metric": "Supply gap", "Value": _tonnes(score["supply_gap_tonnes"])},
            ]
        )
    for row in imports:
        rows.append({"Metric": f"Import value ({row['year']})", "Value": _currency(row["value_usd"])})
    for row in exports:
        rows.append({"Metric": f"Export value ({row['year']})", "Value": _currency(row["value_usd"])})
    return rows


def _progress_callback(progress, label):
    def callback(completed, total):
        progress_value = min(completed / total, 1.0) if total else 0.1
        text = f"{label}: {completed:,}" + (f" of {total:,}" if total else "")
        progress.progress(progress_value, text=text)

    return callback


def _current_year():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).year


def _safe_json(value):
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _currency(value):
    return "Not available" if value is None else f"${value:,.0f}"


def _percent(value):
    return "Not available" if value is None else f"{value:.1f}%"


def _tonnes(value):
    return "Not available" if value is None else f"{value:,.0f} t"


def _kilograms(value):
    return "Not available" if value is None else f"{value:,.0f} kg"
