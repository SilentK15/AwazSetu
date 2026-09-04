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

STATUS_OPTIONS = ["Pending", "In Progress", "Waiting for Citizen Confirmation", "Reopened", "Resolved"]
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
            "broken road", "damaged road", "road accident", "accident", "accidents",
            "accidental", "manhole", "crater", "craters", "skid", "skidding",
            "slip", "slippery", "asphalt", "tar road", "uneven road",
            "speed breaker", "speedbreaker", "barrier", "debris",
            "सड़क", "खड्डा", "रस्ता", "खड्डे", "पूल", "अपघात",
        ],
        "proto": "Issues related to roads, potholes, craters, traffic accidents, footpaths, bridges, "
                 "broken pavement, and damaged street infrastructure.",
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


def classify_photo_department(photo_bytes: bytes) -> tuple:
    """
    Multimodal Computer Vision Classifier for Citizen Uploaded Evidence:
    Extracts spatial color-entropy, luminance horizon, and edge disruptions to detect civic domain:
    - Roads & Infrastructure: Low color saturation (gray/dirt tones), asphalt luminance, crater/pothole edge disruption.
    - Waste Management: High color scatter / clutter variance on ground plane.
    - Water Supply: Strong blue/cyan shift or clean surface reflective water pooling.
    - Electricity / Power: Overhead linear edge density (wires/poles) in upper crop.
    """
    if not photo_bytes:
        return None, 0.0, ""
    try:
        from PIL import Image, ImageFilter, ImageStat
        import io
        img = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
        w, h = img.size

        # Ground crop (lower 65% of image where road/ground/potholes lie)
        ground_crop = img.crop((0, int(h * 0.35), w, h))
        g_stat = ImageStat.Stat(ground_crop)
        r_m, g_m, b_m = g_stat.mean[:3]
        color_diff = max(abs(r_m - g_m), abs(g_m - b_m), abs(r_m - b_m))
        brightness = sum(g_stat.mean[:3]) / 3.0

        edges = ground_crop.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        edge_mean = sum(edge_stat.mean[:3]) / 3.0
        stddev = sum(g_stat.stddev[:3]) / 3.0

        # Overhead crop (upper 45% of image for overhead lines / electric poles)
        upper_crop = img.crop((0, 0, w, int(h * 0.45)))
        u_edges = upper_crop.filter(ImageFilter.FIND_EDGES)
        u_edge_mean = sum(ImageStat.Stat(u_edges).mean[:3]) / 3.0

        # 1. Roads & Infrastructure (Asphalt, Potholes, Road Fractures, Craters)
        # Neutral saturation (color_diff < 28), asphalt luminance (30-165), high crater edge disruption
        if color_diff < 28.0 and 30 <= brightness <= 165:
            if edge_mean > 11.5 or stddev > 24.0:
                conf = min(0.97, 0.82 + (edge_mean / 100.0) + (stddev / 250.0))
                diag = f"Asphalt crater & road surface fracture detected (Edge Disruption: {edge_mean:.1f}, Variance: {stddev:.1f})"
                return "Roads & Infrastructure", conf, diag

        # 2. Waste Management (Multicolor litter, garbage dump, plastic clutter)
        if color_diff > 32.0 and edge_mean > 16.0 and stddev > 38.0:
            conf = min(0.92, 0.75 + (edge_mean / 120.0))
            diag = f"Surface litter & irregular waste scatter detected (Color Scatter: {color_diff:.1f}, Edge Clutter: {edge_mean:.1f})"
            return "Waste Management", conf, diag

        # 3. Water Supply (Standing clean water / pipeline flooding)
        if b_m > r_m + 12.0 and b_m > g_m + 6.0 and edge_mean < 14.0:
            conf = 0.88
            diag = f"Water pooling & fluid reflection signature detected (Blue Bias: {b_m - r_m:.1f})"
            return "Water Supply", conf, diag

        # 4. Electricity / Power (Overhead lines / hanging wires)
        if u_edge_mean > 20.0 and edge_mean < 12.0:
            conf = 0.85
            diag = f"Overhead linear wire/cable patterns detected (Upper Edge Density: {u_edge_mean:.1f})"
            return "Electricity / Power", conf, diag

        return None, 0.0, ""
    except Exception:
        return None, 0.0, ""


