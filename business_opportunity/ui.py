"""Premium Streamlit presentation layer for country-level business opportunities."""

import json
import os
from html import escape

import streamlit as st
import streamlit.components.v1 as components

from business_opportunity import service
from market_opportunities.catalog import PRODUCT_BY_CODE
from market_opportunities.database import connect, default_database_path, initialize
from market_opportunities.reports import build_pdf, build_xlsx


def render_business_opportunity():
    connection = connect()
    initialize(connection)
    try:
        countries = service.country_catalog(connection)
    finally:
        connection.close()

    st.title("Business Opportunity")
    st.caption("Country-level export and investment intelligence from imported official datasets.")
    if not countries:
        st.info(
            "No country catalogue is loaded. Open Market Opportunities → Data Updates and initialize "
            "the World Bank and UN reference catalogue first."
        )
        return

    explorer_tab, country_tab, comparison_tab, methodology_tab = st.tabs(
        ["Global Explorer", "Country Dashboard", "Country Comparison", "Data & Method"]
    )
    with explorer_tab:
        _render_global_explorer(countries)
    with country_tab:
        _render_country_dashboard(countries)
    with comparison_tab:
        _render_comparison(countries)
    with methodology_tab:
        _render_methodology()


def _render_global_explorer(countries):
    search_column, continent_column, region_column = st.columns([2, 1, 1])
    query = search_column.text_input("Search country", placeholder="Morocco", key="business_country_search")
    continents = sorted({country["continent"] for country in countries})
    continent = continent_column.selectbox("Continent group", ["All continents", *continents])
    regions = sorted({country["region"] for country in countries if country["region"]})
    region = region_column.selectbox("World Bank region", ["All regions", *regions])
    visible_countries = [
        country
        for country in countries
        if (not query or query.casefold() in country["country_name"].casefold())
        and (continent == "All continents" or country["continent"] == continent)
        and (region == "All regions" or country["region"] == region)
    ]
    st.metric("Countries available", len(visible_countries))
    _render_country_map(visible_countries)
    _html_table(
        [
            {
                "Country": f"{country['flag']} {country['country_name']}",
                "ISO3": country["iso3"],
                "Continent group": country["continent"],
                "Region": country["region"] or "Not classified",
                "Income group": country["income_level"] or "Not classified",
            }
            for country in visible_countries[:100]
        ],
        "No countries matched the selected filters.",
    )
    st.caption(
        "Country points use World Bank coordinates. Select a country in the Country Dashboard tab "
        "for its full business-opportunity analysis."
    )


def _render_country_dashboard(countries):
    country_by_label = {f"{country['flag']} {country['country_name']} ({country['iso3']})": country for country in countries}
    selected_label = st.selectbox("Select country", list(country_by_label), key="business_country")
    selected_country = country_by_label[selected_label]
    dashboard = _load_dashboard(selected_country["iso3"])
    if dashboard is None:
        st.error("This country was not found in the local business intelligence store.")
        return

    _render_overview(dashboard)
    _render_production(dashboard["production"])
    _render_product_opportunities(dashboard["products"])
    _render_competitors(selected_country["iso3"])
    _render_insights(dashboard)
    _render_downloads(dashboard)


def _render_overview(dashboard):
    country = dashboard["country"]
    st.subheader(f"{country['flag']} {country['country_name']} business opportunity")
    population, gdp, currency, updated = st.columns(4)
    population.metric(
        "Population",
        f"{country['population']:,}" if country["population"] is not None else "Not imported",
    )
    gdp.metric(
        "GDP (current USD)",
        _currency(country["gdp_current_usd"]),
        help=f"World Bank year: {country['gdp_year']}" if country["gdp_year"] else "Not imported",
    )
    currency.metric("Currency", country["currency"])
    updated.metric("Last data updated", dashboard["last_data_updated"] or "No observations loaded")

    opportunity, level, region, industry = st.columns(4)
    opportunity.metric("Business opportunity", f"{dashboard['overall_score']:.1f}/10")
    level.metric("Opportunity level", dashboard["opportunity_level"])
    region.metric("Region", country["region"] or "Not classified")
    industry.metric(
        "Dairy industry overview",
        "Fresh milk data loaded" if dashboard["production"]["total_milk_tonnes"] is not None else "Production data not loaded",
    )


def _render_production(production):
    st.subheader("Local dairy production")
    total, cow, buffalo, goat, sheep, growth = st.columns(6)
    total.metric("Total milk", _tonnes(production["total_milk_tonnes"]))
    cow.metric("Cow milk", _tonnes(production["cow_milk_tonnes"]))
    buffalo.metric("Buffalo milk", _tonnes(production["buffalo_milk_tonnes"]))
    goat.metric("Goat milk", _tonnes(production["goat_milk_tonnes"]))
    sheep.metric("Sheep milk", _tonnes(production["sheep_milk_tonnes"]))
    growth.metric("Annual growth", _percent(production["growth_pct"]))
    trend = production["five_year_trend"]
    if trend:
        _chart(
            "Five-year total milk production trend",
            "line",
            [row["year"] for row in trend],
            [row["total_milk_tonnes"] for row in trend],
            "Total milk (tonnes)",
        )
    else:
        st.caption("No FAOSTAT production records are loaded for this country.")


