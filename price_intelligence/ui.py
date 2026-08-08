"""Streamlit dashboard for verified Global Dairy Retail Price Intelligence."""

import json
from html import escape
from io import StringIO

import requests
import streamlit as st
import streamlit.components.v1 as components

from market_opportunities.database import connect, initialize
from market_opportunities.reports import build_pdf, build_xlsx
from price_intelligence import api, repository, service
from price_intelligence.catalog import RETAIL_PRODUCT_BY_CODE, SOURCE_REGISTRY
from price_intelligence.database import initialize as initialize_prices


def render_prices():
    connection = connect()
    initialize(connection)
    initialize_prices(connection)
    api.initialize_price_store(connection)
    try:
        countries = service.map_countries(connection)
        explorer, country, updates, sources = st.tabs(
            ["World Price Map", "Country Price Dashboard", "Data Updates", "Sources & Method"]
        )
        with explorer:
            _render_explorer(connection, countries)
        with country:
            _render_country_dashboard(connection, countries)
        with updates:
            _render_updates(connection)
        with sources:
            _render_sources()
    finally:
        connection.close()


def _render_explorer(connection, countries):
    st.subheader("Global Dairy Retail Price Intelligence")
    st.caption("Only verified public-source retail prices are displayed. Countries without records remain grey.")
    search, region_filter, continent_filter, product_filter = st.columns(4)
    query = search.text_input("Search country", key="prices_search")
    regions = sorted({country["region"] for country in countries if country["region"]})
    region = region_filter.selectbox("Region", ["All regions", *regions], key="prices_region")
    continents = sorted({country["continent"] for country in countries})
    continent = continent_filter.selectbox("Continent", ["All continents", *continents], key="prices_continent")
    product = product_filter.selectbox(
        "Product",
        ["All products", *RETAIL_PRODUCT_BY_CODE],
        format_func=lambda code: "All products" if code == "All products" else RETAIL_PRODUCT_BY_CODE[code].name,
        key="prices_product_filter",
    )
    filtered = [
        country
        for country in service.map_countries(connection, query, region, continent)
        if product == "All products" or _country_has_product(connection, country["iso3"], product)
    ]
    coverage = sum(country["available_products"] for country in filtered)
    countries_count, product_count, latest = st.columns(3)
    countries_count.metric("Countries with verified coverage", sum(country["available_products"] > 0 for country in filtered))
    product_count.metric("Verified product observations", coverage)
    latest.metric("Latest observation", max((country["last_observation_date"] for country in filtered if country["last_observation_date"]), default="Not imported"))
    _render_map(filtered)
    _table(
        [
            {
                "Country": f"{country['flag']} {country['country_name']}",
                "Coverage": country["available_products"],
                "Coverage level": country["coverage_level"],
                "Last verified observation": country["last_observation_date"] or "No verified data",
                "Region": country["region"] or "Not classified",
            }
            for country in filtered
        ],
        "No countries match the selected filters.",
    )


def _render_country_dashboard(connection, countries):
    selectable = [country for country in countries if country["available_products"] > 0]
    if not selectable:
        st.info("No verified retail prices are loaded. Use Data Updates to import an authorized public-source CSV.")
        return
    labels = {f"{country['flag']} {country['country_name']} ({country['iso3']})": country["iso3"] for country in selectable}
    country_label, display_currency = st.columns(2)
    iso3 = labels[country_label.selectbox("Country", list(labels), key="prices_country")]
    output_currency = display_currency.selectbox("View prices in", ["Local", "USD", "EUR", "INR"], key="prices_display_currency")
    product_filter, price_filter = st.columns(2)
    product = product_filter.selectbox(
        "Product filter",
        ["All products", *RETAIL_PRODUCT_BY_CODE],
        format_func=lambda code: "All products" if code == "All products" else RETAIL_PRODUCT_BY_CODE[code].name,
        key="prices_country_product",
    )
    max_price = price_filter.number_input("Maximum local price per kg/liter (optional)", min_value=0.0, value=0.0)
    dashboard = service.country_prices(
        connection,
        iso3,
        "USD" if output_currency == "Local" else output_currency,
        product_code=product,
        price_max=max_price if max_price else None,
    )
    country = dashboard["country"]
    _render_country_kpis(country, dashboard, output_currency)
    _render_price_table(dashboard, output_currency)
    _render_trend(connection, iso3, dashboard, output_currency)
    _render_exports(country, dashboard, output_currency)


