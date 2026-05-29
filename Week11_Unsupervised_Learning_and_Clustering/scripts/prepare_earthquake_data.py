"""
Fetch one year of global M>=4.5 earthquakes from the USGS FDSN web service
and write data/usgs_earthquakes.csv for use in the CE49X Week 11 lecture
on unsupervised learning and clustering.

Usage
-----
    From the Week11 folder, run:

        python scripts/prepare_earthquake_data.py

    The script writes  data/usgs_earthquakes.csv (~100 KB, ~1,500 rows).
    The lecture notebook reads this file directly.

Reproducibility
---------------
    The query window is fixed below (TIME_START / TIME_END) so the output is
    reproducible. Update the constants to refresh data for a future semester.

Source / citation
-----------------
    USGS Earthquake Hazards Program — FDSN event web service.
    https://earthquake.usgs.gov/fdsnws/event/1/
    Data are in the U.S. public domain. See data/README.md for citation.
"""

from __future__ import annotations

import csv
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# ---- Query parameters (edit these to refresh for a future semester) --------
TIME_START = "2024-01-01"
TIME_END = "2024-12-31"
MIN_MAGNITUDE = 4.5
# ---------------------------------------------------------------------------

USGS_ENDPOINT = "https://earthquake.usgs.gov/fdsnws/event/1/query"

OUT_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_CSV = OUT_DIR / "usgs_earthquakes.csv"

# The columns we keep from the USGS CSV (and the names we use in the notebook).
COLUMN_MAP = {
    "time":      "time",
    "latitude":  "latitude",
    "longitude": "longitude",
    "depth":     "depth_km",
    "mag":       "magnitude",
    "magType":   "mag_type",
    "place":     "place",
}


def build_query_url() -> str:
    params = {
        "format":       "csv",
        "starttime":    TIME_START,
        "endtime":      TIME_END,
        "minmagnitude": str(MIN_MAGNITUDE),
        "orderby":      "time",
    }
    return f"{USGS_ENDPOINT}?{urllib.parse.urlencode(params)}"


def fetch_csv(url: str) -> str:
    print(f"GET {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "CE49X-Week11"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read().decode("utf-8")
    return raw


def filter_and_write(raw_csv: str, out_path: Path) -> int:
    reader = csv.DictReader(raw_csv.splitlines())
    out_fields = list(COLUMN_MAP.values())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for row in reader:
            try:
                trimmed = {
                    new: row[old] for old, new in COLUMN_MAP.items()
                }
            except KeyError as e:
                print(f"  unexpected USGS schema: missing column {e}",
                      file=sys.stderr)
                raise
            # Skip rows with blank coordinates / magnitude — rare but possible.
            if not trimmed["latitude"] or not trimmed["longitude"]:
                continue
            if not trimmed["magnitude"]:
                continue
            writer.writerow(trimmed)
            n += 1
    return n


def main() -> None:
    url = build_query_url()
    raw = fetch_csv(url)
    n = filter_and_write(raw, OUT_CSV)
    print(f"wrote {n} rows -> {OUT_CSV}")


if __name__ == "__main__":
    main()