def _render_product_opportunities(products):
    st.subheader("Product-wise market analysis")
    rows = [
        {
            "Product": product["product"],
            "Production": _tonnes(product["production_tonnes"]),
            "Demand": _tonnes(product["demand_tonnes"]),
            "Imports": _kilograms(product["import_quantity_kg"]),
            "Exports": _kilograms(product["export_quantity_kg"]),
            "Consumption": _per_capita(product["consumption_kg_per_capita"]),
            "Supply gap": _tonnes(product["supply_gap_tonnes"]),
            "Opportunity": _opportunity_badge(product["opportunity_level"]),
            "Score": f"{product['opportunity_score']:.1f}/100",
        }
        for product in products
    ]
    _html_table(rows, "No product records are available.")
    st.caption(
        "Production, demand, consumption, and supply gap are shown only when compatible official "
        "FAOSTAT observations have been imported. Product trade and opportunity scores use UN Comtrade."
    )
    product_by_label = {product["product"]: product for product in products}
    selected_product = st.selectbox("Inspect product market", list(product_by_label), key="business_product_detail")
    product = product_by_label[selected_product]
    _render_product_detail(product)


def _render_product_detail(product):
    st.markdown(f"#### {product['product']} import and export analysis")
    imports, import_value, import_price, growth = st.columns(4)
    imports.metric("Import quantity", _kilograms(product["import_quantity_kg"]))
    import_value.metric("Import value", _currency(product["import_value_usd"]))
    import_price.metric("Average import price", _price(product["average_import_price_usd_per_kg"]))
    growth.metric("Import growth", _percent(product["import_growth_pct"]))
    if product["import_trend"]:
        _chart(
            f"{product['product']} five-year import trend",
            "line",
            [row["year"] for row in product["import_trend"]],
            [row["value_usd"] or 0 for row in product["import_trend"]],
            "Import value (USD)",
        )
    suppliers, exports = st.columns(2)
    with suppliers:
        st.markdown("**Top supplier countries**")
        _html_table(
            [
                {
                    "Supplier": row["partner_name"],
                    "Market share": _percent(row["market_share_pct"]),
                    "Import value": _currency(row["value_usd"]),
                    "Year": row["year"],
                }
                for row in product["top_suppliers"]
            ],
            "Partner routes have not been imported for this product.",
        )
    with exports:
        st.markdown("**Major export destinations**")
        _html_table(
            [
                {
                    "Destination": row["partner_name"],
                    "Export value": _currency(row["value_usd"]),
                    "Year": row["year"],
                }
                for row in product["top_destinations"]
            ],
            "Partner routes have not been imported for this product.",
        )
    st.caption(product["score_method"])


def _render_competitors(iso3):
    connection = connect()
    initialize(connection)
    try:
        competitors = service.competitor_analysis(connection, iso3)
    finally:
        connection.close()
    st.subheader("Competitor analysis")
    _html_table(
        [
            {
                "Supplier country": row["supplier"],
                "Aggregate market share": _percent(row["market_share_pct"]),
                "Imported value": _currency(row["import_value_usd"]),
                "Product categories": row["product_categories"],
                "Latest route year": row["latest_year"],
                "Position": "Leading supplier" if index == 0 else "Active supplier",
            }
            for index, row in enumerate(competitors)
        ],
        "Import partner routes have not been imported. Enable partner routes in Market Opportunities → Data Updates.",
    )


def _render_insights(dashboard):
    st.subheader("AI Business Insights")
    st.caption("Rules-based executive insights generated strictly from imported official observations.")
    for insight in dashboard["insights"]:
        st.write(f"- {insight}")


def _render_downloads(dashboard):
    rows = [
        {
            "Product": product["product"],
            "Opportunity score": f"{product['opportunity_score']:.1f}",
            "Opportunity level": product["opportunity_level"],
            "Import value (USD)": _currency(product["import_value_usd"]),
            "Import growth": _percent(product["import_growth_pct"]),
            "Supply gap": _tonnes(product["supply_gap_tonnes"]),
        }
        for product in dashboard["products"]
    ]
    left, right = st.columns(2)
    safe_country = dashboard["country"]["iso3"].lower()
    left.download_button(
        "Download Excel business report",
        build_xlsx(rows, "Business Opportunity"),
        f"{safe_country}-business-opportunity.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    right.download_button(
        "Download PDF business report",
        build_pdf(f"{dashboard['country']['country_name']} Business Opportunity", rows),
        f"{safe_country}-business-opportunity.pdf",
        "application/pdf",
    )


