# Week 11 Datasets

## USGS Earthquake Catalog (2024, M ≥ 4.5, global)

Used as the **headline real-world dataset** for the Week 11 Unsupervised
Learning & Clustering lecture. One calendar year of significant global
seismicity — large enough to reveal plate-boundary structure, small enough
to cluster on a laptop in seconds.

### Source

- **Provider:** U.S. Geological Survey, Earthquake Hazards Program.
- **Service:** FDSN event web service (CSV format).
- **Endpoint:** https://earthquake.usgs.gov/fdsnws/event/1/
- **Query window:** `starttime=2024-01-01`, `endtime=2024-12-31`,
  `minmagnitude=4.5`, `orderby=time`.

### Citation

> U.S. Geological Survey, Earthquake Hazards Program (2024).
> *Advanced National Seismic System (ANSS) Comprehensive Earthquake Catalog.*
> Accessed via https://earthquake.usgs.gov/fdsnws/event/1/

### License & redistribution

USGS data products are in the **U.S. public domain** unless otherwise noted
(see https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits).
The CSV produced by the prep script is committed to this repository so that
students do not need internet access during lecture.

### How to (re)generate

From the Week11 root directory:

```bash
python scripts/prepare_earthquake_data.py
```

This issues a single HTTPS request to the USGS FDSN service and writes
`data/usgs_earthquakes.csv` (~6,000–7,000 rows, ~550 KB). The query window
is fixed in the script for reproducibility — edit `TIME_START` / `TIME_END`
near the top of the script to refresh for a future semester.

### Schema

| Column | Type | Description |
|---|---|---|
| `time` | str (ISO-8601, UTC) | Event origin time (e.g. `2024-12-30T23:56:29.977Z`) |
| `latitude` | float | Epicenter latitude, decimal degrees (–90, +90) |
| `longitude` | float | Epicenter longitude, decimal degrees (–180, +180) |
| `depth_km` | float | Hypocenter depth below mean sea level, in kilometers |
| `magnitude` | float | Reported magnitude (mixed types — see `mag_type`) |
| `mag_type` | str | Magnitude scale used (`mb`, `mww`, `mwc`, `ml`, …) |
| `place` | str | Human-readable nearest place description |

The notebook reads `data/usgs_earthquakes.csv` directly. The columns most
used for clustering are `latitude`, `longitude`, `depth_km`, and `magnitude`.
