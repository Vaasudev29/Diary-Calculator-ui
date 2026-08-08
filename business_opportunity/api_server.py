"""Dependency-free read-only REST server for Business Opportunity data."""

import argparse
import json
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from business_opportunity import service
from market_opportunities.catalog import PRODUCT_BY_CODE
from market_opportunities.database import connect, default_database_path, initialize


class BusinessOpportunityHandler(BaseHTTPRequestHandler):
    server_version = "DairyBusinessOpportunityAPI/1.0"

    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            payload, status = self._route(parsed.path, parse_qs(parsed.query))
        except ValueError as error:
            payload, status = {"error": str(error)}, HTTPStatus.BAD_REQUEST
        except (OSError, sqlite3.Error):
            self.log_exception("Unhandled API error")
            payload, status = {"error": "Internal server error."}, HTTPStatus.INTERNAL_SERVER_ERROR
        self._send_json(payload, status)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def log_message(self, format_string, *args):
        return

    def log_exception(self, message):
        self.server.logger.error(message, exc_info=True)

    def _route(self, path, query):
        if path == "/health":
            return {"status": "ok"}, HTTPStatus.OK
        connection = connect(self.server.database_path)
        initialize(connection)
        try:
            if path == "/api/v1/business-opportunities/countries":
                return self._countries(connection, query), HTTPStatus.OK
            if path.startswith("/api/v1/business-opportunities/countries/"):
                iso3 = path.rsplit("/", 1)[-1].upper()
                dashboard = service.country_dashboard(connection, iso3)
                if dashboard is None:
                    return {"error": "Country not found."}, HTTPStatus.NOT_FOUND
                return dashboard, HTTPStatus.OK
            if path.startswith("/api/v1/business-opportunities/products/"):
                product_code = path.rsplit("/", 1)[-1]
                if product_code not in PRODUCT_BY_CODE:
                    raise ValueError(f"Unsupported product code: {product_code}.")
                return service.rank_countries_for_product(connection, product_code), HTTPStatus.OK
            return {"error": "Route not found."}, HTTPStatus.NOT_FOUND
        finally:
            connection.close()

    def _countries(self, connection, query):
        limit = int(query.get("limit", ["250"])[0])
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500.")
        return service.country_catalog(
            connection,
            query=query.get("search", [None])[0],
            region=query.get("region", [None])[0],
            continent=query.get("continent", [None])[0],
        )[:limit]

    def _send_json(self, payload, status):
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


def main():
    parser = argparse.ArgumentParser(description="Run the Business Opportunity read-only REST API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--database", default=str(default_database_path()))
    arguments = parser.parse_args()
    import logging

    server = ThreadingHTTPServer((arguments.host, arguments.port), BusinessOpportunityHandler)
    server.logger = logging.getLogger("business_opportunity.api")
    server.database_path = arguments.database
    print(f"Business Opportunity API listening on http://{arguments.host}:{arguments.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