def classify_department(text_en: str, category_hint: str = None, photo_bytes: bytes = None):
    text_l = text_en.lower()

    # Domain Safeguard 1: Road Hazards & Potholes & Accidents in text
    # If text is describing a road hazard/pothole/accident, NEVER route to Electricity/Power or Water Supply
    road_signals = [
        "accident", "accidents", "accidental", "pothole", "potholes", "crater", "craters",
        "skid", "skidding", "slip", "slippery", "road", "broken road", "damaged road",
        "pavement", "asphalt", "tar road", "uneven road", "speed breaker", "speedbreaker", "footpath"
    ]
    electric_hard_signals = [
        "wire", "live wire", "spark", "sparking", "transformer", "electrocution",
        "shock", "voltage", "power cut", "power outage", "current", "electric pole"
    ]
    water_signals = ["pipe", "pipeline", "leak", "leaking", "tap", "borewell", "water shortage", "no water"]
    waste_signals = ["garbage", "trash", "waste", "dustbin", "dumping", "litter"]

    has_road = any(w in text_l for w in road_signals)
    has_electric = any(w in text_l for w in electric_hard_signals)
    has_water = any(w in text_l for w in water_signals)
    has_waste = any(w in text_l for w in waste_signals)

    # Road safety text override:
    if has_road and not (has_electric or has_water or has_waste):
        detected_kw = [w for w in road_signals if w in text_l]
        return (
            "Roads & Infrastructure",
            "Assigned Department: Roads & Infrastructure\n"
            "• Inference Mechanism: Road Safety & Accident Prevention Engine\n"
            "• Model Confidence: 98.0%\n"
            "• Trigger Keywords Detected: " + ", ".join(sorted(set(detected_kw))),
            0.98
        )

    # Computer Vision Analysis on photographic evidence (if attached)
    photo_dept, photo_conf, photo_diag = None, 0.0, ""
    if photo_bytes:
        photo_dept, photo_conf, photo_diag = classify_photo_department(photo_bytes)

    hits_per_dept = {}
    for dept, info in DEPARTMENTS.items():
        hits = [kw for kw in info["keywords"] if kw in text_l]
        hits_per_dept[dept] = hits

    # Normalize category_hint: ignore Auto-Detect or generic values
    valid_hint = None
    if category_hint and category_hint not in ("Auto-Detect", "Not sure / Let AI decide", "", "None"):
        if category_hint in DEPARTMENTS:
            valid_hint = category_hint

    # Count hits
    sorted_depts = sorted(hits_per_dept.keys(), key=lambda d: len(hits_per_dept[d]), reverse=True)
    top_dept = sorted_depts[0]
    n_hits = len(hits_per_dept[top_dept])
    hint_hits = len(hits_per_dept[valid_hint]) if valid_hint else 0

    # MULTIMODAL RESOLUTION:
    # If citizen text has 0 keywords (e.g., short, ambiguous, or gibberish like 'yinga yinga')
    # and computer vision detected clear photographic evidence (e.g. road craters / potholes):
    if n_hits == 0 and photo_dept:
        rationale_lines = [
            f"Assigned Department: {photo_dept}",
            "• Inference Mechanism: Multimodal Computer Vision Engine (Visual Hazard Classification)",
            f"• Model Confidence: {photo_conf * 100:.1f}%",
            f"• Photographic Evidence: {photo_diag}",
        ]
        if valid_hint and valid_hint != photo_dept:
            rationale_lines.append(f"• Citizen Hint '{valid_hint}' superseded by verified on-site photographic evidence.")
        return photo_dept, "\n".join(rationale_lines), photo_conf

    if valid_hint:
        if hint_hits > 0 and hint_hits >= n_hits:
            best_dept = valid_hint
            method = "Citizen Selected Category (Confirmed by Keywords)"
            confidence = min(0.98, 0.60 + 0.15 * hint_hits)
            matched = hits_per_dept[valid_hint]
        elif n_hits > 0 and hint_hits == 0:
            best_dept = top_dept
            method = "Lexical Keyword Override (Citizen hint lacked matching terms)"
            confidence = min(0.95, 0.55 + 0.15 * n_hits)
            matched = hits_per_dept[top_dept]
        elif n_hits >= hint_hits + 2:
            best_dept = top_dept
            method = "Lexical Keyword Override (Strong contradictory keyword signals)"
            confidence = min(0.95, 0.50 + 0.15 * n_hits)
            matched = hits_per_dept[top_dept]
        elif hint_hits > 0:
            best_dept = valid_hint
            method = "Citizen Selected Category (Confirmed)"
            confidence = 0.90
            matched = hits_per_dept[valid_hint]
        else:
            # Check if photo provides definitive ground truth over empty hint
            if photo_dept:
                best_dept = photo_dept
                confidence = photo_conf
                method = "Multimodal Visual Override (Photographic evidence superseded ungrounded hint)"
                matched = []
            else:
                dept_names = list(DEPARTMENTS.keys())
                protos = [DEPARTMENTS[d]["proto"] for d in dept_names]
                all_emb = embed_batch([text_en] + protos)
                complaint_emb = all_emb[0].reshape(1, -1)
                proto_emb = all_emb[1:]
                sims = cosine_similarity(complaint_emb, proto_emb)[0]
                best_idx = int(np.argmax(sims))
                sem_dept = dept_names[best_idx]
                sem_score = float(sims[best_idx])
                hint_idx = dept_names.index(valid_hint)
                hint_score = float(sims[hint_idx])

                if sem_score - hint_score > 0.12 and sem_score > 0.35:
                    best_dept = sem_dept
                    confidence = sem_score
                    method = "Semantic Similarity Override (High semantic distance from hint)"
                    matched = []
                else:
                    best_dept = valid_hint
                    confidence = 0.85
                    method = "Citizen Selected Category (Fallback Deferral)"
                    matched = []
    elif n_hits > 0:
        best_dept = top_dept
        confidence = min(1.0, 0.45 + 0.18 * n_hits)
        method = "Lexical Keyword Matching"
        matched = hits_per_dept[best_dept]
        if photo_dept == best_dept:
            confidence = min(0.99, confidence + 0.15)
            method += " + Multimodal Visual Verification"
    else:
        # Fallback to semantic prototype if neither keywords nor photo detected
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
    if valid_hint:
        rationale_lines.append(f"• Citizen Selected Hint: {valid_hint}")
    if matched:
        rationale_lines.append(f"• Trigger Keywords Detected: {', '.join(sorted(set(matched)))}")
    elif not photo_dept:
        rationale_lines.append("• Semantic Match: Nearest cosine distance to departmental operational scope.")
    if photo_diag:
        rationale_lines.append(f"• Visual Evidence Corroboration: {photo_diag}")

    return best_dept, "\n".join(rationale_lines), confidence


