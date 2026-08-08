"""Streamlit presentation layer for reproducible dairy industry analysis."""

import json
from html import escape
from io import StringIO

import streamlit as st
import streamlit.components.v1 as components

from dairy_analysis import evidence, service
from dairy_analysis.source_catalog import EVIDENCE_CATEGORIES, SOURCE_CATALOG
from market_opportunities.database import connect, default_database_path, initialize
from market_opportunities.reports import build_pdf, build_xlsx
from price_intelligence.database import initialize as initialize_prices


def render_dairy_industry_analysis():
    connection = connect()
    initialize(connection)
    initialize_prices(connection)
    try:
        options = service.country_options(connection)
    finally:
        connection.close()
    st.title("Dairy Industry Analysis")
    st.caption("Reproducible agricultural-economics analysis from imported official country observations.")
    if not options:
        st.info("Load the country catalogue in Market Opportunities → Data Updates before analyzing a country.")
        return
    overview_tab, trends_tab, outlook_tab, risks_tab, sources_tab, enrichment_tab = st.tabs(
        [
            "Executive Summary",
            "Trends & KPIs",
            "Forecast & Outlook",
            "Risks & SWOT",
            "Data & Sources",
            "Source Enrichment",
        ]
    )
    labels = {f"{_flag(option['iso2'])} {option['country_name']} ({option['iso3']})": option["iso3"] for option in options}
    selection = st.selectbox("Country", list(labels), key="analysis_country")
    analysis = _load_analysis(labels[selection])
    with overview_tab:
        _render_executive_summary(analysis)
    with trends_tab:
        _render_trends(analysis)
    with outlook_tab:
        _render_forecast(analysis)
    with risks_tab:
        _render_risks_swot(analysis)
    with sources_tab:
        _render_data_sources(analysis)
    with enrichment_tab:
        _render_source_enrichment(labels[selection], analysis)


@st.cache_data(ttl=300, show_spinner=False)
def _cached_analysis(database_path, modified_at, iso3):
    del modified_at
    connection = connect(database_path)
    initialize(connection)
    initialize_prices(connection)
    try:
        return service.analyze_country(connection, iso3)
    finally:
        connection.close()


def _load_analysis(iso3):
    path = default_database_path()
    modified_at = path.stat().st_mtime if path.exists() else 0
    return _cached_analysis(str(path), modified_at, iso3)


def _render_executive_summary(analysis):
    country = analysis["country"]
    st.subheader(f"{_flag(country['iso2'])} {country['country_name']} Dairy Industry")
    population, gdp, region, data_status = st.columns(4)
    population.metric("Population", f"{country['population']:,}" if country["population"] else "Not imported")
    gdp.metric("GDP (current USD)", _currency(country["gdp_current_usd"]))
    region.metric("Region", country["region"] or "Not classified")
    data_status.metric("Imported data series", sum(analysis["sources"].values()), f"of {len(analysis['sources'])} source areas")
    for insight in analysis["insights"]:
        st.write(f"- {insight}")
    _render_kpi_cards(analysis["kpis"])
    _render_report_downloads(analysis)


def _render_kpi_cards(kpis):
    st.subheader("Core dairy-sector KPIs")
    if not kpis["data_available"]:
        st.info("No country production, trade, food-balance, population, or livestock records are imported yet.")
        return
    production, demand, self_sufficiency, dependency = st.columns(4)
    production.metric("Production", _tonnes(kpis["total_milk_tonnes"]), _percent(kpis["production_growth_pct"]))
    demand.metric("Demand", _tonnes(kpis["demand_tonnes"]), _percent(kpis["demand_growth_pct"]))
    self_sufficiency.metric("Self-sufficiency", _percent(kpis["self_sufficiency_pct"]))
    dependency.metric("Import dependency", _percent(kpis["import_dependency_pct"]))
    imports, exports, per_capita, yield_metric = st.columns(4)
    imports.metric("Imports", _tonnes(kpis["import_tonnes"]), _percent(kpis["import_growth_pct"]))
    exports.metric("Exports", _tonnes(kpis["export_tonnes"]), _percent(kpis["export_growth_pct"]))
    per_capita.metric("Per-capita consumption", _kg_per_capita(kpis["per_capita_consumption_kg"]))
    yield_metric.metric("Milk yield", _kg_per_animal(kpis["milk_yield_kg_per_animal"]))
    st.caption(f"Demand calculation: {kpis['demand_method']}.")


