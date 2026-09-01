"""
CivicNexus Backend Core — AI-Based Citizen Grievance Classification, Prioritization,
and Duplicate Complaint Detection (SIH 2026 Problem Statement SIH26-S02)

Preserved Core Modules:
- SQLite persistence layer (grievance_db.sqlite3)
- SentenceTransformers embedding pipeline (all-MiniLM-L6-v2)
- Lexical keyword + semantic prototype cosine similarity department classification
- Dynamic urgency scoring with VADER distress sentiment + hazard weighting
- Haversine geospatial proximity (<400m) semantic duplicate detection
- Disjoint-Set Union (DSU) 1 km root-cause macro clustering
"""

import os
import json
import math
import uuid
import sqlite3
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Optional / best-effort imports
try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0
    LANGDETECT_AVAILABLE = True
except Exception:
    LANGDETECT_AVAILABLE = False

try:
    from deep_translator import GoogleTranslator
    DEEP_TRANSLATOR_AVAILABLE = True
except Exception:
    DEEP_TRANSLATOR_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except Exception:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grievance_db.sqlite3")
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

CITY_NAME = "Mumbai Metropolitan Region"
CITY_CENTER = (19.0760, 72.8777)

WARDS = {
    "Dadar Central":    (19.0178, 72.8478),
    "Andheri West":     (19.1197, 72.8464),
    "Bandra Promenade": (19.0544, 72.8371),
    "Kurla Junction":   (19.0726, 72.8793),
    "Borivali North":   (19.2307, 72.8567),
    "Colaba Point":     (18.9067, 72.8147),
}

PRESET_LOCATIONS = {
    "Dadar TT Circle":      (19.0178, 72.8478),
    "Andheri Station (W)":   (19.1197, 72.8464),
    "Bandra Bandstand":      (19.0450, 72.8200),
    "Kurla LBS Road":        (19.0726, 72.8793),
    "Borivali Station (W)":  (19.2307, 72.8567),
    "Colaba Causeway":       (18.9067, 72.8147),
}

STATUS_OPTIONS = ["Pending", "In Progress", "Resolved"]
PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
PRIORITY_COLORS = {"Critical": "#dc2626", "High": "#ea580c", "Medium": "#ca8a04", "Low": "#16a34a"}

DUPLICATE_SIM_THRESHOLD = 0.80
DUPLICATE_DIST_KM = 0.40         # 400 metres geospatial threshold
CLUSTER_SIM_THRESHOLD = 0.55
CLUSTER_DIST_KM = 1.0            # 1 km for broader root-cause clustering


DEPARTMENTS = {
    "Water Supply": {
        "keywords": [
            "water", "pipe", "pipeline", "leak", "leaking", "tap", "supply",
            "drinking water", "tanker", "borewell", "contaminated water",
            "no water", "low pressure", "burst pipe", "water shortage",
            "पानी", "पाणी", "नळ", "गळती",
        ],
        "proto": "Issues related to drinking water supply, pipeline leaks, "
                 "water tankers, contamination and low water pressure.",
    },
    "Roads & Infrastructure": {
        "keywords": [
            "road", "pothole", "potholes", "street", "footpath", "bridge",
            "construction", "pavement", "divider", "flyover", "encroachment",
            "broken road", "damaged road", "road accident", "manhole",
            "सड़क", "खड्डा", "रस्ता", "खड्डे", "पूल",
        ],
        "proto": "Issues related to roads, potholes, footpaths, bridges, "
                 "and damaged public infrastructure.",
    },
    "Electricity/Power": {
        "keywords": [
            "electricity", "power", "transformer", "wire", "spark",
            "sparking", "outage", "voltage", "streetlight", "street light",
            "power cut", "short circuit", "electric pole", "power outage",
            "live wire", "बिजली", "विद्युत", "वायर", "लाईट",
        ],
        "proto": "Issues related to electricity supply, power cuts, "
                 "transformers, sparking or live wires and streetlights.",
    },
    "Waste Management": {
        "keywords": [
            "garbage", "trash", "waste", "dump", "dumping", "litter",
            "overflowing", "dustbin", "sanitation", "sweeping", "landfill",
            "कचरा", "घाण", "डस्टबिन", "स्वच्छता",
        ],
        "proto": "Issues related to garbage collection, waste dumping, "
                 "overflowing dustbins and street sanitation.",
    },
    "Public Health": {
        "keywords": [
            "sewage", "mosquito", "disease", "outbreak", "stray dog",
            "stray dogs", "dead animal", "hospital", "health hazard",
            "open drain", "foul smell", "epidemic", "contamination",
            "गटर", "सांडपाणी", "डास", "दुर्गंधी", "मच्छर",
        ],
        "proto": "Issues related to public health hazards, sewage overflow, "
                 "mosquito breeding, stray animals and disease outbreaks.",
    },
}