def _render_comparison(countries):
    by_label = {f"{country['flag']} {country['country_name']} ({country['iso3']})": country["iso3"] for country in countries}
    labels = st.multiselect("Countries to compare", list(by_label), max_selections=5, key="business_comparison")
    if len(labels) < 2:
        st.info("Select at least two countries to compare business opportunity profiles.")
        return
    connection = connect()
    initialize(connection)
    try:
        comparisons = service.country_comparison(connection, [by_label[label] for label in labels])
    finally:
        connection.close()
    _chart(
        "Overall business opportunity comparison",
        "bar",
        [row["country"] for row in comparisons],
        [row["overall_score"] for row in comparisons],
        "Opportunity score (out of 10)",
    )
    _html_table(
        [
            {
                "Country": row["country"],
                "Business score": f"{row['overall_score']:.1f}/10",
                "Level": row["opportunity_level"],
                "Population": f"{row['population']:,}" if row["population"] else "Not imported",
                "GDP": _currency(row["gdp_current_usd"]),
                "Top loaded product": row["top_product"],
            }
            for row in comparisons
        ],
        "No comparison records are available.",
    )


def _render_methodology():
    st.subheader("Data, scores, and limitations")
    st.write(
        "The module uses the same normalized official-data store as Market Opportunities: UN Comtrade "
        "for annual HS trade and partner routes; FAOSTAT for fresh milk production and Food Balance Sheets; "
        "and World Bank Open Data for country, population, and GDP context."
    )
    st.write(
        "Product opportunities are sorted by the transparent import-led opportunity score. Supply gaps "
        "and import dependency appear only when compatible official demand and production data exists. "
        "No country currency values, production estimates, demand estimates, or supplier shares are fabricated."
    )
    st.write(
        "The 'AI Business Insights' panel is deliberately rules-based: it narrates the latest loaded official "
        "observations and clearly reports when the relevant source data has not been loaded."
    )


@st.cache_data(ttl=300, show_spinner=False)
def _cached_dashboard(database_path, database_mtime, iso3):
    del database_mtime
    connection = connect(database_path)
    initialize(connection)
    try:
        return service.country_dashboard(connection, iso3)
    finally:
        connection.close()


def _load_dashboard(iso3):
    path = default_database_path()
    modified_at = os.path.getmtime(path) if path.exists() else 0
    return _cached_dashboard(os.fspath(path), modified_at, iso3)


def _render_country_map(countries):
    points = [
        {
            "country": country["country_name"],
            "lat": country["latitude"],
            "lon": country["longitude"],
            "region": country["region"],
        }
        for country in countries
        if country["latitude"] is not None and country["longitude"] is not None
    ]
    if not points:
        return
    components.html(
        f"""
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <div id="business-map" style="height:390px;border-radius:12px"></div>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
          const map = L.map('business-map', {{scrollWheelZoom:false}}).setView([20, 0], 2);
          L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; OpenStreetMap contributors'
          }}).addTo(map);
          {_safe_json(points)}.forEach(point => {{
            L.circleMarker([point.lat, point.lon], {{radius:5, color:'#087e8b', fillOpacity:.7}})
              .bindPopup(`<strong>${{point.country}}</strong><br>${{point.region || 'No region'}}`).addTo(map);
          }});
        </script>
        """,
        height=410,
    )


def _chart(title, chart_type, labels, values, label):
    if not labels:
        return
    chart_id = f"business-chart-{abs(hash((title, tuple(labels))))}"
    configuration = {
        "type": chart_type,
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": label,
                    "data": values,
                    "borderColor": "#087e8b",
                    "backgroundColor": "rgba(8,126,139,.35)",
                    "borderWidth": 2,
                    "fill": chart_type == "line",
                }
            ],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {"title": {"display": True, "text": title}},
            "scales": {"y": {"beginAtZero": True}},
        },
    }
    components.html(
        f"""
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
        <canvas id="{chart_id}" style="max-height:320px"></canvas>
        <script>
          new Chart(document.getElementById('{chart_id}'), {_safe_json(configuration)});
        </script>
        """,
        height=350,
    )


def _html_table(rows, empty_message):
    if not rows:
        st.caption(empty_message)
        return
    headers = list(rows[0])
    header_html = "".join(f"<th>{escape(str(header))}</th>" for header in headers)
    rows_html = "".join(
        "<tr>" + "".join(f"<td>{escape(str(row.get(header, '')))}</td>" for header in headers) + "</tr>"
        for row in rows
    )
    st.markdown(
        f'<div class="market-table-wrap"><table class="market-table"><thead><tr>{header_html}</tr></thead>'
        f"<tbody>{rows_html}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _opportunity_badge(level):
    colors = {
        "Excellent": "🟢",
        "Strong": "🟢",
        "Moderate": "🟡",
        "Emerging": "🟠",
        "Insufficient official data": "⚪",
    }
    return f"{colors[level]} {level}"


def _safe_json(value):
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _currency(value):
    return "Not imported" if value is None else f"${value:,.0f}"


def _tonnes(value):
    return "Not imported" if value is None else f"{value:,.0f} MT"


def _kilograms(value):
    return "Not imported" if value is None else f"{value:,.0f} kg"


def _percent(value):
    return "Not imported" if value is None else f"{value:.1f}%"


def _per_capita(value):
    return "Not imported" if value is None else f"{value:.1f} kg/capita/yr"


def _price(value):
    return "Not imported" if value is None else f"${value:.2f}/kg"
