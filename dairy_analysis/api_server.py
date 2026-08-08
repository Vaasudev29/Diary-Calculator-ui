"""Dependency-free read-only REST API for Dairy Industry Analysis."""

import argparse
import json
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from dairy_analysis import service
from market_opportunities.database import connect, default_database_path, initialize
from price_intelligence.database import initialize as initialize_prices


class AnalysisHandler(BaseHTTPRequestHandler):
    server_version = "DairyIndustryAnalysisAPI/1.0"

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            payload, status = self._route(path)
        except (ValueError, sqlite3.Error, OSError) as error:
            payload, status = {"error": str(error)}, HTTPStatus.BAD_REQUEST
        self._send(payload, status)

    def log_message(self, format_string, *args):
        return

    def _route(self, path):
        if path == "/health":
            return {"status": "ok"}, HTTPStatus.OK
        connection = connect(self.server.database_path)
        initialize(connection)
        initialize_prices(connection)
        try:
            if path == "/api/v1/dairy-analysis/countries":
                return [dict(row) for row in service.country_options(connection)], HTTPStatus.OK
            if path.startswith("/api/v1/dairy-analysis/countries/"):
                iso3 = path.rsplit("/", 1)[-1].upper()
                analysis = service.analyze_country(connection, iso3)
                return (
                    (analysis, HTTPStatus.OK)
                    if analysis
                    else ({"error": "Country not found."}, HTTPStatus.NOT_FOUND)
                )
            return {"error": "Route not found."}, HTTPStatus.NOT_FOUND
        finally:
            connection.close()

    def _send(self, payload, status):
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="Run the Dairy Industry Analysis REST API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--database", default=str(default_database_path()))
    arguments = parser.parse_args()
    server = ThreadingHTTPServer((arguments.host, arguments.port), AnalysisHandler)
    server.database_path = arguments.database
    print(f"Dairy Industry Analysis API listening on http://{arguments.host}:{arguments.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
