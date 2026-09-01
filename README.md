# Smart Grievance AI — SIH Hackathon MVP

AI-Based Citizen Grievance Classification, Prioritization & Duplicate Detection.

A single-file, self-contained Streamlit app. No paid API key is required to run
it — it works fully offline-tolerant with local fallbacks, and will
transparently upgrade its translation quality if you add a free/optional
Gemini API key.

## What's inside

- **Citizen Portal** — multilingual complaint submission (English/Hindi/etc.),
  preset city locations, manual lat/long, or click-to-pick on a map, plus a
  mock photo upload.
- **AI Classification & Priority Engine** — rule-based keyword classification
  with a semantic (sentence-embedding) fallback for department routing, and an
  explainable 1–100 severity/priority score built from severity keywords +
  VADER sentiment + repeat-report frequency. Every decision includes a
  plain-English XAI rationale.
- **Semantic Duplicate Detection** — `sentence-transformers` (`all-MiniLM-L6-v2`)
  embeddings + cosine similarity (>0.80) combined with a 500 m geospatial
  proximity check. Duplicates are merged into the parent ticket, boost its
  priority, and the citizen is notified.
- **Root-Cause Clustering** — a looser similarity/proximity threshold groups
  related micro-issues (e.g. several nearby potholes) into named clusters.
- **GIS Hotspot Map** — Folium map with priority-colored markers + a
  complaint-density heatmap layer, filterable by department/priority.
- **Admin Dashboard** — analytics cards, filterable/searchable ticket table,
  status management (Pending/In Progress/Resolved), and a per-ticket inspector
  showing full XAI rationale and linked duplicate reports.
- **Pre-seeded mock data** — 11 realistic grievances across Pune wards,
  including 2 intentional duplicate pairs, so the demo is immediately
  populated and visually dynamic.

## Installation

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

> First run will download the `all-MiniLM-L6-v2` sentence-embedding model
> (~90 MB) from Hugging Face, so make sure you have internet access the
> first time you launch the app. It's cached locally after that.

## Running the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`. A local SQLite database
(`grievance_db.sqlite3`) is created automatically on first launch and
pre-populated with the demo dataset.

To reset the demo data, just delete `grievance_db.sqlite3` and restart the app.

## Optional: Gemini-powered translation

By default, non-English text is translated using a free local fallback
(`deep-translator`, no key required). If you want higher-quality translation,
open the **⚙️ AI Engine Settings** panel in the sidebar and paste a Gemini API
key — the app will automatically prefer it, and gracefully falls back if the
call fails for any reason. To enable this path, also install:

```bash
pip install google-generativeai
```

## Architecture notes

- **No external services required to run** — embeddings, sentiment, and
  classification all run locally; translation degrades gracefully offline.
- **Explainability by design** — `classify_department()` and
  `score_priority()` both return a human-readable rationale string alongside
  their decision, surfaced in both the citizen confirmation and the admin
  ticket inspector.
- **Duplicate vs. cluster distinction** — duplicate detection (submission-time,
  strict thresholds: similarity > 0.80, distance ≤ 500 m) is separate from
  root-cause clustering (dashboard-time, looser thresholds: similarity ≥ 0.55,
  distance ≤ 1 km) so five separate potholes can cluster into one
  "road resurfacing" story without being wrongly merged as literal duplicates.
- **Swap in a real geocoded map picker** — the "Pick on map" mode in the
  Citizen Portal already supports click-to-select lat/long via `streamlit-folium`.

## Customizing for your city / problem statement

- Edit `CITY_NAME`, `CITY_CENTER`, `WARDS`, and `PRESET_LOCATIONS` in `app.py`
  to point at your own city.
- Extend `DEPARTMENTS` and `SEVERITY_KEYWORDS` to add more departments or
  tune scoring for your judges' rubric.
- Tune `DUPLICATE_SIM_THRESHOLD` / `DUPLICATE_DIST_KM` and
  `CLUSTER_SIM_THRESHOLD` / `CLUSTER_DIST_KM` to adjust sensitivity.