SEVERITY_KEYWORDS = {
    "sparking wire": 95, "live wire": 95, "electrocution": 98,
    "gas leak": 98, "fire": 96, "explosion": 99, "transformer blast": 92,
    "short circuit": 88, "flooding": 85, "flooded": 85,
    "sewage overflow": 80, "open manhole": 75, "manhole open": 75,
    "collapsed": 85, "road accident": 88, "accident": 78,
    "no water supply": 68, "water shortage": 55, "burst pipe": 70,
    "broken pipe": 62, "contaminated water": 78,
    "large pothole": 55, "pothole": 38, "potholes": 40,
    "power outage": 50, "power cut": 45,
    "overflowing garbage": 52, "garbage overflow": 52,
    "dead animal": 60, "stray dogs": 45, "mosquito breeding": 55,
    "foul smell": 40, "health hazard": 58,
    "streetlight not working": 28, "no streetlight": 30,
    "school": 15, "children": 15, "hospital": 18,
    "आग": 95, "अपघात": 85, "खड्डा": 40, "पाणी नाही": 65, "गटर तुंबले": 75,
}


_model_instance = None
def load_embedding_model():
    global _model_instance
    if _model_instance is None and SENTENCE_TRANSFORMERS_AVAILABLE:
        try:
            _model_instance = SentenceTransformer(EMBEDDING_MODEL_NAME)
        except Exception:
            _model_instance = None
    return _model_instance

_sia_instance = SentimentIntensityAnalyzer()


def new_id():
    return uuid.uuid4().hex[:8].upper()


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def nearest_ward(lat, lon):
    best_ward, best_dist = None, float("inf")
    for name, (wlat, wlon) in WARDS.items():
        d = haversine_km(lat, lon, wlat, wlon)
        if d < best_dist:
            best_dist, best_ward = d, name
    return best_ward or "Dadar Central"


def embed_text(text: str):
    model = load_embedding_model()
    if model is not None:
        vec = model.encode([text])[0]
        return np.asarray(vec, dtype=float)
    dim = 384
    vec = np.zeros(dim)
    for tok in text.lower().split():
        idx = hash(tok) % dim
        vec[idx] += 1.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def embed_batch(texts):
    model = load_embedding_model()
    if model is not None:
        return np.asarray(model.encode(list(texts)), dtype=float)
    return np.asarray([embed_text(t) for t in texts])


def detect_language(text: str) -> str:
    if not LANGDETECT_AVAILABLE:
        return "unknown"
    try:
        return detect(text)
    except Exception:
        return "unknown"


def normalize_to_english(text: str, gemini_api_key: str = ""):
    lang = detect_language(text)
    if lang == "en" or lang == "unknown":
        return text, lang, "No translation needed / English confirmed."

    if gemini_api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_api_key)
            gmodel = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"Translate the following citizen grievance to English. Return ONLY the translation:\n\n{text}"
            resp = gmodel.generate_content(prompt)
            translated = resp.text.strip()
            return translated, lang, "Translated via Gemini Generative AI API."
        except Exception:
            pass

    if DEEP_TRANSLATOR_AVAILABLE:
        try:
            translated = GoogleTranslator(source="auto", target="en").translate(text)
            if translated:
                return translated, lang, "Translated via Google Translator Engine."
        except Exception:
            pass

    return text, lang, "Local passthrough (offline mode)."


def classify_department(text_en: str):
    text_l = text_en.lower()
    hits_per_dept = {}
    for dept, info in DEPARTMENTS.items():
        hits = [kw for kw in info["keywords"] if kw in text_l]
        hits_per_dept[dept] = hits

    best_dept = max(hits_per_dept, key=lambda d: len(hits_per_dept[d]))
    n_hits = len(hits_per_dept[best_dept])

    if n_hits > 0:
        confidence = min(1.0, 0.45 + 0.18 * n_hits)
        method = "Lexical Keyword Matching"
        matched = hits_per_dept[best_dept]
    else:
        dept_names = list(DEPARTMENTS.keys())
        protos = [DEPARTMENTS[d]["proto"] for d in dept_names]
        all_emb = embed_batch([text_en] + protos)
        complaint_emb = all_emb[0].reshape(1, -1)
        proto_emb = all_emb[1:]
        sims = cosine_similarity(complaint_emb, proto_emb)[0]
        best_idx = int(np.argmax(sims))
        best_dept = dept_names[best_idx]
        confidence = float(sims[best_idx])
        method = "Semantic Embedding Similarity (Prototype Proximity)"
        matched = []

    rationale_lines = [
        f"Assigned Department: {best_dept}",
        f"• Inference Mechanism: {method}",
        f"• Model Confidence: {confidence * 100:.1f}%",
    ]
    if matched:
        rationale_lines.append(f"• Trigger Keywords Detected: {', '.join(sorted(set(matched)))}")
    else:
        rationale_lines.append("• Semantic Match: Nearest cosine distance to departmental operational scope.")

    return best_dept, "\n".join(rationale_lines), confidence


def score_to_priority(score: int) -> str:
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