def _render_country_kpis(country, dashboard, output_currency):
    country_name, currency, exchange_rate, updated = st.columns(4)
    country_name.metric("Country", f"{_flag(country['iso2'])} {country['country_name']}")
    local_currencies = sorted({price["currency_code"] for price in dashboard["prices"]})
    currency.metric("Source currency", ", ".join(local_currencies) if local_currencies else "No verified prices")
    exchange_rate.metric(
        "Display currency",
        output_currency,
        help=f"Latest Frankfurter rate date: {dashboard['exchange_rate_date']}" if output_currency != "Local" else None,
    )
    updated.metric("Last updated", country["last_observation_date"] or "Not imported")
    coverage, data_level = st.columns(2)
    coverage.metric("Products with verified prices", country["available_products"])
    data_level.metric("Data coverage", dashboard["coverage_level"])


def _render_price_table(dashboard, output_currency):
    st.subheader("Dairy product retail prices")
    rows = [
        {
            "Product": price["product_name"],
            "Standard package": price["package_description"],
            "Typical retail range": price["range_label"],
            "Average price": f"{price['average_price_local']:,.2f} {price['currency_code']}",
            "Currency": price["currency_code"],
            f"Price per {price['normalized_unit']}": _display_price(price, output_currency),
            "Data source": price["source_name"],
            "Last updated": price["observation_date"],
        }
        for price in dashboard["prices"]
    ]
    _table(rows, "No verified public data available for the selected filters.")
    if rows:
        st.caption("Every record includes its original source link; open a source below to verify the published observation.")
        for price in dashboard["prices"]:
            st.markdown(f"- [{price['product_name']} source]({price['source_record_url']}) — {price['source_tier']}")


def _render_trend(connection, iso3, dashboard, output_currency):
    if not dashboard["prices"]:
        return
    choices = {price["product_name"]: price["product_code"] for price in dashboard["prices"]}
    product_name = st.selectbox("Price trend product", list(choices), key="prices_trend_product")
    target_currency = "USD" if output_currency == "Local" else output_currency
    records, _ = service.trends(connection, iso3, choices[product_name], target_currency)
    if len(records) < 2:
        st.caption("Price trend requires at least two verified historical observations.")
        return
    _chart(
        f"{product_name} price trend",
        [record["observation_date"] for record in records],
        [record["display_price_per_unit"] for record in records],
        f"{target_currency} per normalized unit",
    )


def _render_exports(country, dashboard, output_currency):
    rows = [
        {
            "Product": price["product_name"],
            "Package": price["package_description"],
            "Retail range": price["range_label"],
            "Display price": _display_price(price, output_currency),
            "Source": price["source_name"],
            "Source URL": price["source_record_url"],
            "Updated": price["observation_date"],
        }
        for price in dashboard["prices"]
    ]
    left, right = st.columns(2)
    left.download_button(
        "Download Excel price report",
        build_xlsx(rows, "Retail Prices"),
        f"{country['iso3'].lower()}-dairy-retail-prices.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    right.download_button(
        "Download PDF price report",
        build_pdf(f"{country['country_name']} Dairy Retail Prices", rows),
        f"{country['iso3'].lower()}-dairy-retail-prices.pdf",
        "application/pdf",
    )


def _render_updates(connection):
    st.subheader("Verified public data updates")
    st.caption("Imports are accepted only with source URL, source tier, and a permitted-use/license note. The platform does not scrape restricted websites.")
    if st.button("Refresh USD/EUR/INR exchange rates"):
        try:
            loaded = api.refresh_exchange_rates(connection)
        except (requests.RequestException, ValueError, OSError) as error:
            st.error(f"Exchange-rate refresh failed: {error}")
        else:
            st.success(f"Loaded {loaded} official central-bank exchange rates.")
    uploaded = st.file_uploader("Authorized public-source CSV", type="csv")
    source_name = st.text_input("Source name")
    source_url = st.text_input("Original source URL")
    source_tier = st.selectbox(
        "Source tier",
        ["Official government statistics", "Official open-data portal", "Permitted public retail portal"],
    )
    license_note = st.text_input("License / permitted-use note")
    with st.expander("Required CSV columns"):
        st.code(
            "country_iso3,product_code,observation_date,package_description,package_quantity,"
            "package_unit,price_low_local,price_high_local,currency_code,source_record_url,published_at"
        )
        st.caption("Package units: kg, g, liter, ml. Retail product codes are listed under Sources & Method.")
    if st.button("Validate and import verified prices", disabled=uploaded is None):
        try:
            text_file = StringIO(uploaded.getvalue().decode("utf-8-sig"))
            loaded = api.import_public_price_csv(connection, text_file, source_name, source_url, source_tier, license_note)
        except (UnicodeDecodeError, ValueError, OSError, requests.RequestException) as error:
            st.error(f"Price import failed and was audited: {error}")
        else:
            st.success(f"Validated and loaded {loaded} verified retail price observations.")
    statuses = repository.price_update_status(connection)
    if statuses:
        _table(
            [
                {
                    "Source": row["source_name"],
                    "Dataset": row["dataset"],
                    "Status": row["status"],
                    "Records": row["records_loaded"],
                    "Completed": row["completed_at"] or "In progress",
                    "Detail": row["detail"] or "",
                }
                for row in statuses
            ],
            "No updates recorded.",
        )


