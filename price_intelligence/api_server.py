"""Dependency-free read-only REST API for Global Dairy Retail Price Intelligence."""

import argparse
import json
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from market_opportunities.database import connect, default_database_path, initialize
from price_intelligence.database import initialize as initialize_prices
from price_intelligence import service


class PriceHandler(BaseHTTPRequestHandler):
    server_version = "DairyRetailPriceAPI/1.0"

    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            payload, status = self._route(parsed.path, parse_qs(parsed.query))
        except ValueError as error:
            payload, status = {"error": str(error)}, HTTPStatus.BAD_REQUEST
        except (OSError, sqlite3.Error):
            payload, status = {"error": "Internal server error."}, HTTPStatus.INTERNAL_SERVER_ERROR
        self._send(payload, status)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors()
        self.end_headers()

    def log_message(self, format_string, *args):
        return

    def _route(self, path, query):
        if path == "/health":
            return {"status": "ok"}, HTTPStatus.OK
        connection = connect(self.server.database_path)
        initialize(connection)
        initialize_prices(connection)
        try:
            if path == "/api/v1/prices/countries":
                return service.map_countries(
                    connection,
                    query=query.get("search", [None])[0],
                    region=query.get("region", [None])[0],
                    continent=query.get("continent", [None])[0],
                ), HTTPStatus.OK
            if path.startswith("/api/v1/prices/countries/"):
                iso3 = path.rsplit("/", 1)[-1].upper()
                currency = query.get("currency", ["USD"])[0].upper()
                dashboard = service.country_prices(connection, iso3, currency)
                return (
                    (dashboard, HTTPStatus.OK)
                    if dashboard
                    else ({"error": "Country not found."}, HTTPStatus.NOT_FOUND)
                )
            return {"error": "Route not found."}, HTTPStatus.NOT_FOUND
        finally:
            connection.close()

    def _send(self, payload, status):
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")


def main():
    parser = argparse.ArgumentParser(description="Run the read-only Dairy Retail Price Intelligence API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--database", default=str(default_database_path()))
    arguments = parser.parse_args()
    server = ThreadingHTTPServer((arguments.host, arguments.port), PriceHandler)
    server.database_path = arguments.database
    print(f"Prices API listening on http://{arguments.host}:{arguments.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
