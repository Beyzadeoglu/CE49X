"""
CE49X Final Project one-command runner.

How to use:
1. Put this file in your project root.
2. Start PostgreSQL first with: docker compose up -d
3. Run with: python CE49X_Final_Project_Run_All.py
4. Paste your FIRMS MAP_KEY when the terminal asks for it.
"""

# %% [markdown]
# # CE49X Final Project: Conflict Situation Monitoring for Maritime Shipping
#
# This notebook collects NASA FIRMS thermal anomalies, collects conflict-related
# news, stores everything in PostgreSQL, clusters thermal events, matches events
# to news, trains classifiers, and creates the required dashboard.

# %% [markdown]
# ## 0. Setup

# %%
from __future__ import annotations

import os
import sys

os.environ.setdefault("MPLBACKEND", "Agg")

print("Starting CE49X final project runner...", flush=True)
FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "").strip()
if not FIRMS_MAP_KEY:
    print("NASA FIRMS MAP_KEY was not found in the environment.", flush=True)
    FIRMS_MAP_KEY = input("Paste your NASA FIRMS MAP_KEY and press Enter, or press Enter to resume existing database: ").strip()
if FIRMS_MAP_KEY:
    print("MAP_KEY received. Loading Python libraries...", flush=True)
else:
    print("No MAP_KEY entered. Loading Python libraries and trying to resume from database...", flush=True)

import re
import time
import math
from io import StringIO
from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

print("Importing numpy...", flush=True)
import numpy as np
print("Importing pandas...", flush=True)
import pandas as pd
print("Importing requests...", flush=True)
import requests
print("Importing BeautifulSoup...", flush=True)
from bs4 import BeautifulSoup

print("Importing matplotlib...", flush=True)
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
print("Importing seaborn...", flush=True)
import seaborn as sns

print("Importing IPython display...", flush=True)
from IPython.display import display
print("Importing scipy...", flush=True)
from scipy import stats

print("Importing scikit-learn...", flush=True)
from sklearn.cluster import DBSCAN
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC

print("Importing database library...", flush=True)
from sqlalchemy import create_engine, text

print("Libraries loaded successfully.", flush=True)
sns.set_theme(style="whitegrid", context="notebook")
pd.set_option("display.max_columns", 100)

PROJECT_ROOT = Path.cwd()
DATA_DIR = PROJECT_ROOT / "data"
FIG_DIR = PROJECT_ROOT / "figures"
DATA_DIR.mkdir(exist_ok=True)
FIG_DIR.mkdir(exist_ok=True)

DB_URL = os.getenv("DATABASE_URL", "postgresql://ce49x@localhost:5432/conflict_monitoring")

START_DATE = "2024-01-01"
END_DATE = "2024-06-30"
FIRMS_SOURCE = "VIIRS_SNPP_SP"
REQUEST_SLEEP_SECONDS = 1.0
NEWS_SLEEP_SECONDS = 6.0

CONFLICT_KEYWORDS = [
    "war", "conflict", "military", "bombing", "airstrike", "shelling",
    "missile", "attack", "troops", "armed", "explosion", "combat",
]

REGIONS = {
    "Ukraine_Black_Sea": {
        "bbox": (22.0, 44.0, 41.0, 53.0),
        "aliases": ["Ukraine", "Black Sea", "Crimea", "Odesa", "Donetsk", "Kherson"],
        "justification": "Black Sea grain, oil, and insurance risk corridor affected by the Russia-Ukraine war.",
    },
    "Red_Sea_Yemen": {
        "bbox": (32.0, 12.0, 44.0, 21.0),
        "aliases": ["Yemen", "Red Sea", "Sanaa", "Hodeidah", "Bab el-Mandeb", "Houthis"],
        "justification": "Bab el-Mandeb and Red Sea shipping lanes are critical for Europe-Asia trade and energy flows.",
    },
    "Persian_Gulf": {
        "bbox": (43.0, 24.0, 57.0, 33.0),
        "aliases": ["Persian Gulf", "Iraq", "Iran", "Kuwait", "Basra", "Hormuz"],
        "justification": "Major oil export region where conflict can affect energy prices and tanker routing.",
    },
    "Eastern_Mediterranean": {
        "bbox": (29.0, 29.0, 42.5, 38.0),
        "aliases": ["Gaza", "Israel", "Lebanon", "Syria", "Eastern Mediterranean"],
        "justification": "Conflict-prone region near Suez-linked shipping and offshore energy infrastructure.",
    },
}

print(f"Project root: {PROJECT_ROOT}")
print(f"Date range: {START_DATE} to {END_DATE}")
print(f"Regions: {list(REGIONS)}")

# %% [markdown]
# ## 1. Database Helpers

# %%
engine = create_engine(DB_URL)

def write_table(df: pd.DataFrame, table_name: str) -> None:
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"Wrote {len(df):,} rows to {table_name}")

def read_table(table_name: str) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM {table_name}", engine)