def _render_trends(analysis):
    st.subheader("Production, demand, and trade trends")
    trend = analysis["trend"]
    if not trend:
        st.info("No compatible annual observations are imported for this country.")
        return
    years = [row["year"] for row in trend]
    _chart(
        "Production and demand",
        years,
        [
            {"label": "Production (tonnes)", "values": [row.get("total_milk_tonnes") for row in trend], "color": "#087e8b"},
            {"label": "Demand (tonnes)", "values": [row.get("demand_tonnes") for row in trend], "color": "#123047"},
        ],
    )
    _chart(
        "Imports vs exports",
        years,
        [
            {"label": "Imports (tonnes)", "values": [row.get("import_tonnes") for row in trend], "color": "#d07d00"},
            {"label": "Exports (tonnes)", "values": [row.get("export_tonnes") for row in trend], "color": "#087e8b"},
        ],
    )
    _chart(
        "Per-capita consumption and yield",
        years,
        [
            {"label": "Per-capita consumption (kg)", "values": [row.get("per_capita_consumption_kg") for row in trend], "color": "#123047"},
            {"label": "Milk yield (kg/animal)", "values": [row.get("milk_yield_kg_per_animal") for row in trend], "color": "#087e8b"},
        ],
    )
    _table(
        [
            {
                "Year": row["year"],
                "Production": _tonnes(row.get("total_milk_tonnes")),
                "Demand": _tonnes(row.get("demand_tonnes")),
                "Imports": _tonnes(row.get("import_tonnes")),
                "Exports": _tonnes(row.get("export_tonnes")),
                "Trade balance": _tonnes(row.get("trade_balance_tonnes")),
                "Self-sufficiency": _percent(row.get("self_sufficiency_pct")),
            }
            for row in trend
        ],
        "No trend rows available.",
    )
    _render_price_analysis(analysis["prices"])


def _render_price_analysis(prices):
    st.subheader("Price analysis")
    if not prices:
        st.caption("Farmgate, retail, butter, cheese, and powder price records are not imported for this country.")
        return
    _table(
        [
            {
                "Product": row["product_name"],
                "Price per normalized unit": f"{row['price_per_normalized_unit']:,.2f} {row['currency_code']}",
                "Currency": row["currency_code"],
                "Observation": row["observation_date"],
                "Source": row["source_name"],
            }
            for row in prices
        ],
        "No verified price records imported.",
    )


def _render_forecast(analysis):
    st.subheader("Five-year market outlook")
    forecast = analysis["forecast"]
    if not forecast["available"]:
        st.info(forecast["assumption"])
        return
    projections = forecast["projections"]
    _chart(
        "CAGR-based outlook",
        [row["year"] for row in projections],
        [
            {"label": "Production forecast (tonnes)", "values": [row["production_tonnes"] for row in projections], "color": "#087e8b"},
            {"label": "Demand forecast (tonnes)", "values": [row["demand_tonnes"] for row in projections], "color": "#123047"},
            {"label": "Import forecast (tonnes)", "values": [row["import_tonnes"] for row in projections], "color": "#d07d00"},
        ],
    )
    _table(
        [
            {
                "Year": row["year"],
                "Production": _tonnes(row["production_tonnes"]),
                "Demand": _tonnes(row["demand_tonnes"]),
                "Imports": _tonnes(row["import_tonnes"]),
            }
            for row in projections
        ],
        "No projection rows available.",
    )
    st.warning(forecast["assumption"])
    st.caption(
        "This is a mechanical historical-trend scenario, not an econometric forecast. "
        "It does not claim to predict policy, weather, feed, disease, or structural market changes."
    )