def _render_sources():
    st.subheader("Verified source policy")
    for source in SOURCE_REGISTRY:
        with st.expander(source["name"], expanded=True):
            st.write(source["coverage"])
            st.caption(source["tier"])
            st.write(source["automation"])
            if source["url"]:
                st.markdown(f"[Source documentation or feed]({source['url']})")
    st.markdown("#### Supported product codes")
    _table(
        [{"Product code": code, "Product": product.name, "Normalized unit": product.normalized_unit} for code, product in RETAIL_PRODUCT_BY_CODE.items()],
        "No products configured.",
    )
    st.write(
        "Government portals that require CAPTCHA, authentication, or prohibit automated collection are not scraped. "
        "For those sources, download the authorized public file manually and import it with its source metadata."
    )


def _render_map(countries):
    points = [
        {
            "country": country["country_name"],
            "lat": country["latitude"],
            "lon": country["longitude"],
            "coverage": country["available_products"],
            "level": country["coverage_level"],
        }
        for country in countries
        if country["latitude"] is not None and country["longitude"] is not None
    ]
    components.html(
        f"""
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <div id="price-map" style="height:420px;border-radius:12px"></div>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
          const map = L.map('price-map', {{scrollWheelZoom:false}}).setView([20, 0], 2);
          L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{attribution:'&copy; OpenStreetMap contributors'}}).addTo(map);
          {_safe_json(points)}.forEach(point => {{
            const color = point.coverage >= 12 ? '#087e3b' : point.coverage >= 5 ? '#70ad47' : point.coverage ? '#b7cf9e' : '#8d99a5';
            L.circleMarker([point.lat, point.lon], {{radius:6, color, fillColor:color, fillOpacity:.8}})
              .bindPopup(`<strong>${{point.country}}</strong><br>${{point.coverage}} verified product(s)<br>${{point.level}} coverage`).addTo(map);
          }});
        </script>
        """,
        height=440,
    )


def _country_has_product(connection, iso3, product_code):
    return bool(
        connection.execute(
            "SELECT 1 FROM retail_prices WHERE country_iso3 = ? AND product_code = ? LIMIT 1",
            (iso3, product_code),
        ).fetchone()
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


def _chart(title, labels, values, label):
    chart_id = f"price-chart-{abs(hash((title, tuple(labels))))}"
    configuration = {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": label,
                    "data": values,
                    "borderColor": "#087e8b",
                    "backgroundColor": "rgba(8,126,139,.35)",
                    "borderWidth": 2,
                    "fill": True,
                }
            ],
        },
        "options": {"responsive": True, "maintainAspectRatio": False},
    }
    components.html(
        f'<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>'
        f'<canvas id="{chart_id}" style="max-height:320px"></canvas>'
        f"<script>new Chart(document.getElementById('{chart_id}'), {_safe_json(configuration)});</script>",
        height=350,
    )


def _display_price(price, output_currency):
    if output_currency == "Local":
        return f"{price['price_per_normalized_unit']:,.2f} {price['currency_code']}/{price['normalized_unit']}"
    if price["display_price_per_unit"] is None:
        return "No verified exchange rate available"
    return f"{price['display_price_per_unit']:,.2f} {price['display_currency']}/{price['normalized_unit']}"


def _flag(iso2):
    return service.country_flag(iso2)


def _safe_json(value):
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