def verify_tables() -> pd.DataFrame:
    query = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name;
    """
    return pd.read_sql(query, engine)

def table_exists(table_name: str) -> bool:
    query = """
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = :table_name
    ) AS exists;
    """
    with engine.connect() as conn:
        return bool(conn.execute(text(query), {"table_name": table_name}).scalar())

def table_count(table_name: str) -> int:
    if not table_exists(table_name):
        return 0
    with engine.connect() as conn:
        return int(conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar())

try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("Database connection OK")
except Exception as exc:
    print("\nPostgreSQL connection failed.")
    print("Open Docker Desktop, then run this in the outputs folder:")
    print("  docker compose up -d")
    print(f"\nOriginal error: {exc}")
    sys.exit(1)

# %% [markdown]
# ## 2. Task 1A: NASA FIRMS Data Collection
#
# FIRMS area endpoint used:
# `https://firms.modaps.eosdis.nasa.gov/api/area/csv/[MAP_KEY]/[SOURCE]/[BBOX]/[DAY_RANGE]/[DATE]`
#
# The assignment says historical API requests return up to 5 days, so this code
# loops over 5-day chunks.

# %%
def date_chunks(start_date: str, end_date: str, chunk_days: int = 5):
    start = pd.to_datetime(start_date).date()
    end = pd.to_datetime(end_date).date()
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end)
        yield current, chunk_end, (chunk_end - current).days + 1
        current = chunk_end + timedelta(days=1)

def fetch_firms_chunk(
    map_key: str,
    source: str,
    bbox: tuple[float, float, float, float],
    chunk_start,
    day_range: int,
    region_name: str,
) -> pd.DataFrame:
    west, south, east, north = bbox
    area = f"{west},{south},{east},{north}"
    url = (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{map_key}/{source}/{area}/{day_range}/{chunk_start:%Y-%m-%d}"
    )
    response = requests.get(url, timeout=90)
    response.raise_for_status()

    if response.text.strip().lower().startswith(("invalid", "error")):
        raise RuntimeError(f"FIRMS API returned an error for {region_name}: {response.text[:300]}")

    df = pd.read_csv(StringIO(response.text))
    if df.empty:
        return df
    df["region"] = region_name
    df["firms_source"] = source
    df["api_url"] = url.replace(map_key, "[MAP_KEY]")
    return df

def collect_firms_data() -> pd.DataFrame:
    if not FIRMS_MAP_KEY or FIRMS_MAP_KEY == "PASTE_YOUR_FIRMS_MAP_KEY_HERE":
        raise ValueError("Set FIRMS_MAP_KEY before collecting NASA FIRMS data.")

    frames = []
    for region_name, info in REGIONS.items():
        print(f"Collecting FIRMS for {region_name}")
        for chunk_start, chunk_end, day_range in date_chunks(START_DATE, END_DATE, 5):
            df_chunk = fetch_firms_chunk(
                FIRMS_MAP_KEY,
                FIRMS_SOURCE,
                info["bbox"],
                chunk_start,
                day_range,
                region_name,
            )
            frames.append(df_chunk)
            print(f"  {chunk_start} to {chunk_end}: {len(df_chunk):,} rows")
            time.sleep(REQUEST_SLEEP_SECONDS)

    df_firms_raw = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    df_firms_raw = df_firms_raw.drop_duplicates()
    return df_firms_raw

# Run this cell after setting FIRMS_MAP_KEY.
if table_exists("firms_detections"):
    print(f"Skipping FIRMS download; firms_detections already has {table_count('firms_detections'):,} rows.")
    df_firms_raw = pd.DataFrame()
else:
    df_firms_raw = collect_firms_data()
    print(df_firms_raw.shape)
    df_firms_raw.head()

# %% [markdown]
# ## 3. Task 1A: FIRMS Cleaning and Exploration

# %%
def clean_firms_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    if "bright_ti4" in df.columns and "brightness" not in df.columns:
        df["brightness"] = df["bright_ti4"]
    if "frp" not in df.columns:
        raise ValueError("Expected FIRMS column 'frp' was not found.")

    df["acq_time"] = df["acq_time"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(4)
    df["acq_datetime"] = pd.to_datetime(
        df["acq_date"].astype(str) + " " + df["acq_time"],
        format="%Y-%m-%d %H%M",
        errors="coerce",
        utc=True,
    )
    df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce").dt.date

    for col in ["latitude", "longitude", "brightness", "frp"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["latitude", "longitude", "acq_datetime", "frp", "brightness", "region"])
    df = df[(df["latitude"].between(-90, 90)) & (df["longitude"].between(-180, 180))]
    df = df[df["frp"] >= 0]

    # VIIRS confidence is often "low", "nominal", or "high".
    # Keep nominal/high to remove lower-quality thermal detections.
    if "confidence" in df.columns:
        conf_numeric = pd.to_numeric(df["confidence"], errors="coerce")
        if conf_numeric.notna().mean() > 0.8:
            df = df[conf_numeric >= 30]
        else:
            df["confidence"] = df["confidence"].astype(str).str.lower()
            df = df[df["confidence"].isin(["nominal", "high", "n", "h"])]

    after = len(df)
    print(f"Rows before cleaning: {before:,}")
    print(f"Rows after cleaning:  {after:,}")
    print(f"Removed:              {before - after:,}")
    return df.reset_index(drop=True)

if table_exists("firms_detections") and df_firms_raw.empty:
    df_firms = read_table("firms_detections")
    print(f"Loaded existing cleaned FIRMS table: {len(df_firms):,} rows.")
else:
    df_firms = clean_firms_data(df_firms_raw)
    display(df_firms.head())
    display(df_firms.describe(include="all"))
    display(df_firms.isna().sum().sort_values(ascending=False).head(20))
    print(df_firms["region"].value_counts())
    write_table(df_firms, "firms_detections")

# %% [markdown]
# ## 4. Task 1B: War and Conflict News Collection
#
# This uses two sources:
# 1. GDELT DOC 2.1 API
# 2. Google News RSS search
#
# Both are collected over the same region/date window as the FIRMS data.

# %%
def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()

def region_query_terms(region_info: dict) -> str:
    return " OR ".join(f'"{alias}"' if " " in alias else alias for alias in region_info["aliases"])

def keyword_query_terms() -> str:
    return " OR ".join(CONFLICT_KEYWORDS)

def extract_location_mentions(text_value: str, region_info: dict) -> str:
    text_value = normalize_text(text_value)
    found = []
    for alias in region_info["aliases"]:
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, text_value, flags=re.IGNORECASE):
            found.append(alias)
    return "; ".join(sorted(set(found)))

def get_with_backoff(url: str, params: dict | None = None, headers: dict | None = None, attempts: int = 4):
    """Request a URL and wait longer if a news provider rate-limits the notebook."""
    for attempt in range(attempts):
        response = requests.get(url, params=params, headers=headers, timeout=60)
        if response.status_code == 429:
            wait_seconds = NEWS_SLEEP_SECONDS * (attempt + 1)
            print(f"Rate limited by news source. Waiting {wait_seconds:.0f}s before retry {attempt + 1}/{attempts}.")
            time.sleep(wait_seconds)
            continue
        response.raise_for_status()
        return response
    print(f"Skipped after repeated rate limits: {url}")
    return None

def fetch_gdelt_articles(region_name: str, region_info: dict, start_date: str, end_date: str) -> pd.DataFrame:
    frames = []
    for chunk_start, chunk_end, _ in date_chunks(start_date, end_date, 31):
        query = f"({region_query_terms(region_info)}) ({keyword_query_terms()})"
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": 250,
            "sort": "HybridRel",
            "startdatetime": f"{chunk_start:%Y%m%d}000000",
            "enddatetime": f"{chunk_end:%Y%m%d}235959",
        }
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        response = get_with_backoff(url, params=params)
        if response is None:
            frames.append(pd.DataFrame())
            continue
        data = response.json()
        rows = []
        for article in data.get("articles", []):
            title = normalize_text(article.get("title"))
            snippet = normalize_text(article.get("seendate"))
            combined = f"{title} {snippet}"
            rows.append({
                "title": title,
                "published_date": article.get("seendate"),
                "source": article.get("domain"),
                "url": article.get("url"),
                "region": region_name,
                "location_mentions": extract_location_mentions(combined, region_info),
                "snippet": snippet,
                "collection_source": "GDELT DOC 2.1 API",
                "access_date": datetime.now(timezone.utc).date().isoformat(),
            })
        frames.append(pd.DataFrame(rows))
        print(f"GDELT {region_name} {chunk_start} to {chunk_end}: {len(rows):,}")
        time.sleep(NEWS_SLEEP_SECONDS)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def fetch_google_news_rss(region_name: str, region_info: dict, start_date: str, end_date: str) -> pd.DataFrame:
    frames = []
    for chunk_start, chunk_end, _ in date_chunks(start_date, end_date, 31):
        query = (
            f'({region_query_terms(region_info)}) ({keyword_query_terms()}) '
            f"after:{chunk_start:%Y-%m-%d} before:{(chunk_end + timedelta(days=1)):%Y-%m-%d}"
        )
        url = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        )
        response = get_with_backoff(url, headers={"User-Agent": "Mozilla/5.0"})
        if response is None:
            frames.append(pd.DataFrame())
            continue
        soup = BeautifulSoup(response.text, "xml")
        rows = []
        for item in soup.find_all("item"):
            title = item.title.get_text(" ", strip=True) if item.title else ""
            pub_date = item.pubDate.get_text(" ", strip=True) if item.pubDate else ""
            link = item.link.get_text(" ", strip=True) if item.link else ""
            source_tag = item.find("source")
            source = source_tag.get_text(" ", strip=True) if source_tag else "Google News"
            rows.append({
                "title": title,
                "published_date": pub_date,
                "source": source,
                "url": link,
                "region": region_name,
                "location_mentions": extract_location_mentions(title, region_info),
                "snippet": "",
                "collection_source": "Google News RSS",
                "access_date": datetime.now(timezone.utc).date().isoformat(),
            })
        frames.append(pd.DataFrame(rows))
        print(f"Google RSS {region_name} {chunk_start} to {chunk_end}: {len(rows):,}")
        time.sleep(NEWS_SLEEP_SECONDS)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def fetch_bing_news_rss(region_name: str, region_info: dict, start_date: str, end_date: str) -> pd.DataFrame:
    frames = []
    for chunk_start, chunk_end, _ in date_chunks(start_date, end_date, 31):
        query = f"({region_query_terms(region_info)}) ({keyword_query_terms()})"
        url = f"https://www.bing.com/news/search?q={quote_plus(query)}&format=rss"
        response = get_with_backoff(url, headers={"User-Agent": "Mozilla/5.0"})
        if response is None:
            frames.append(pd.DataFrame())
            continue
        soup = BeautifulSoup(response.text, "xml")
        rows = []
        for item in soup.find_all("item"):
            title = item.title.get_text(" ", strip=True) if item.title else ""
            pub_date = item.pubDate.get_text(" ", strip=True) if item.pubDate else ""
            link = item.link.get_text(" ", strip=True) if item.link else ""
            source_tag = item.find("source")
            source = source_tag.get_text(" ", strip=True) if source_tag else "Bing News"
            rows.append({
                "title": title,
                "published_date": pub_date,
                "source": source,
                "url": link,
                "region": region_name,
                "location_mentions": extract_location_mentions(title, region_info),
                "snippet": "",
                "collection_source": "Bing News RSS",
                "access_date": datetime.now(timezone.utc).date().isoformat(),
            })
        frames.append(pd.DataFrame(rows))
        print(f"Bing RSS {region_name} {chunk_start} to {chunk_end}: {len(rows):,}")
        time.sleep(NEWS_SLEEP_SECONDS)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def collect_news_articles() -> pd.DataFrame:
    frames = []
    for region_name, region_info in REGIONS.items():
        frames.append(fetch_gdelt_articles(region_name, region_info, START_DATE, END_DATE))
        frames.append(fetch_google_news_rss(region_name, region_info, START_DATE, END_DATE))
        frames.append(fetch_bing_news_rss(region_name, region_info, START_DATE, END_DATE))

    df_news = pd.concat(frames, ignore_index=True)
    df_news["published_date"] = pd.to_datetime(df_news["published_date"], errors="coerce", utc=True)
    df_news["title"] = df_news["title"].fillna("").str.strip()
    df_news["source"] = df_news["source"].fillna("Unknown").str.strip()
    df_news["url"] = df_news["url"].fillna("").str.strip()
    df_news = df_news[df_news["title"].ne("")]
    df_news = df_news.drop_duplicates(subset=["url", "title", "published_date"])
    return df_news.reset_index(drop=True)

if table_exists("news_articles"):
    print(f"Skipping news collection; news_articles already has {table_count('news_articles'):,} rows.")
    df_news = read_table("news_articles")
else:
    df_news = collect_news_articles()
    display(df_news.head())
    display(df_news.info())
    print(df_news["collection_source"].value_counts())
    print(df_news["region"].value_counts())
    write_table(df_news, "news_articles")

# %% [markdown]
# ## 5. Task 2: Thermal Event Clustering
#
# Methodology: detections are clustered within each region using DBSCAN with a
# custom space-time metric. Two detections are neighbors if they are within
# 10 km and within 2 days. Each cluster becomes one thermal event.

# %%
def haversine_km(lat1, lon1, lat2, lon2) -> float:
    radius_km = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def cluster_region_events(
    region_df: pd.DataFrame,
    spatial_km: float = 10.0,
    temporal_days: float = 2.0,
) -> pd.DataFrame:
    df = region_df.copy().reset_index(drop=True)
    df["acq_datetime"] = pd.to_datetime(df["acq_datetime"], errors="coerce", utc=True)
    df = df.dropna(subset=["latitude", "longitude", "acq_datetime"])
    if df.empty:
        return df.assign(cluster=-1)

    df["date_num"] = df["acq_datetime"].astype("int64") / (1e9 * 86400)
    X = df[["latitude", "longitude", "date_num"]].to_numpy(dtype=float)

    def space_time_metric(a, b):
        space = haversine_km(a[0], a[1], b[0], b[1]) / spatial_km
        time_distance = abs(a[2] - b[2]) / temporal_days
        return max(space, time_distance)

    labels = DBSCAN(eps=1.0, min_samples=1, metric=space_time_metric).fit_predict(X)
    df["cluster"] = labels
    return df

def build_thermal_events(df_firms_clean: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    clustered_frames = []
    event_rows = []
    event_counter = 1

    for region_name, region_df in df_firms_clean.groupby("region"):
        clustered = cluster_region_events(region_df)
        clustered["event_id"] = clustered["cluster"].map(
            {label: f"E{event_counter + i:06d}" for i, label in enumerate(sorted(clustered["cluster"].unique()))}
        )
        event_counter += clustered["cluster"].nunique()
        clustered_frames.append(clustered)

        for event_id, event_df in clustered.groupby("event_id"):
            start_dt = event_df["acq_datetime"].min()
            end_dt = event_df["acq_datetime"].max()
            event_rows.append({
                "event_id": event_id,
                "region": region_name,
                "centroid_latitude": event_df["latitude"].mean(),
                "centroid_longitude": event_df["longitude"].mean(),
                "start_date": start_dt.date(),
                "end_date": end_dt.date(),
                "duration_days": max((end_dt.date() - start_dt.date()).days + 1, 1),
                "total_frp": event_df["frp"].sum(),
                "mean_frp": event_df["frp"].mean(),
                "max_brightness": event_df["brightness"].max(),
                "n_detections": len(event_df),
                "pct_night": event_df.get("daynight", pd.Series(index=event_df.index, dtype=str)).astype(str).str.upper().eq("N").mean(),
            })

    df_clustered = pd.concat(clustered_frames, ignore_index=True)
    df_events = pd.DataFrame(event_rows).sort_values(["region", "start_date"]).reset_index(drop=True)
    return df_clustered, df_events

df_firms_db = read_table("firms_detections")
if table_exists("thermal_events"):
    print(f"Skipping clustering; thermal_events already has {table_count('thermal_events'):,} rows.")
    df_events = read_table("thermal_events")
    df_clustered = df_firms_db
else:
    df_clustered, df_events = build_thermal_events(df_firms_db)
    display(df_events.head())
    display(df_events.describe(include="all"))
    print(df_events["region"].value_counts())
    write_table(df_events, "thermal_events")

# %% [markdown]
# ## 6. Task 2: Temporal and Spatial Visualizations

# %%
def plot_temporal_visualizations(events: pd.DataFrame, clustered: pd.DataFrame) -> None:
    events = events.copy()
    events["start_date"] = pd.to_datetime(events["start_date"])
    events["month"] = events["start_date"].dt.to_period("M").dt.to_timestamp()

    monthly_events = (
        events.groupby(["month", "region"], as_index=False)
        .agg(event_count=("event_id", "count"), mean_frp=("mean_frp", "mean"))
    )

    fig, ax = plt.subplots(figsize=(11, 5))
    sns.lineplot(data=monthly_events, x="month", y="event_count", hue="region", marker="o", ax=ax)
    ax.set_title("Monthly Thermal Event Frequency by Region")
    ax.set_xlabel("Month")
    ax.set_ylabel("Number of thermal events")
    ax.legend(title="Region", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "task2_monthly_event_frequency.png", dpi=300)
    plt.show()

    fig, ax = plt.subplots(figsize=(11, 5))
    sns.lineplot(data=monthly_events, x="month", y="mean_frp", hue="region", marker="o", ax=ax)
    ax.set_title("Mean Thermal Intensity by Region Over Time")
    ax.set_xlabel("Month")
    ax.set_ylabel("Mean FRP (MW)")
    ax.legend(title="Region", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "task2_mean_frp_trend.png", dpi=300)
    plt.show()

    daynight = (
        clustered.assign(daynight=clustered["daynight"].fillna("Unknown"))
        .groupby(["region", "daynight"], as_index=False)
        .size()
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=daynight, x="region", y="size", hue="daynight", ax=ax)
    ax.set_title("Day vs. Night FIRMS Detection Counts")
    ax.set_xlabel("Region")
    ax.set_ylabel("Number of detections")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "task2_daynight_detection_counts.png", dpi=300)
    plt.show()

def plot_spatial_visualizations(events: pd.DataFrame) -> None:
    events = events.copy()
    size = 20 + 180 * (events["total_frp"] / events["total_frp"].quantile(0.95)).clip(upper=1)

    fig, ax = plt.subplots(figsize=(12, 6))
    scatter = ax.scatter(
        events["centroid_longitude"],
        events["centroid_latitude"],
        s=size,
        c=events["duration_days"],
        cmap="viridis",
        alpha=0.72,
        edgecolor="black",
        linewidth=0.25,
    )
    ax.set_title("Thermal Events Across Selected Shipping and Energy Risk Regions")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Event duration (days)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "task2_spatial_events_duration.png", dpi=300)
    plt.show()

    top_hotspots = (
        events.sort_values("total_frp", ascending=False)
        .groupby("region")
        .head(5)
        .reset_index(drop=True)
    )
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.scatterplot(
        data=events,
        x="centroid_longitude",
        y="centroid_latitude",
        hue="region",
        size="total_frp",
        sizes=(20, 220),
        alpha=0.55,
        ax=ax,
    )
    for _, row in top_hotspots.iterrows():
        ax.text(row["centroid_longitude"], row["centroid_latitude"], row["event_id"], fontsize=7)
    ax.set_title("Top Thermal Hotspots Labeled by Event ID")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "task2_top_hotspots.png", dpi=300)
    plt.show()

plot_temporal_visualizations(df_events, df_clustered)
plot_spatial_visualizations(df_events)

# %% [markdown]
# ## 7. Task 3: Thermal-News Matching

# %%
def to_naive_datetime(series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", utc=True).dt.tz_convert(None)

def has_conflict_keyword(text_value: str) -> bool:
    text_value = normalize_text(text_value).lower()
    return any(re.search(r"\b" + re.escape(keyword.lower()) + r"\b", text_value) for keyword in CONFLICT_KEYWORDS)

def match_events_to_news(events: pd.DataFrame, news: pd.DataFrame, window_days: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    events = events.copy()
    news = news.copy()

    events["start_dt"] = to_naive_datetime(events["start_date"])
    events["end_dt"] = to_naive_datetime(events["end_date"])
    news["published_dt"] = to_naive_datetime(news["published_date"])
    news["article_text"] = (news["title"].fillna("") + " " + news["snippet"].fillna("")).str.strip()
    news["keyword_relevant"] = news["article_text"].map(has_conflict_keyword)
    news = news[news["keyword_relevant"] & news["published_dt"].notna()].copy()

    match_rows = []
    for _, event in events.iterrows():
        region_news = news[news["region"].eq(event["region"])].copy()
        in_window = region_news[
            (region_news["published_dt"] >= event["start_dt"])
            & (region_news["published_dt"] <= event["end_dt"] + pd.Timedelta(days=window_days))
        ].copy()

        for _, article in in_window.iterrows():
            lag_days = (article["published_dt"].date() - event["start_dt"].date()).days
            match_rows.append({
                "event_id": event["event_id"],
                "region": event["region"],
                "article_title": article["title"],
                "article_url": article["url"],
                "article_source": article["source"],
                "article_date": article["published_dt"],
                "lag_days": lag_days,
                "match_reason": f"same region, 0-{window_days} day window, conflict keyword",
            })

    df_matches = pd.DataFrame(match_rows)
    matched_event_ids = set(df_matches["event_id"]) if not df_matches.empty else set()
    events["conflict_associated"] = events["event_id"].isin(matched_event_ids).astype(int)
    return events.drop(columns=["start_dt", "end_dt"]), df_matches

df_events_db = read_table("thermal_events")
df_news_db = read_table("news_articles")

df_events_matched, df_event_matches = match_events_to_news(df_events_db, df_news_db, window_days=7)
display(df_event_matches.head())
display(df_events_matched.groupby("region")["conflict_associated"].mean().rename("conflict_association_rate"))

write_table(df_events_matched, "thermal_events")
write_table(df_event_matches, "event_matches")

# %% [markdown]
# ## 8. Task 3: Regional Reporting Comparison and Hypothesis Test

# %%
def regional_coverage_stats(events: pd.DataFrame, news: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    event_counts = events.groupby("region").agg(
        thermal_events=("event_id", "count"),
        conflict_association_rate=("conflict_associated", "mean"),
        mean_total_frp=("total_frp", "mean"),
    )
    article_counts = news.groupby("region").agg(
        total_articles=("url", "count"),
        unique_sources=("source", "nunique"),
    )
    if not matches.empty:
        delay_stats = matches.groupby("region").agg(
            mean_reporting_delay_days=("lag_days", "mean"),
            median_reporting_delay_days=("lag_days", "median"),
        )
    else:
        delay_stats = pd.DataFrame(index=event_counts.index)

    summary = event_counts.join(article_counts, how="left").join(delay_stats, how="left")
    summary["total_articles"] = summary["total_articles"].fillna(0).astype(int)
    summary["unique_sources"] = summary["unique_sources"].fillna(0).astype(int)
    summary["articles_per_thermal_event"] = summary["total_articles"] / summary["thermal_events"]
    return summary.reset_index()

coverage = regional_coverage_stats(df_events_matched, df_news_db, df_event_matches)
display(coverage)

conflict_frp = df_events_matched.loc[df_events_matched["conflict_associated"].eq(1), "total_frp"].dropna()
non_conflict_frp = df_events_matched.loc[df_events_matched["conflict_associated"].eq(0), "total_frp"].dropna()

if len(conflict_frp) >= 2 and len(non_conflict_frp) >= 2:
    test_stat, p_value = stats.ttest_ind(conflict_frp, non_conflict_frp, equal_var=False)
    print("Hypothesis test: Welch t-test comparing total FRP")
    print("H0: conflict-associated and non-conflict events have the same mean total FRP")
    print("H1: the mean total FRP differs between the two groups")
    print(f"t statistic = {test_stat:.3f}, p-value = {p_value:.4f}")
else:
    print("Not enough observations in both groups for Welch t-test.")

def plot_coverage_visualizations(news: pd.DataFrame, coverage_df: pd.DataFrame) -> None:
    source_counts = (
        news.groupby(["region", "source"], as_index=False)
        .size()
        .sort_values("size", ascending=False)
    )
    top_sources = source_counts.groupby("region").head(5)
    pivot_sources = top_sources.pivot_table(index="region", columns="source", values="size", fill_value=0)

    fig, ax = plt.subplots(figsize=(12, 6))
    pivot_sources.plot(kind="bar", stacked=True, ax=ax, colormap="tab20")
    ax.set_title("Conflict News Article Counts by Region and Source")
    ax.set_xlabel("Region")
    ax.set_ylabel("Number of articles")
    ax.tick_params(axis="x", rotation=25)
    ax.legend(title="Source", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "task3_articles_by_region_source.png", dpi=300)
    plt.show()

    keyword_rows = []
    for region_name, group in news.groupby("region"):
        text_blob = " ".join(group["title"].fillna("").astype(str)).lower()
        for keyword in CONFLICT_KEYWORDS:
            keyword_rows.append({
                "region": region_name,
                "keyword": keyword,
                "count": len(re.findall(r"\b" + re.escape(keyword) + r"\b", text_blob)),
            })
    keyword_df = pd.DataFrame(keyword_rows)
    keyword_pivot = keyword_df.pivot(index="region", columns="keyword", values="count").fillna(0)

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.heatmap(keyword_pivot, cmap="mako", annot=True, fmt=".0f", ax=ax)
    ax.set_title("Conflict Keyword Frequency by Region")
    ax.set_xlabel("Keyword")
    ax.set_ylabel("Region")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "task3_keyword_heatmap.png", dpi=300)
    plt.show()

plot_coverage_visualizations(df_news_db, coverage)

# %% [markdown]
# ## 9. Task 3: Machine Learning Classification

# %%
def make_one_hot_encoder():
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)

def train_conflict_classifiers(events: pd.DataFrame):
    model_df = events.copy()
    model_df["start_date"] = pd.to_datetime(model_df["start_date"])
    model_df["month"] = model_df["start_date"].dt.month
    model_df["season"] = ((model_df["month"] % 12) // 3 + 1).astype(str)

    feature_cols_numeric = [
        "total_frp", "duration_days", "max_brightness", "n_detections",
        "pct_night", "centroid_latitude", "centroid_longitude", "month",
    ]
    feature_cols_categorical = ["region", "season"]
    target_col = "conflict_associated"

    model_df = model_df.dropna(subset=feature_cols_numeric + feature_cols_categorical + [target_col])
    X = model_df[feature_cols_numeric + feature_cols_categorical]
    y = model_df[target_col].astype(int)

    if y.nunique() < 2:
        raise ValueError("ML classification requires both conflict-associated and non-conflict events.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), feature_cols_numeric),
            ("cat", make_one_hot_encoder(), feature_cols_categorical),
        ]
    )

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, class_weight="balanced"),
        "Decision Tree": DecisionTreeClassifier(max_depth=5, random_state=42, class_weight="balanced"),
        "Gaussian Naive Bayes": GaussianNB(),
        "SVM": SVC(kernel="rbf", class_weight="balanced", probability=True, random_state=42),
    }

    results = []
    fitted = {}
    for model_name, model in models.items():
        pipe = Pipeline([("preprocess", preprocessor), ("model", model)])
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)
        results.append({
            "model": model_name,
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1": f1_score(y_test, y_pred, zero_division=0),
        })
        fitted[model_name] = (pipe, y_test, y_pred)
        print("\n" + model_name)
        print(classification_report(y_test, y_pred, zero_division=0))

        cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
        fig, ax = plt.subplots(figsize=(4.6, 4))
        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Blues",
            xticklabels=["No conflict", "Conflict"],
            yticklabels=["No conflict", "Conflict"],
            ax=ax,
        )
        ax.set_title(f"Confusion Matrix: {model_name}")
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        fig.tight_layout()
        fig.savefig(FIG_DIR / f"task3_confusion_matrix_{model_name.lower().replace(' ', '_')}.png", dpi=300)
        plt.show()

    return pd.DataFrame(results).sort_values("f1", ascending=False), fitted, feature_cols_numeric, feature_cols_categorical

model_results, fitted_models, numeric_features, categorical_features = train_conflict_classifiers(df_events_matched)
display(model_results)

best_model_name = model_results.iloc[0]["model"]
best_pipe = fitted_models[best_model_name][0]
feature_names = best_pipe.named_steps["preprocess"].get_feature_names_out()
model = best_pipe.named_steps["model"]

if hasattr(model, "coef_"):
    importance = pd.DataFrame({
        "feature": feature_names,
        "importance": model.coef_[0],
    }).assign(abs_importance=lambda d: d["importance"].abs()).sort_values("abs_importance", ascending=False)
elif hasattr(model, "feature_importances_"):
    importance = pd.DataFrame({
        "feature": feature_names,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)
else:
    importance = pd.DataFrame({"feature": feature_names, "importance": np.nan})

display(importance.head(15))

# %% [markdown]
# ## 10. Task 4: Multi-Panel Dashboard

# %%
def create_dashboard(events: pd.DataFrame, news: pd.DataFrame, matches: pd.DataFrame, coverage_df: pd.DataFrame) -> None:
    events = events.copy()
    events["start_date"] = pd.to_datetime(events["start_date"])
    events["month"] = events["start_date"].dt.to_period("M").dt.to_timestamp()

    fig = plt.figure(figsize=(16, 10))
    gs = gridspec.GridSpec(2, 3, figure=fig, height_ratios=[1.15, 1.0], width_ratios=[1.2, 1.0, 1.0])

    ax_map = fig.add_subplot(gs[0, :2])
    colors = events["conflict_associated"].map({0: "#7f8c8d", 1: "#c0392b"})
    sizes = 25 + 220 * (events["total_frp"] / events["total_frp"].quantile(0.95)).clip(upper=1)
    ax_map.scatter(
        events["centroid_longitude"],
        events["centroid_latitude"],
        s=sizes,
        c=colors,
        alpha=0.72,
        edgecolor="black",
        linewidth=0.25,
    )
    ax_map.set_title("Thermal events by conflict association")
    ax_map.set_xlabel("Longitude")
    ax_map.set_ylabel("Latitude")
    ax_map.scatter([], [], c="#c0392b", label="Conflict-associated")
    ax_map.scatter([], [], c="#7f8c8d", label="No matched news")
    ax_map.legend(loc="lower left")

    ax_rate = fig.add_subplot(gs[0, 2])
    rate_data = coverage_df.sort_values("conflict_association_rate", ascending=False)
    sns.barplot(data=rate_data, x="conflict_association_rate", y="region", color="#2e86ab", ax=ax_rate)
    ax_rate.set_title("Conflict-association rate")
    ax_rate.set_xlabel("Matched thermal events (%)")
    ax_rate.set_ylabel("")
    ax_rate.xaxis.set_major_formatter(lambda x, pos: f"{x:.0%}")

    ax_trend = fig.add_subplot(gs[1, :2])
    monthly = events.groupby(["month", "region"], as_index=False).agg(
        event_count=("event_id", "count"),
        conflict_rate=("conflict_associated", "mean"),
    )
    sns.lineplot(data=monthly, x="month", y="event_count", hue="region", marker="o", ax=ax_trend)
    ax_trend.set_title("Monthly thermal event frequency")
    ax_trend.set_xlabel("Month")
    ax_trend.set_ylabel("Number of events")
    ax_trend.legend(title="Region", ncols=2)

    ax_blind = fig.add_subplot(gs[1, 2])
    blind = coverage_df.copy()
    blind["satellite_value_score"] = blind["thermal_events"] / (blind["total_articles"] + 1)
    blind = blind.sort_values("satellite_value_score", ascending=False)
    sns.barplot(data=blind, x="satellite_value_score", y="region", color="#6a994e", ax=ax_blind)
    ax_blind.set_title("Potential news blind spots")
    ax_blind.set_xlabel("Thermal events per article")
    ax_blind.set_ylabel("")

    fig.suptitle(
        "Satellite thermal anomalies reveal conflict-risk signals unevenly covered by news",
        fontsize=16,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(PROJECT_ROOT / "dashboard.png", dpi=300)
    plt.show()

create_dashboard(df_events_matched, df_news_db, df_event_matches, coverage)

# %% [markdown]
# ## 11. Required Written Discussion
#
# ### Key Findings
# Write one paragraph explaining the relationship you found between thermal
# anomalies and conflict news. Mention which regions had the strongest
# conflict-association rate, which had the largest FRP spikes, and any surprises.
#
# ### Shipping & Energy Implications
# Write one paragraph explaining which regions create the highest route, fuel,
# insurance, or energy-price risks. Add 2-3 actionable recommendations for a
# maritime shipping company, such as monitoring thresholds, route review, or
# fuel hedging triggers.
#
# ### Limitations & Future Work
# Write one paragraph discussing matching errors, natural/industrial fire
# confounding, news bias, limited time coverage, geocoding uncertainty, and what
# extra data would help, such as AIS vessel tracks, ACLED/GDELT event databases,
# port disruption data, oil prices, or verified strike datasets.
#
# ### Methodology Reflection
# Write one paragraph explaining the hardest part of the pipeline and what you
# would improve if you restarted, such as better geocoding, stronger spatial
# matching, longer time series, or a manually validated training set.

# %% [markdown]
# ## 12. Final Verification

# %%
print("Database tables:")
display(verify_tables())

for table in ["firms_detections", "news_articles", "thermal_events", "event_matches"]:
    count_df = pd.read_sql(f"SELECT COUNT(*) AS n FROM {table}", engine)
    print(f"{table}: {int(count_df.loc[0, 'n']):,} rows")

print(f"Dashboard saved to: {PROJECT_ROOT / 'dashboard.png'}")
print(f"Figures saved to: {FIG_DIR}")
