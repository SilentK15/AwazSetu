# AwazSetu (आवाज़ सेतु) 🏛️
### Smart Citizen Grievance Redressal & Duplicate Detection System (SIH 2026)

Hey there! This is **AwazSetu**, a platform we built to fix how municipal complaints are handled. 

Most civic complaint portals have two massive issues:
1. **Wrong Department Routing:** A citizen complains about a crater or accident risk on a broken road, but it ends up in Electricity or Water Supply because of a broken dropdown or generic keywords.
2. **Duplicate Overload:** When a water main bursts or a massive pothole opens up at a busy junction, dozens of citizens report the exact same thing. Municipal officers get buried under 50 separate tickets for one incident instead of fixing the actual problem.

AwazSetu solves this by using real-time AI classification, smart geospatial duplicate detection, and dedicated departmental admin portals so officers can get straight to work with exact Google Maps coordinates.

---

## What the system actually does

### 1. Citizen Portal
- **Zero Confusion Form:** Citizens can just describe what's wrong in plain English, Hindi, or Marathi. They don't need to guess which government department handles what — our AI auto-routes it.
- **Smart Location Search:** Type any society, landmark, or street name (e.g., *Lodha Amara*, *Vardhaman Vatika*). It autocompletes using live geocoding and drops an interactive Leaflet pin.
- **Photo Evidence:** Upload on-site photos. The backend runs computer vision edge/texture analysis to assess structural damage and boost the urgency score.
- **Strict Privacy & Ticket Tracking:** Citizens log in with their mobile number and only see their own filed complaints and real-time status.

### 2. Department-Specific Admin Dashboards
- **Department Portals:** Officers don't get distracted by other departments' issues. A Roads engineer only sees Roads & Potholes tickets, Water engineers see pipeline issues, etc. (with a Central Admin view for the Municipal Commissioner).
- **Exact Google Maps Links:** Every ticket shows the exact GPS coordinates and place name with a 1-click **"Open in Google Maps"** button so field teams can navigate right to the spot.
- **Live GIS Heatmap:** See priority-coded incident pins across the city.
- **Status Lifecycle:** Mark complaints as *Pending*, *In Progress*, or *Resolved*.

### 3. AI Redressal Engine (Under the Hood)
- **Road Safety & Accident Safeguard:** High-risk road hazards and accident risks are guarded against false routing.
- **Semantic + Lexical Routing:** Combines keyword signals with `all-MiniLM-L6-v2` sentence embeddings when complaints are short or ambiguous.
- **Multi-Tiered Duplicate Clustering:**
  - If a complaint is filed within **400m** of an active issue in the same department with matching semantics, it merges automatically.
  - Adaptive thresholds check up to **1.5 km** for broader locality clustering.
  - When merged, the original parent ticket gets upvoted (+8 priority points), boosting urgent community issues to the top of the queue.
  - Chained duplicates automatically resolve to the single root master ticket.
- **Explainable AI (XAI):** Every single ticket includes a plain-English explanation of why the department was picked, which keywords triggered it, and how the 1–100 urgency score was calculated.

---

## Tech Stack

- **Frontend:** Vanilla HTML5, CSS3, JavaScript (no bloated heavy frameworks, instant load times, clean gov-tech aesthetic).
- **Interactive Maps:** Leaflet.js with CartoDB clean tiles + OpenStreetMap Nominatim geocoding.
- **Backend:** Python (`server.py` with multi-threaded HTTP server and REST endpoints).
- **Database:** SQLite (`grievance_db.sqlite3` for complaints, `civic_users.db` for auth).
- **AI & NLP:**
  - `sentence-transformers` (`all-MiniLM-L6-v2`) for local 384-dimensional semantic embeddings.
  - `vaderSentiment` for citizen distress analysis.
  - `scikit-learn` for cosine similarity matrices.
  - `Pillow` for photo texture variance and damage edge detection.
  - `deep-translator` for multilingual input handling.

---

## How to run it locally

### 1. Clone & Set up Virtual Environment
```bash
# Clone repository
git clone https://github.com/SilentK15/AwazSetu.git
cd AwazSetu

# Create & activate venv
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux / Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

*(Note: On first run, it will download the lightweight `all-MiniLM-L6-v2` model (~90 MB) once. After that, it runs completely offline without any paid API keys).*

### 2. Start the Server
```bash
python server.py
```

The portal will start on: **`http://127.0.0.1:8080/`**

---

## Demo Credentials for Testing

### Department Officer Accounts (Password: `admin123`)
| Department | Username | Password | Access Scope |
|---|---|---|---|
| **Roads & Infrastructure** | `roads_admin` | `admin123` | Roads, potholes, and highway operations |
| **Water Supply** | `water_admin` | `admin123` | Pipeline leaks and contamination queue |
| **Electricity/Power** | `power_admin` | `admin123` | Streetlights and wiring hazards |
| **Waste Management** | `waste_admin` | `admin123` | Garbage dumping and sanitation |
| **Public Health** | `health_admin` | `admin123` | Open sewage and biohazard reports |
| **Central Administration** | `admin` | `admin123` | Municipal Commissioner master view |

### Citizen Portal
- Click the **Citizen** tab on the login screen.
- Log in with any registered 10-digit mobile number (e.g. `6359012124` / `9820011223`, password `admin123`) or click **Create Account** to register a new verified citizen account.

---

## Core Civic Innovations
- **Whole-Site Multilingual UI**: 1-click global language switcher supporting English, Hindi (हिन्दी), and Marathi (मराठी) across all screens, navigation, and live data.
- **Continuous Voice Dictation**: Speech-to-text with conversational pause recovery and Devanagari speech support.
- **Single-Vote Community Upvoting**: Citizens can upvote existing complaints (+1 Affects Me Too) with strict duplicate vote prevention.
- **Mandatory Photo Resolution Proof**: Officers must upload on-site "After" photographic evidence and notes to submit work.
- **Citizen Verification & Auto-Deletion**: Once work is submitted, status becomes `Waiting for Citizen Confirmation`. When the citizen confirms the fix, the ticket is permanently closed and deleted from active complaints. If unsatisfied, the citizen reopens the ticket with elevated urgency.

---

## Project Structure

```
├── backend.py            # AI classification, priority scoring, duplicate detection engine
├── server.py             # Python HTTP server & REST API endpoints
├── grievance_db.sqlite3  # SQLite database storing grievances, embeddings, and photos
├── civic_users.db        # SQLite database for citizen and admin auth
├── public/               # Frontend assets
│   ├── index.html        # Clean single-page application structure
│   ├── styles.css        # Gov-tech design system & responsive styling
│   └── app.js            # Leaflet map logic, location autocomplete, and dashboard state
└── requirements.txt      # Python dependencies
```

---

Built with ❤️ for the Smart India Hackathon. Feel free to open issues or contribute!