def _render_risks_swot(analysis):
    st.subheader("Risks and SWOT")
    swot = analysis["swot"]
    strengths, weaknesses, opportunities, threats = st.columns(4)
    for column, label, entries in (
        (strengths, "Strengths", swot["strengths"]),
        (weaknesses, "Weaknesses", swot["weaknesses"]),
        (opportunities, "Opportunities", swot["opportunities"]),
        (threats, "Threats", swot["threats"]),
    ):
        with column:
            st.markdown(f"**{label}**")
            for entry in entries:
                st.write(f"- {entry}")
    st.subheader("Data-limited risk areas")
    st.write(
        "Climate, feed availability, veterinary/disease indicators, government policy, subsidies, "
        "company market shares, farms, processing capacity, and consumer-preference series require "
        "additional approved official sources. They are intentionally not inferred."
    )


def _render_data_sources(analysis):
    st.subheader("Data availability and calculation method")
    _table(
        [
            {"Area": label.replace("_", " ").title(), "Status": "Imported" if available else "Not imported"}
            for label, available in analysis["sources"].items()
        ],
        "No source availability details.",
    )
    st.markdown(
        """
**Sources:** FAOSTAT production/Food Balance Sheets; UN Comtrade annual HS trade records;
World Bank population and GDP; and the Prices module's verified-source retail records.

**Formulas:** apparent demand = production + imports - exports when all compatible observations
exist; otherwise FAOSTAT Food Balance Sheet domestic supply is used. Self-sufficiency =
production / demand × 100. Import dependency = imports / demand × 100. Export ratio = exports /
production × 100. Per-capita consumption = demand × 1,000 / population. Milk yield = production ×
1,000 / dairy animals. CAGR = (last / first)^(1 / years) - 1.
"""
    )
    if analysis["evidence"]:
        st.subheader("Merged cited country evidence")
        _table(
            [
                {
                    "Category": category,
                    "Metric": record["metric"],
                    "Value": _evidence_value(record),
                    "Data year": record["data_year"],
                    "Source": record["source_title"],
                    "Source URL": record["source_url"],
                }
                for category, records in analysis["evidence"].items()
                for record in records
            ],
            "No cited enrichment records.",
        )


def _render_source_enrichment(selected_iso3, analysis):
    st.subheader("Free-source enrichment")
    st.caption(
        "Use this governed importer for permitted public sources that are not available through the "
        "automated international APIs. Each record requires a country, data year, value, source URL, "
        "source tier/type, and license or permitted-use note."
    )
    categories = sorted({category for source in SOURCE_CATALOG for category in source["categories"]})
    coverage = {category: len(analysis["evidence"].get(category, [])) for category in categories}
    _table(
        [
            {
                "Category": category.replace("_", " ").title(),
                "Cited records": count,
                "Status": "Enriched" if count else "Needs a permitted public source",
            }
            for category, count in coverage.items()
        ],
        "No enrichment categories configured.",
    )
    with st.expander("Approved free-source discovery catalogue", expanded=True):
        for source in SOURCE_CATALOG:
            st.markdown(f"**{source['name']}** — {source['tier']}")
            st.write(source["use"])
            if source["url"]:
                st.markdown(f"[Open source]({source['url']})")
    uploaded = st.file_uploader("Cited country evidence CSV", type="csv", key="evidence_upload")
    with st.expander("Required evidence CSV schema"):
        st.code(
            "country_iso3,category,metric,numeric_value,text_value,unit,data_year,source_title,"
            "source_url,source_tier,source_type,license_note,published_at,extraction_method,notes"
        )
        st.caption(f"Allowed categories: {', '.join(EVIDENCE_CATEGORIES)}.")
    if st.button("Validate and merge cited evidence", disabled=uploaded is None):
        connection = connect()
        initialize(connection)
        initialize_prices(connection)
        try:
            loaded = evidence.import_evidence_csv(
                connection,
                StringIO(uploaded.getvalue().decode("utf-8-sig")),
                f"Country dairy evidence ({selected_iso3})",
            )
        except (UnicodeDecodeError, ValueError, OSError) as error:
            st.error(f"Evidence import failed and was audited: {error}")
        else:
            _cached_analysis.clear()
            st.success(f"Merged {loaded} cited evidence record(s). Refresh the selected country analysis to view them.")
        finally:
            connection.close()