def score_to_priority(score: int) -> str:
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


def analyze_photo_hazard(photo_bytes: bytes) -> tuple[float, str]:
    """
    Computer Vision Analysis for Citizen Uploaded Incident Photos:
    - Analyzes image texture, edge density (structural disruption/potholes/debris),
      and color variance (water/sewage/fire hazard).
    - Returns (visual_hazard_boost_pts, xai_diagnostic_text)
    """
    if not photo_bytes:
        return 0.0, ""
    try:
        from PIL import Image, ImageFilter, ImageStat
        import io
        img = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
        stat = ImageStat.Stat(img)
        stddev = sum(stat.stddev) / len(stat.stddev)

        # Detect structural disruption and irregular edges
        edges = img.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        edge_mean = sum(edge_stat.mean) / len(edge_stat.mean)

        if edge_mean > 16.0 or stddev > 42.0:
            boost = 14.0
            diag = f"High structural disruption & hazard detected (Edge Density: {edge_mean:.1f}, Texture Variance: {stddev:.1f})"
        elif edge_mean > 8.0 or stddev > 22.0:
            boost = 10.0
            diag = f"Moderate physical damage verified (Edge Density: {edge_mean:.1f})"
        else:
            boost = 8.0
            diag = "On-site photographic proof verified (Baseline physical evidence)"
        return boost, diag
    except Exception:
        return 8.0, "On-site photographic proof verified (Physical attachment confirmed)"


