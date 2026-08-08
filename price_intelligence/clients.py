"""Public API clients for permitted retail-price and foreign-exchange sources."""

from datetime import date

import requests

from price_intelligence.catalog import BLS_API_URL, FRANKFURTER_RATES_URL


class PublicPriceClient:
    def __init__(self, timeout_seconds=60):
        self.session = requests.Session()
        self.timeout_seconds = timeout_seconds
        self.session.headers.update(
            {
                "User-Agent": "DairyProcessCalculatorSuite/1.0 (public-price-data-importer)",
                "Accept": "application/json",
            }
        )

    def fetch_bls_series(self, series_id, start_year, end_year):
        response = self.session.get(
            f"{BLS_API_URL}/{series_id}",
            params={"startyear": start_year, "endyear": end_year},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "REQUEST_SUCCEEDED":
            raise ValueError(f"BLS rejected {series_id}: {payload.get('message', [])}")
        series = payload.get("Results", {}).get("series", [])
        if len(series) != 1 or not isinstance(series[0].get("data"), list):
            raise ValueError(f"BLS returned an unexpected response for {series_id}.")
        return series[0]["data"]

    def fetch_exchange_rates(self, base_currency, quote_currencies):
        response = self.session.get(
            FRANKFURTER_RATES_URL,
            params={"base": base_currency, "quotes": ",".join(quote_currencies)},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Frankfurter response has an unexpected shape.")
        rate_date = date.today().isoformat()
        rates = {}
        for record in payload:
            if record.get("base") != base_currency or record.get("quote") not in quote_currencies:
                continue
            rates[record["quote"]] = {"rate": float(record["rate"]), "date": record.get("date", rate_date)}
        if set(rates) != set(quote_currencies):
            missing = set(quote_currencies) - set(rates)
            raise ValueError(f"Frankfurter did not return requested currencies: {', '.join(sorted(missing))}.")
        return rates