def _render_report_downloads(analysis):
    rows = [
        {
            "Metric": "Country",
            "Value": analysis["country"]["country_name"],
        },
        *[
            {"Metric": label, "Value": value}
            for label, value in (
                ("Latest production", _tonnes(analysis["kpis"].get("total_milk_tonnes"))),
                ("Latest demand", _tonnes(analysis["kpis"].get("demand_tonnes"))),
                ("Self-sufficiency", _percent(analysis["kpis"].get("self_sufficiency_pct"))),
                ("Import dependency", _percent(analysis["kpis"].get("import_dependency_pct"))),
                ("Production CAGR", _percent(analysis["kpis"].get("production_cagr_pct"))),
            )
        ],
    ]
    rows.extend(
        {
            "Metric": f"{category.title()}: {record['metric']} ({record['data_year']})",
            "Value": f"{_evidence_value(record)} | {record['source_title']} | {record['source_url']}",
        }
        for category, records in analysis["evidence"].items()
        for record in records
    )
    left, right = st.columns(2)
    country = analysis["country"]["iso3"].lower()
    left.download_button(
        "Download Excel industry report",
        build_xlsx(rows, "Dairy Industry Analysis"),
        f"{country}-dairy-industry-analysis.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    right.download_button(
        "Download PDF industry report",
        build_pdf(f"{analysis['country']['country_name']} Dairy Industry Analysis", rows),
        f"{country}-dairy-industry-analysis.pdf",
        "application/pdf",
    )


def _chart(title, labels, series):
    chart_id = f"analysis-chart-{abs(hash((title, tuple(labels))))}"
    configuration = {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": item["label"],
                    "data": item["values"],
                    "borderColor": item["color"],
                    "backgroundColor": item["color"],
                    "borderWidth": 2,
                    "spanGaps": True,
                }
                for item in series
            ],
        },
        "options": {"responsive": True, "maintainAspectRatio": False},
    }
    components.html(
        f'<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>'
        f'<canvas id="{chart_id}" style="max-height:330px"></canvas>'
        f"<script>new Chart(document.getElementById('{chart_id}'), {_safe_json(configuration)});</script>",
        height=350,
    )


def _table(rows, empty_message):
    if not rows:
        st.caption(empty_message)
        return
    headers = list(rows[0])
    st.markdown(
        '<div class="market-table-wrap"><table class="market-table"><thead><tr>'
        + "".join(f"<th>{escape(str(header))}</th>" for header in headers)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join(f"<td>{escape(str(row.get(header, '')))}</td>" for header in headers) + "</tr>"
            for row in rows
        )
        + "</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _flag(iso2):
    return "".join(chr(127397 + ord(letter.upper())) for letter in iso2) if iso2 and len(iso2) == 2 else ""


def _tonnes(value):
    return "Not available" if value is None else f"{value:,.0f} tonnes"


def _percent(value):
    return "Not available" if value is None else f"{value:.2f}%"


def _currency(value):
    return "Not available" if value is None else f"${value:,.0f}"


def _kg_per_capita(value):
    return "Not available" if value is None else f"{value:.1f} kg/person/year"


def _kg_per_animal(value):
    return "Not available" if value is None else f"{value:,.0f} kg/animal/year"


def _evidence_value(record):
    if record["numeric_value"] is not None:
        return f"{record['numeric_value']:,.2f}" + (f" {record['unit']}" if record["unit"] else "")
    return record["text_value"]


def _safe_json(value):
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
