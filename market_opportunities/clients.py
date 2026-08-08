"""HTTP clients for authoritative public datasets."""

from time import sleep

import requests

from market_opportunities.catalog import (
    COMTRADE_URL,
    FAOSTAT_BULK_DOWNLOADS_URL,
    FAOSTAT_GUEST_TOKEN_URL,
    NASA_POWER_MONTHLY_URL,
    UN_M49_URL,
    WORLD_BANK_COUNTRIES_URL,
    WORLD_BANK_GDP_URL,
    WORLD_BANK_INDICATOR_URL,
    WORLD_BANK_POPULATION_URL,
)


class OfficialDataClient:
    """Small, explicit client with public-source headers and rate pacing."""

    def __init__(
        self,
        timeout_seconds=60,
        request_pause_seconds=0.75,
        max_rate_limit_retries=4,
        rate_limit_backoff_seconds=5,
    ):
        self.timeout_seconds = timeout_seconds
        self.request_pause_seconds = request_pause_seconds
        self.max_rate_limit_retries = max_rate_limit_retries
        self.rate_limit_backoff_seconds = rate_limit_backoff_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "DairyProcessCalculatorSuite/1.0 "
                    "(official-public-data-market-opportunity-importer)"
                ),
                "Accept": "application/json",
            }
        )

    def _get_json(self, url, params=None):
        for attempt in range(self.max_rate_limit_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout_seconds)
            except requests.RequestException:
                if attempt == self.max_rate_limit_retries:
                    raise
                sleep(self.rate_limit_backoff_seconds * (2**attempt))
                continue
            if response.status_code == 429:
                if attempt == self.max_rate_limit_retries:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                try:
                    wait_seconds = max(float(retry_after), self.request_pause_seconds) if retry_after else (
                        self.rate_limit_backoff_seconds * (2**attempt)
                    )
                except ValueError:
                    wait_seconds = self.rate_limit_backoff_seconds * (2**attempt)
                sleep(wait_seconds)
                continue
            if response.status_code >= 500:
                if attempt == self.max_rate_limit_retries:
                    response.raise_for_status()
                sleep(self.rate_limit_backoff_seconds * (2**attempt))
                continue
            response.raise_for_status()
            sleep(self.request_pause_seconds)
            return response.json()
        raise RuntimeError("Public API request retry loop exited unexpectedly.")

    def fetch_world_bank_countries(self):
        payload = self._get_json(WORLD_BANK_COUNTRIES_URL, {"format": "json", "per_page": 400})
        if not isinstance(payload, list) or len(payload) != 2 or not isinstance(payload[1], list):
            raise ValueError("World Bank country metadata response has an unexpected shape.")
        return payload[1]

    def fetch_world_bank_population(self, start_year, end_year):
        payload = self._get_json(
            WORLD_BANK_POPULATION_URL,
            {
                "format": "json",
                "per_page": 20000,
                "date": f"{start_year}:{end_year}",
            },
        )
        if not isinstance(payload, list) or len(payload) != 2 or not isinstance(payload[1], list):
            raise ValueError("World Bank population response has an unexpected shape.")
        return payload[1]

    def fetch_world_bank_gdp(self, start_year, end_year):
        payload = self._get_json(
            WORLD_BANK_GDP_URL,
            {
                "format": "json",
                "per_page": 20000,
                "date": f"{start_year}:{end_year}",
            },
        )
        if not isinstance(payload, list) or len(payload) != 2 or not isinstance(payload[1], list):
            raise ValueError("World Bank GDP response has an unexpected shape.")
        return payload[1]

    def fetch_world_bank_indicator(self, indicator_code, start_year, end_year):
        payload = self._get_json(
            WORLD_BANK_INDICATOR_URL.format(indicator_code=indicator_code),
            {
                "format": "json",
                "per_page": 20000,
                "date": f"{start_year}:{end_year}",
            },
        )
        if not isinstance(payload, list) or len(payload) != 2 or not isinstance(payload[1], list):
            raise ValueError(f"World Bank indicator {indicator_code} response has an unexpected shape.")
        return payload[1]

    def fetch_nasa_power_monthly(self, latitude, longitude, start_year, end_year):
        payload = self._get_json(
            NASA_POWER_MONTHLY_URL,
            {
                "parameters": "T2M,PRECTOTCORR",
                "community": "AG",
                "longitude": f"{longitude:.4f}",
                "latitude": f"{latitude:.4f}",
                "format": "JSON",
                "start": start_year,
                "end": end_year,
            },
        )
        parameters = payload.get("properties", {}).get("parameter") if isinstance(payload, dict) else None
        if not isinstance(parameters, dict) or not all(isinstance(parameters.get(code), dict) for code in ("T2M", "PRECTOTCORR")):
            raise ValueError("NASA POWER monthly response has an unexpected shape.")
        return parameters

    def fetch_un_m49_areas(self):
        payload = self._get_json(UN_M49_URL)
        if not isinstance(payload, list):
            raise ValueError("UN M49 response has an unexpected shape.")
        return payload

    def fetch_comtrade(self, year, reporter_m49, product_hs, flow, partners=False):
        flow_code = {"Import": "M", "Export": "X"}[flow]
        payload = self._get_json(
            COMTRADE_URL,
            {
                "period": year,
                "reporterCode": reporter_m49,
                "flowCode": flow_code,
                "partnerCode": "all" if partners else "0",
                "cmdCode": product_hs,
                "partner2Code": "0",
                "customsCode": "C00",
                "motCode": "0",
                "maxRecords": 500,
            },
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("UN Comtrade response has an unexpected shape.")
        return payload["data"]

    def fetch_faostat_bulk_url(self, domain_code, expected_file_name):
        """Resolve a current bulk URL through FAOSTAT's official guest-token API."""
        token_response = self.session.post(FAOSTAT_GUEST_TOKEN_URL, timeout=self.timeout_seconds)
        token_response.raise_for_status()
        token_payload = token_response.json()
        token = (
            token_payload.get("token")
            or token_payload.get("access_token")
            or token_payload.get("accessToken")
        )
        if not token:
            raise ValueError("FAOSTAT guest-token response did not include an access token.")
        self.session.headers["Authorization"] = f"Bearer {token}"
        payload = self._get_json(f"{FAOSTAT_BULK_DOWNLOADS_URL}/{domain_code}/")
        records = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(records, list):
            raise ValueError("FAOSTAT bulk-download response has an unexpected shape.")
        for record in records:
            if record.get("FileName") == expected_file_name and record.get("URL"):
                return record["URL"]
        raise ValueError(
            f"FAOSTAT did not publish the expected {expected_file_name} archive for domain {domain_code}."
        )
