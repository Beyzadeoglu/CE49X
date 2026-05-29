"""
Prepare a 50,000-row stratified subsample of the DrivenData "Richter's Predictor"
Nepal earthquake building damage dataset for use in CE49X Week 9 lecture.

Usage
-----
    1. Download the competition data from
         https://www.drivendata.org/competitions/57/nepal-earthquake/data/
       (free DrivenData account required). You need:
         - train_values.csv   (~21 MB)
         - train_labels.csv   (~3 MB)
       Place both files in:  Week09_.../data/raw/

    2. From the Week09 folder, run:
         python scripts/prepare_nepal_data.py

    3. The script writes  data/nepal_buildings_sample.csv  (~5 MB).
       The lecture notebook reads this file directly.

Reproducibility
---------------
    Stratified by damage_grade with random_state=49.  Re-running on the same
    raw inputs produces a byte-identical output.

Source / citation
-----------------
    Data collected post-2015 Gorkha earthquake by NSET-Nepal and Kathmandu
    Living Labs, hosted on DrivenData. See data/README.md for full citation.
"""

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

# Paths are resolved relative to this script's parent (the Week09 folder)
HERE = Path(__file__).resolve().parent
WEEK09_DIR = HERE.parent
RAW_DIR = WEEK09_DIR / "data" / "raw"
OUT_PATH = WEEK09_DIR / "data" / "nepal_buildings_sample.csv"

N_SAMPLE = 50_000
RANDOM_STATE = 49


def main() -> None:
    values_path = RAW_DIR / "train_values.csv"
    labels_path = RAW_DIR / "train_labels.csv"

    if not values_path.exists() or not labels_path.exists():
        raise FileNotFoundError(
            f"Could not find raw files in {RAW_DIR}.\n"
            "Download train_values.csv and train_labels.csv from "
            "https://www.drivendata.org/competitions/57/nepal-earthquake/data/ "
            "and place them in data/raw/."
        )

    print(f"Loading {values_path.name} ...")
    values = pd.read_csv(values_path)
    print(f"Loading {labels_path.name} ...")
    labels = pd.read_csv(labels_path)

    df = values.merge(labels, on="building_id", how="inner")
    print(f"Merged: {df.shape[0]:,} rows, {df.shape[1]} columns")

    if len(df) <= N_SAMPLE:
        sample = df.copy()
    else:
        # Stratified subsample preserves the class distribution.
        sample, _ = train_test_split(
            df,
            train_size=N_SAMPLE,
            stratify=df["damage_grade"],
            random_state=RANDOM_STATE,
        )

    # Sort by building_id for byte-stable output across runs
    sample = sample.sort_values("building_id").reset_index(drop=True)

    print(f"Subsampled: {len(sample):,} rows")
    print("Class distribution:")
    print(sample["damage_grade"].value_counts(normalize=True).sort_index().round(3))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(OUT_PATH, index=False)
    print(f"\nWrote {OUT_PATH.relative_to(WEEK09_DIR)}  ({OUT_PATH.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
