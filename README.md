# CE49X Final Project Code Scaffold

This folder contains the completed CE49X final project pipeline and final submission artifacts.

## Files

- `CE49X_Final_Project_FINAL.ipynb`: final notebook/report for submission.
- `CE49X_Final_Project_COMPLETE_OUTPUTS.ipynb`: best single notebook for presentation/submission; contains sections, output tables, figures, and discussion in one place.
- `FINAL_PROJECT_REPORT.md`: written report with actual computed project metrics.
- `PRESENTATION_SCRIPT.md`: 10-15 minute video presentation script.
- `dashboard.png`: required 300 DPI dashboard figure.
- `figures/`: supporting Task 2 and Task 3 visualizations.
- `final_data_snapshots/`: CSV snapshots of PostgreSQL tables and final summary outputs.
- `CE49X_Final_Project_Run_All.py`: full executable pipeline from collection to dashboard.
- `CE49X_Final_Project_Code.py`: notebook-style cells in the exact project order.
- `CE49X_Final_Project_Notebook.ipynb`: generated Jupyter notebook version of the same ordered code.
- `requirements.txt`: Python packages required by the assignment.
- `docker-compose.yml`: PostgreSQL database matching the PDF requirements.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d
export FIRMS_MAP_KEY="your_firms_map_key_here"
jupyter notebook
```

Then open `CE49X_Final_Project_Notebook.ipynb` in Jupyter. You can also use `CE49X_Final_Project_Code.py` if you prefer notebook-style `# %%` cells in VS Code.

## Completed Results

- FIRMS detections: `265,321`
- News articles: `3,724`
- Thermal events: `2,904`
- Event-news matches: `135,311`
- Best ML model by F1: `SVM`, F1 = `0.950`
- Dashboard: `dashboard.png`

## Cursor'da En Kolay Yol

Cursor notebook açılışında takılıyorsa notebook kullanmayın. Terminalden şunu çalıştırın:

```bash
cd /Users/yigitbeyzadeoglu/Documents/Codex/2026-06-01/files-mentioned-by-the-user-final/outputs
source .venv/bin/activate
docker compose up -d
python CE49X_Final_Project_Run_All.py
```

Script sizden NASA FIRMS MAP_KEY isteyecek. Key'i terminale yapıştırın; kod dosyasını elle düzenlemeniz gerekmez.

Seçili analiz ayarları:

- Tarih aralığı: `2024-01-01` - `2024-06-30`
- Bölgeler: Ukraine/Black Sea, Red Sea/Yemen, Persian Gulf/Hormuz, Eastern Mediterranean

## Required Manual Edits

Update these values near the top of the code before running:

- `FIRMS_MAP_KEY`
- `START_DATE`
- `END_DATE`
- `REGIONS`, if your instructor expects different regions

## Notes

The code uses:

- NASA FIRMS area CSV endpoint for thermal anomalies.
- GDELT DOC API and Google News RSS as two news sources.
- PostgreSQL tables required by the PDF:
  - `firms_detections`
  - `news_articles`
  - `thermal_events`
  - `event_matches`
- DBSCAN space-time clustering with a 10 km / 2 day neighborhood.
- Logistic Regression, Decision Tree, Gaussian Naive Bayes, and SVM classifiers.
- `matplotlib.gridspec.GridSpec` dashboard saved as `dashboard.png` at 300 DPI.