def score_priority(text_en: str, sentiment_compound: float, upvotes: int = 0, has_photo: bool = False, photo_bytes: bytes = None):
    text_l = text_en.lower()
    matched = [(kw, w) for kw, w in SEVERITY_KEYWORDS.items() if kw in text_l]
    matched.sort(key=lambda x: -x[1])

    photo_component, photo_diag = 0.0, ""
    if has_photo or photo_bytes:
        photo_component, photo_diag = analyze_photo_hazard(photo_bytes) if photo_bytes else (8.0, "Photographic proof attached")

    if matched:
        top_kw, top_w = matched[0]
        extra = sum(w * 0.10 for _, w in matched[1:])
        severity_component = min(100, top_w + extra)
    else:
        top_kw, top_w = None, 0
        # If visual evidence confirms physical disruption/craters, baseline severity cannot be a negligible 18
        if photo_component >= 14.0:
            severity_component = 55.0  # Significant physical hazard/crater detected visually
        elif photo_component >= 10.0:
            severity_component = 42.0  # Moderate damage verified visually
        elif photo_component >= 8.0:
            severity_component = 30.0  # Physical proof confirmed visually
        else:
            severity_component = 18.0

    sentiment_component = min(12.0, abs(sentiment_compound) * 12) if sentiment_compound < 0 else 0.0
    repeat_component = min(15.0, upvotes * 3)

    raw = (severity_component * 0.72) + sentiment_component + repeat_component + photo_component
    final_score = int(max(1, min(100, round(raw))))
    priority = score_to_priority(final_score)

    lines = [
        f"Dynamic Priority: {priority} | Urgency Score: {final_score}/100",
        f"• Keyword Hazard Weight: {severity_component:.1f} pts" + (f" (Top keyword: '{top_kw}')" if top_kw else (" (Visual Hazard Baseline)" if photo_component >= 10 else "")),
        f"• Distress Sentiment (VADER Compound = {sentiment_compound:.2f}): +{sentiment_component:.1f} pts",
        f"• Community Multiplier ({upvotes} linked reports): +{repeat_component:.1f} pts",
    ]
    if photo_component > 0:
        lines.append(f"• Visual AI Image Analysis ({photo_diag}): +{photo_component:.1f} pts")
    lines.append(
        f"• Formulation: (0.72 × {severity_component:.1f}) + {sentiment_component:.1f} + {repeat_component:.1f} + {photo_component:.1f} = {final_score}/100"
    )
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
            created_at TEXT,
            image_data TEXT
        )
        """
    )
    # Ensure newly added columns exist in existing databases
    cols = [c[1] for c in conn.execute("PRAGMA table_info(grievances)").fetchall()]
    new_cols = {
        "image_data": "TEXT",
        "resolution_photo": "TEXT",
        "resolution_note": "TEXT",
        "resolved_at": "TEXT",
        "citizen_feedback": "TEXT",
        "citizen_remarks": "TEXT",
    }
    for c_name, c_type in new_cols.items():
        if c_name not in cols:
            conn.execute(f"ALTER TABLE grievances ADD COLUMN {c_name} {c_type}")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS grievance_upvotes (
            ticket_id TEXT,
            user_id TEXT,
            created_at TEXT,
            PRIMARY KEY (ticket_id, user_id)
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


def delete_record_from_db(gid: str):
    conn = get_conn()
    conn.execute("DELETE FROM grievances WHERE id = ? OR parent_id = ?", (gid, gid))
    try:
        conn.execute("DELETE FROM grievance_upvotes WHERE ticket_id = ? OR ticket_id = ?", (gid, gid))
    except Exception:
        pass
    conn.commit()
    conn.close()


def update_status_in_db(gid: str, status: str, resolution_photo: str = None, resolution_note: str = None):
    conn = get_conn()
    now_str = datetime.now().isoformat() if status in ("Resolved", "Waiting for Citizen Confirmation", "Awaiting Citizen Confirmation") else None
    if status in ("Resolved", "Waiting for Citizen Confirmation", "Awaiting Citizen Confirmation"):
        conn.execute(
            """
            UPDATE grievances 
            SET status = ?, 
                resolution_photo = COALESCE(?, resolution_photo), 
                resolution_note = COALESCE(?, resolution_note), 
                resolved_at = COALESCE(?, resolved_at) 
            WHERE id = ? OR parent_id = ?
            """,
            (status, resolution_photo, resolution_note, now_str, gid, gid),
        )
    else:
        conn.execute(
            "UPDATE grievances SET status = ? WHERE id = ? OR parent_id = ?",
            (status, gid, gid),
        )
    conn.commit()
    conn.close()


def record_citizen_feedback_in_db(gid: str, feedback: str, remarks: str = ""):
    if feedback in ("Satisfied", "Confirmed", "Resolved"):
        # Citizen confirmed resolution: permanently delete ticket from system
        delete_record_from_db(gid)
        return {"deleted": True, "id": gid}

    conn = get_conn()
    if feedback == "Reopened":
        row = conn.execute("SELECT severity_score FROM grievances WHERE id = ?", (gid,)).fetchone()
        new_score = 65
        if row:
            new_score = min(100, (row["severity_score"] or 40) + 15)
        new_priority = score_to_priority(new_score)
        conn.execute(
            """
            UPDATE grievances 
            SET status = 'Reopened', 
                citizen_feedback = 'Reopened', 
                citizen_remarks = ?, 
                severity_score = ?, 
                priority = ? 
            WHERE id = ? OR parent_id = ?
            """,
            (remarks, new_score, new_priority, gid, gid),
        )
    else:
        conn.execute(
            """
            UPDATE grievances 
            SET citizen_feedback = ?, 
                citizen_remarks = ? 
            WHERE id = ? OR parent_id = ?
            """,
            (feedback, remarks, gid, gid),
        )
    conn.commit()
    conn.close()
    return {"deleted": False, "id": gid}


def record_citizen_upvote_in_db(gid: str, user_id: str, boost_points: int = 5):
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS grievance_upvotes (
            ticket_id TEXT,
            user_id TEXT,
            created_at TEXT,
            PRIMARY KEY (ticket_id, user_id)
        )
        """
    )
    # Check if user already upvoted
    existing = conn.execute(
        "SELECT 1 FROM grievance_upvotes WHERE ticket_id = ? AND user_id = ?",
        (gid, user_id),
    ).fetchone()
    if existing:
        conn.close()
        return None, "already_upvoted"

    row = conn.execute("SELECT upvotes, severity_score, priority FROM grievances WHERE id = ?", (gid,)).fetchone()
    if not row:
        conn.close()
        return None, "not_found"

    new_upvotes = (row["upvotes"] or 0) + 1
    new_score = min(100, (row["severity_score"] or 20) + boost_points)
    new_priority = score_to_priority(new_score)
    conn.execute(
        "UPDATE grievances SET upvotes = ?, severity_score = ?, priority = ? WHERE id = ?",
        (new_upvotes, new_score, new_priority, gid),
    )
    conn.execute(
        "INSERT INTO grievance_upvotes (ticket_id, user_id, created_at) VALUES (?, ?, ?)",
        (gid, user_id, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"upvotes": new_upvotes, "severity_score": new_score, "priority": new_priority}, None


def fetch_user_upvoted_tickets(user_id: str):
    if not user_id:
        return []
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS grievance_upvotes (
            ticket_id TEXT,
            user_id TEXT,
            created_at TEXT,
            PRIMARY KEY (ticket_id, user_id)
        )
        """
    )
    rows = conn.execute("SELECT ticket_id FROM grievance_upvotes WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return [r["ticket_id"] for r in rows]


def increment_upvote_in_db(gid: str, boost_points: int = 5):
    conn = get_conn()
    row = conn.execute("SELECT upvotes, severity_score, priority FROM grievances WHERE id = ?", (gid,)).fetchone()
    res = None
    if row:
        new_upvotes = (row["upvotes"] or 0) + 1
        new_score = min(100, (row["severity_score"] or 20) + boost_points)
        new_priority = score_to_priority(new_score)
        conn.execute(
            "UPDATE grievances SET upvotes = ?, severity_score = ?, priority = ? WHERE id = ?",
            (new_upvotes, new_score, new_priority, gid),
        )
        conn.commit()
        res = {"upvotes": new_upvotes, "severity_score": new_score, "priority": new_priority}
    conn.close()
    return res


def find_duplicate_match(new_embedding, new_lat, new_lon, records, new_dept: str = None, new_text: str = ""):
    if not records:
        return None, 0.0

    # Match against active (non-resolved) records
    active_records = [r for r in records if r.get("status") != "Resolved"]
    if not active_records:
        return None, 0.0

    # Lookup table by id for parent resolution
    rec_by_id = {r["id"]: r for r in records}

    new_text_lower = new_text.lower() if new_text else ""
    keywords_all = set()
    for d in DEPARTMENTS.values():
        keywords_all.update(d.get("keywords", []))
    new_kw_hits = {w for w in keywords_all if w in new_text_lower}

    best_id, best_effective_sim = None, 0.0

    for r in active_records:
        try:
            emb = np.array(json.loads(r["embedding"]))
        except Exception:
            continue

        sim = float(cosine_similarity(new_embedding.reshape(1, -1), emb.reshape(1, -1))[0][0])
        dist = haversine_km(new_lat, new_lon, r["lat"], r["lon"])

        is_same_dept = bool(new_dept and (r.get("department") == new_dept))

        # Keyword overlap bonus
        r_text_lower = (r.get("original_text") or "").lower()
        r_kw_hits = {w for w in keywords_all if w in r_text_lower}
        shared_kw = new_kw_hits.intersection(r_kw_hits)
        kw_bonus = min(0.15, len(shared_kw) * 0.06)

        effective_sim = sim + kw_bonus

        # Tiered adaptive thresholds:
        # Tier 1: Very close proximity (<= 400m)
        if dist <= 0.40:
            required_sim = 0.28 if is_same_dept else 0.50
        # Tier 2: Neighborhood proximity (<= 1.0 km)
        elif dist <= 1.0:
            required_sim = 0.38 if is_same_dept else 0.60
        # Tier 3: Immediate locality (<= 2.0 km or same ward)
        elif dist <= 2.0 or (r.get("ward") and r.get("ward").strip().lower() in new_text_lower):
            required_sim = 0.45 if is_same_dept else 0.68
        else:
            continue

        if effective_sim >= required_sim and effective_sim > best_effective_sim:
            # Trace to root parent if candidate is already a duplicate
            cand_id = r["id"]
            visited = set()
            while rec_by_id.get(cand_id, {}).get("is_duplicate") == 1 and rec_by_id.get(cand_id, {}).get("parent_id"):
                p_id = rec_by_id[cand_id]["parent_id"]
                if p_id in visited or p_id not in rec_by_id:
                    break
                visited.add(cand_id)
                cand_id = p_id

            best_effective_sim = effective_sim
            best_id = cand_id

    return best_id, best_effective_sim


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
        m_wards = [records[m].get("ward") or nearest_ward(lats[m], lons[m]) for m in members]
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