def score_priority(text_en: str, sentiment_compound: float, upvotes: int = 0):
    text_l = text_en.lower()
    matched = [(kw, w) for kw, w in SEVERITY_KEYWORDS.items() if kw in text_l]
    matched.sort(key=lambda x: -x[1])

    if matched:
        top_kw, top_w = matched[0]
        extra = sum(w * 0.10 for _, w in matched[1:])
        severity_component = min(100, top_w + extra)
    else:
        top_kw, top_w = None, 0
        severity_component = 18

    sentiment_component = min(12.0, abs(sentiment_compound) * 12) if sentiment_compound < 0 else 0.0
    repeat_component = min(15.0, upvotes * 3)

    raw = severity_component * 0.80 + sentiment_component + repeat_component
    final_score = int(max(1, min(100, round(raw))))
    priority = score_to_priority(final_score)

    lines = [
        f"Dynamic Priority: {priority} | Urgency Score: {final_score}/100",
        f"• Keyword Hazard Weight: {severity_component:.1f} pts" + (f" (Top keyword: '{top_kw}')" if top_kw else ""),
        f"• Distress Sentiment (VADER Compound = {sentiment_compound:.2f}): +{sentiment_component:.1f} pts",
        f"• Community Multiplier ({upvotes} linked reports): +{repeat_component:.1f} pts",
        f"• Formulation: (0.80 × {severity_component:.1f}) + {sentiment_component:.1f} + {repeat_component:.1f} = {final_score}/100",
    ]
    return final_score, priority, "\n".join(lines)


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS grievances (
            id TEXT PRIMARY KEY,
            original_text TEXT,
            text_en TEXT,
            detected_lang TEXT,
            category_hint TEXT,
            department TEXT,
            priority TEXT,
            severity_score INTEGER,
            sentiment_compound REAL,
            lat REAL,
            lon REAL,
            ward TEXT,
            status TEXT,
            upvotes INTEGER,
            is_duplicate INTEGER,
            parent_id TEXT,
            embedding TEXT,
            xai_department TEXT,
            xai_priority TEXT,
            image_flag INTEGER,
            citizen_name TEXT,
            citizen_phone TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def fetch_all_records():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM grievances ORDER BY datetime(created_at) DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_record(record: dict):
    conn = get_conn()
    cols = ", ".join(record.keys())
    placeholders = ", ".join(["?"] * len(record))
    conn.execute(f"INSERT INTO grievances ({cols}) VALUES ({placeholders})", tuple(record.values()))
    conn.commit()
    conn.close()


def update_status_in_db(gid: str, status: str):
    conn = get_conn()
    conn.execute("UPDATE grievances SET status = ? WHERE id = ?", (status, gid))
    conn.commit()
    conn.close()


def increment_upvote_in_db(gid: str, boost_points: int = 0):
    conn = get_conn()
    row = conn.execute("SELECT upvotes, severity_score FROM grievances WHERE id = ?", (gid,)).fetchone()
    if row:
        new_upvotes = row["upvotes"] + 1
        new_score = min(100, row["severity_score"] + boost_points)
        new_priority = score_to_priority(new_score)
        conn.execute(
            "UPDATE grievances SET upvotes = ?, severity_score = ?, priority = ? WHERE id = ?",
            (new_upvotes, new_score, new_priority, gid),
        )
        conn.commit()
    conn.close()


def find_duplicate_match(new_embedding, new_lat, new_lon, records):
    if not records:
        return None, 0.0

    parents = [r for r in records if r["is_duplicate"] == 0]
    best_id, best_sim = None, 0.0

    for r in parents:
        try:
            emb = np.array(json.loads(r["embedding"]))
        except Exception:
            continue
        sim = float(cosine_similarity(new_embedding.reshape(1, -1), emb.reshape(1, -1))[0][0])
        dist = haversine_km(new_lat, new_lon, r["lat"], r["lon"])
        if sim >= DUPLICATE_SIM_THRESHOLD and dist <= DUPLICATE_DIST_KM and sim > best_sim:
            best_sim, best_id = sim, r["id"]

    return best_id, best_sim


def get_macro_clusters(records):
    if not records or len(records) < 2:
        return []

    ids = [r["id"] for r in records]
    embeddings = [np.array(json.loads(r["embedding"])) for r in records]
    lats = [r["lat"] for r in records]
    lons = [r["lon"] for r in records]
    depts = [r["department"] for r in records]

    n = len(ids)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    sims = cosine_similarity(np.vstack(embeddings))
    for i in range(n):
        for j in range(i + 1, n):
            dist = haversine_km(lats[i], lons[i], lats[j], lons[j])
            if sims[i][j] >= CLUSTER_SIM_THRESHOLD and dist <= CLUSTER_DIST_KM:
                union(i, j)

    groups = {}
    for i in range(n):
        r = find(i)
        groups.setdefault(r, []).append(i)

    summary = []
    c_num = 1
    for r, members in groups.items():
        if len(members) < 2:
            continue
        m_depts = [depts[m] for m in members]
        top_dept = max(set(m_depts), key=m_depts.count)
        m_wards = [nearest_ward(lats[m], lons[m]) for m in members]
        top_ward = max(set(m_wards), key=m_wards.count)
        summary.append({
            "cluster_id": f"CLUST-{c_num:02d}",
            "department": top_dept,
            "ward": top_ward,
            "count": len(members),
            "ticket_ids": [ids[m] for m in members],
        })
        c_num += 1

    return summary
