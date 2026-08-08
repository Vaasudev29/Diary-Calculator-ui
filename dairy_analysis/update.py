"""Command-line importer for cited, permitted dairy-industry evidence."""

import argparse
import os
from pathlib import Path
import sys

# Conda on Windows may omit this DLL directory from PATH for direct `python -m` calls.
_dll_directory = None
if os.name == "nt" and hasattr(os, "add_dll_directory"):
    conda_dll_directory = Path(sys.prefix) / "Library" / "bin"
    if conda_dll_directory.is_dir():
        os.environ["PATH"] = str(conda_dll_directory) + os.pathsep + os.environ.get("PATH", "")
        _dll_directory = os.add_dll_directory(str(conda_dll_directory))

from dairy_analysis.evidence import import_evidence_csv
from market_opportunities.database import connect, initialize
from price_intelligence.database import initialize as initialize_prices


def main():
    parser = argparse.ArgumentParser(description="Merge cited dairy-industry evidence into the local analysis store.")
    parser.add_argument("--evidence-csv", required=True, help="Path to a cited, permitted public-source evidence CSV.")
    parser.add_argument("--dataset-name", default="Country dairy evidence")
    arguments = parser.parse_args()
    connection = connect()
    initialize(connection)
    initialize_prices(connection)
    try:
        with Path(arguments.evidence_csv).open("r", encoding="utf-8-sig", newline="") as evidence_file:
            print({"evidence_records_loaded": import_evidence_csv(connection, evidence_file, arguments.dataset_name)})
    finally:
        connection.close()


if __name__ == "__main__":
    main()
