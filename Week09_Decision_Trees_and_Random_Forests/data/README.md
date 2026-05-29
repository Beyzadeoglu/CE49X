# Week 9 Datasets

## Nepal Earthquake Building Damage (DrivenData "Richter's Predictor")

Post-2015 Gorkha earthquake survey of building damage in Nepal. Used as the
**headline dataset** for the Week 9 Decision Trees & Random Forests lecture.

### Source
- **Competition page:** https://www.drivendata.org/competitions/57/nepal-earthquake/
- **Data collectors:** National Society for Earthquake Technology — Nepal (NSET-Nepal)
  and Kathmandu Living Labs (KLL), with the Central Bureau of Statistics.
- **Hosted by:** DrivenData.

### Citation
> DrivenData (2018). "Richter's Predictor: Modeling Earthquake Damage."
> https://www.drivendata.org/competitions/57/nepal-earthquake/

### License & redistribution
The raw competition files are made available to registered DrivenData users
under the competition Terms & Conditions. **The raw files are NOT committed to
this repository** (see `.gitignore`); each instructor or student must download
their own copy.

### How to obtain the data (instructor, one-time setup)

1. Sign in (or sign up — free) at https://www.drivendata.org.
2. Visit the competition page and download:
   - `train_values.csv`  (~21 MB)
   - `train_labels.csv`  (~3 MB)
3. Place both files in `data/raw/` (this folder).
4. From the Week09 root directory, run:

   ```bash
   python scripts/prepare_nepal_data.py
   ```

   This produces `data/nepal_buildings_sample.csv` (~5 MB, 50,000 rows,
   stratified by `damage_grade`, `random_state=49`).

The lecture notebook reads `data/nepal_buildings_sample.csv` directly.

### Schema

The merged file has 39 columns: 38 features + 1 target.

| Column | Type | Description |
|---|---|---|
| `building_id` | int | Unique identifier (used only for joins; **drop before modeling**) |
| `geo_level_1_id` | int (cat) | Coarsest geographic region (~30 districts) |
| `geo_level_2_id` | int (cat) | Mid-level region (~1,400) |
| `geo_level_3_id` | int (cat) | Fine-grained ward (~12,500) |
| `count_floors_pre_eq` | int | Floors before the earthquake |
| `age` | int | Building age in years |
| `area_percentage` | int | Footprint area (normalized) |
| `height_percentage` | int | Building height (normalized) |
| `land_surface_condition` | str (cat) | n / o / t |
| `foundation_type` | str (cat) | h / i / r / u / w |
| `roof_type` | str (cat) | n / q / x |
| `ground_floor_type` | str (cat) | f / m / v / x / z |
| `other_floor_type` | str (cat) | j / q / s / x |
| `position` | str (cat) | j / o / s / t |
| `plan_configuration` | str (cat) | a / c / d / f / m / n / o / q / s / u |
| `has_superstructure_*` | int (binary) | 11 binary flags: adobe_mud, mud_mortar_stone, stone_flag, cement_mortar_stone, mud_mortar_brick, cement_mortar_brick, timber, bamboo, rc_non_engineered, rc_engineered, other |
| `legal_ownership_status` | str (cat) | a / r / v / w |
| `count_families` | int | Number of families housed |
| `has_secondary_use*` | int (binary) | 11 secondary-use flags |
| **`damage_grade`** | int | **Target.** 1 = low, 2 = medium, 3 = near-total destruction |

Class distribution (after subsampling): roughly 10% / 57% / 33% for grades 1 / 2 / 3.

---

## Concrete Compressive Strength (NOT included)

The Concrete dataset (Yeh 1998, UCI) was originally planned but is **not** used
in the Week 9 lecture. The regression aside in §6 uses synthetic data from
`sklearn.datasets.make_regression` instead, which keeps the lecture focused on
the Nepal narrative and avoids managing a second real dataset.

If you would like to add a Concrete-based exercise later, the dataset is
available at https://archive.ics.uci.edu/dataset/165 (CC-BY 4.0).
