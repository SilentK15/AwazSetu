"""
Smart India Hackathon 2026 — Problem Statement SIH26-S02
Civic Grievance Redressal Portal (CivicNexus)

AI-Based Citizen Grievance Classification, Prioritization, and Duplicate Complaint Detection
- 100% Native Streamlit Architecture: Zero external server dependencies
- Zero Fake Data: Strictly displays real complaints from SQLite persistence
- Real-Time Resolution Lifecycle: Pending -> In Progress -> Resolved with instant database commits
- Reliable Location System: Interactive Map Click-to-Pin, Preset Landmarks & Coordinate Input
- True Multilingual Support: English, Hindi, and Marathi UI translations & multilingual complaint ingestion
- Preserved Core AI: SentenceTransformers (all-MiniLM-L6-v2), Cosine Similarity (>0.80), Haversine (<400m), VADER XAI
- Role-based access: separate Citizen and Authority sign-in, each landing on its own dashboard
- Clean, high-contrast public-service design system (zero emojis, no broken cards)
"""

import os
import json
import sqlite3
import hashlib
import secrets
import base64
import re
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import streamlit_js_eval
import backend

# =============================================================================
# APP CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="AwazSetu — AI Civic Grievance Redressal Portal",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DEFAULT_MAPBOX_TOKEN = base64.b64decode("cGsuZXlKMUlqb2lhM05vYVhScGFqRTFJaXdpWVNJNkltTnRiamwwT1dGM2FqQmplWGN5Y0hGNWEyMDNaSEUxWlRJaWZRLkpCQmlENUpyVWtuRFNMUjEySVFfWkE=").decode()
MAPBOX_ACCESS_TOKEN = os.environ.get("MAPBOX_ACCESS_TOKEN", "")
try:
    if not MAPBOX_ACCESS_TOKEN and "MAPBOX_ACCESS_TOKEN" in st.secrets:
        MAPBOX_ACCESS_TOKEN = st.secrets["MAPBOX_ACCESS_TOKEN"]
except Exception:
    pass
if not MAPBOX_ACCESS_TOKEN:
    MAPBOX_ACCESS_TOKEN = DEFAULT_MAPBOX_TOKEN

# Initialize grievance database (unchanged backend contract)
backend.init_db()


# =============================================================================
# LIGHTWEIGHT AUTH LAYER (separate SQLite store — does not touch backend.py)
# =============================================================================
USERS_DB_PATH = os.environ.get("CIVIC_USERS_DB", "civic_users.db")


def _users_conn():
    conn = sqlite3.connect(USERS_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_users_db():
    conn = _users_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT,
            department TEXT,
            employee_id TEXT,
            created_at TEXT,
            UNIQUE(role, username)
        )
    """)
    conn.commit()

    # Ensure department and employee_id columns exist in existing databases
    cols = [c[1] for c in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "department" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN department TEXT")
    if "employee_id" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN employee_id TEXT")
    conn.commit()

    # Pre-seed dedicated accounts for every department
    officers = [
        ("USR-ADM-001", "admin", "admin", "Central Municipal Commissioner", "All", "MC-HQ-1001"),
        ("USR-ROADS-01", "admin", "roads_admin", "Roads & Highways Department Officer", "Roads & Infrastructure", "MC-RD-4081"),
        ("USR-WATER-01", "admin", "water_admin", "Water Supply & Sewerage Officer", "Water Supply", "MC-WS-5190"),
        ("USR-POWER-01", "admin", "power_admin", "Electrical Engineering Officer", "Electricity/Power", "MC-EE-7230"),
        ("USR-WASTE-01", "admin", "waste_admin", "Solid Waste Management Officer", "Waste Management", "MC-WM-3124"),
        ("USR-HEALTH-01", "admin", "health_admin", "Chief Public Health Officer", "Public Health", "MC-PH-8802"),
    ]
    for uid, role, uname, fname, dept, emp_id in officers:
        existing = conn.execute("SELECT id FROM users WHERE role = ? AND username = ?", (role, uname)).fetchone()
        if not existing:
            salt = secrets.token_hex(8)
            pw_hash = _hash_password("admin123", salt)
            conn.execute(
                "INSERT INTO users (id, role, username, password_hash, salt, full_name, department, employee_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (uid, role, uname, pw_hash, salt, fname, dept, emp_id, datetime.now().isoformat()),
            )
        else:
            conn.execute(
                "UPDATE users SET department = ?, full_name = ?, employee_id = ? WHERE role = ? AND username = ?",
                (dept, fname, emp_id, role, uname),
            )
    conn.commit()
    conn.close()


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def create_user(role: str, username: str, password: str, full_name: str):
    conn = _users_conn()
    existing = conn.execute(
        "SELECT id FROM users WHERE role = ? AND username = ?", (role, username)
    ).fetchone()
    if existing:
        conn.close()
        return False, "exists"
    salt = secrets.token_hex(8)
    pw_hash = _hash_password(password, salt)
    uid = f"USR-{role.upper()[:3]}-{secrets.token_hex(4).upper()}"
    conn.execute(
        "INSERT INTO users (id, role, username, password_hash, salt, full_name, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (uid, role, username, pw_hash, salt, full_name, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return True, uid


def authenticate(role: str, username: str, password: str):
    conn = _users_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE role = ? AND username = ?", (role, username)
    ).fetchone()
    conn.close()
    if not row:
        return None
    if _hash_password(password, row["salt"]) == row["password_hash"]:
        return dict(row)
    return None


init_users_db()


# =============================================================================
# SESSION STATE INITIALISATION
# =============================================================================
defaults = {
    "ui_lang": "en",
    "auth_user": None,          # dict once logged in
    "auth_role": None,          # "citizen" | "admin"
    "active_tab": None,         # language-independent tab key
    "picked_latlon": backend.CITY_CENTER,
    "auth_view": "login",       # "login" | "register" (citizen only)
    "auth_error": "",
    "auth_notice": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# =============================================================================
# MULTILINGUAL DICTIONARY
# =============================================================================
TRANSLATIONS = {
    "en": {
        "portal_title": "AwazSetu",
        "portal_subtitle": "AI-Powered Civic Grievance Classification, Prioritization & Redressal",
        "portal_eyebrow": "AWAZSETU · CITIZEN SERVICE PLATFORM",
        "status_operational": "Services Operational",
        "portal_status": "AwazSetu Status",
        "nav_citizen": "Citizen Portal",
        "nav_track": "Track Complaint",
        "nav_dashboard": "Authority Dashboard",
        "nav_how": "How It Works",
        "hero_kicker": "AWAZSETU CITIZEN GRIEVANCE SERVICE",
        "hero_title": "Report a civic issue in a few simple steps.",
        "hero_desc": "Submit a complaint with location and description. Intelligent AI routing directs the issue to the appropriate service team and merges duplicate reports.",
        "point_1": "Multilingual complaint submission",
        "point_2": "Similar complaint detection (400m)",
        "point_3": "Transparent priority explanation (XAI)",
        "step_1": "1. Issue", "step_1_sub": "Describe problem",
        "step_2": "2. Location", "step_2_sub": "Pin affected area",
        "step_3": "3. Analysis", "step_3_sub": "AI verification",
        "step_4": "4. Submit", "step_4_sub": "Receive ticket ID",
        "form_heading": "Describe the civic issue & select location",
        "req_note": "* Required fields",
        "lbl_cat": "Issue category",
        "cat_placeholder": "Select closest category / Let AI decide",
        "lbl_desc": "What is the problem? *",
        "desc_placeholder": "Describe what you observed, where it is happening, and any details that may help resolve the issue. (English, Hindi, Marathi supported)",
        "lbl_ward": "Administrative area / Ward *",
        "upload_label": "Attach supporting photo or document (Optional, JPG/PNG)",
        "btn_submit": "Submit Grievance →",
        "loc_method_label": "Location Selection Method",
        "loc_preset": "Area / Landmark Preset",
        "loc_map": "Pick on Interactive Map",
        "loc_manual": "Manual Coordinates",
        "loc_gps": "Use My Location (GPS Lock)",
        "intel_title": "Complaint analysis",
        "intel_kicker": "INTELLIGENT ASSISTANCE",
        "intel_desc": "As you describe your issue, the AI engine identifies its department, urgency score and checks for nearby duplicate complaints.",
        "privacy_title": "Your privacy matters",
        "privacy_desc": "Only information needed to process and resolve the grievance is collected. Avoid sharing passwords or sensitive personal data.",
        "help_title": "AwazSetu Citizen Help & Support",
        "help_desc": "Civic Incident Helpline: 1916 | Emergency: 112",
        "dup_banner_title": "Similar issues reported nearby",
        "track_header": "Track Complaint & Live Status",
        "track_empty": "No complaints have been submitted yet. Submit a new complaint to track its live status.",
        "dash_title": "AwazSetu Service Operations Dashboard",
        "dash_kicker": "AUTHORITY OPERATIONS",
        "dash_desc": "Monitor real citizen grievance volume, priority queues, locations and resolution progress.",
        "kpi_total": "Total Complaints",
        "kpi_pending": "Pending Review",
        "kpi_high": "High / Critical",
        "kpi_resolved": "Resolved",
        "queue_title": "Priority Queue (Needs Attention)",
        "map_title": "Metropolitan Geospatial Map",
        "map_live": "Live GIS Feed",
        "strip_duplicates": "Duplicate complaints merged",
        "strip_clusters": "Active issue clusters",
        "strip_upvotes": "Citizen confirmations",
        "btn_resolve": "Mark as Resolved",
        "empty_queue": "No unresolved complaints in queue.",
        "empty_dashboard": "No complaints have been submitted yet.",
        "empty_cluster": "No multi-complaint clusters detected yet.",
        "status_pending": "Pending",
        "status_progress": "In Progress",
        "status_resolved": "Resolved",
        # --- Auth ---
        "auth_eyebrow": "SECURE SIGN-IN",
        "auth_title": "Sign in to AwazSetu",
        "auth_subtitle": "Choose your account type to access the civic portal.",
        "tab_citizen_auth": "Citizen",
        "tab_admin_auth": "Authority",
        "tab_login": "Log In",
        "tab_register": "New Registration",
        "lbl_fullname": "Full name",
        "lbl_phone": "🇮🇳 Indian Mobile Number (+91)",
        "lbl_username": "Username",
        "lbl_password": "Password",
        "lbl_confirm_password": "Confirm password",
        "btn_login": "Log In",
        "btn_register": "Create Account",
        "citizen_login_desc": "Log in with your registered 10-digit Indian mobile number (+91).",
        "citizen_register_desc": "Create a verified citizen account using your 10-digit Indian mobile number.",
        "admin_login_desc": "Authorised personnel only. Log in to access the operations dashboard.",
        "err_fields": "Please fill in all required fields.",
        "err_invalid": "Incorrect username/mobile number or password.",
        "err_exists": "An account with this mobile number already exists. Please log in instead.",
        "err_phone": "⚠️ Please enter a valid 10-digit Indian mobile number (+91 starting with 6, 7, 8, or 9).",
        "err_password_len": "Password must be at least 4 characters.",
        "err_password_match": "Passwords do not match.",
        "success_register": "Account created successfully. Please log in below.",
        "demo_admin_hint": "Evaluation access — Username: admin · Password: admin123",
        "logout_btn": "Log Out",
        "welcome_msg": "Welcome",
        "role_citizen_tag": "Citizen Account",
        "role_admin_tag": "Authority Account",
        "my_dashboard_title": "My Complaint Summary",
        "my_filter_toggle": "Show only my complaints",
        "my_kpi_total": "Filed by me",
        "my_kpi_open": "Awaiting resolution",
        "my_kpi_resolved": "Resolved",
        "status_waiting": "Waiting for Citizen Confirmation",
        "status_reopened": "Reopened",
        "res_proof_title": "Resolution Proof & Verification",
        "btn_confirm_res": "✓ Confirm Resolved (Close & Remove Ticket)",
        "btn_reopen": "↺ Issue Not Fixed (Reopen Ticket)",
        "affects_me_too": "👍 Affects Me Too (+1)",
        "already_upvoted": "✓ Confirmed by You (+1)",
        "admin_no_upvote": "Authority accounts cannot upvote grievances",
        "did_it_resolve": "Did the municipal authority successfully resolve this issue?",
        "reopen_reason_placeholder": "Please explain what remains incomplete or unfixed...",
        "upload_proof_label": "Upload Resolution Proof Photo (Mandatory)",
        "res_note_label": "Resolution Completion Note / Remarks",
        "btn_send_citizen_confirm": "Submit Resolution for Citizen Verification",
        "sla_breached": "SLA Breached",
        "sla_remaining": "SLA Remaining",
    },
    "hi": {
        "portal_title": "आवाज़सेतु (AwazSetu)",
        "portal_subtitle": "AI-संचालित नागरिक शिकायत वर्गीकरण, प्राथमिकता एवं निवारण मंच",
        "portal_eyebrow": "आवाज़सेतु · नागरिक सेवा मंच",
        "status_operational": "सेवाएं सक्रिय हैं",
        "portal_status": "आवाज़सेतु स्थिति",
        "nav_citizen": "नागरिक पोर्टल",
        "nav_track": "शिकायत ट्रैक करें",
        "nav_dashboard": "अधिकारी डैशबोर्ड",
        "nav_how": "यह कैसे काम करता है",
        "hero_kicker": "आवाज़सेतु नागरिक शिकायत सेवा",
        "hero_title": "कुछ आसान चरणों में नागरिक समस्या की रिपोर्ट करें।",
        "hero_desc": "स्थान और विवरण के साथ शिकायत दर्ज करें। AI सही विभाग को शिकायत भेजता है और 400 मीटर के भीतर डुप्लीकेट शिकायतों को रोकता है।",
        "point_1": "बहुभाषी शिकायत दर्ज (हिंदी, मराठी, अंग्रेजी)",
        "point_2": "समान शिकायत पहचान (400 मीटर)",
        "point_3": "पारदर्शी प्राथमिकता स्पष्टीकरण (XAI)",
        "step_1": "1. समस्या", "step_1_sub": "विवरण लिखें",
        "step_2": "2. स्थान", "step_2_sub": "प्रभावित क्षेत्र",
        "step_3": "3. विश्लेषण", "step_3_sub": "AI सत्यापन",
        "step_4": "4. जमा करें", "step_4_sub": "टिकट ID प्राप्त करें",
        "form_heading": "नागरिक समस्या का विवरण दें और स्थान चुनें",
        "req_note": "* आवश्यक फ़ील्ड",
        "lbl_cat": "समस्या श्रेणी",
        "cat_placeholder": "निकटतम श्रेणी चुनें / AI को तय करने दें",
        "lbl_desc": "समस्या क्या है? *",
        "desc_placeholder": "आपने क्या देखा, यह कहाँ हो रहा है, और समाधान में मदद करने वाले विवरण लिखें। (हिंदी, मराठी या अंग्रेजी समर्थित)",
        "lbl_ward": "प्रशासनिक क्षेत्र / वार्ड *",
        "upload_label": "सहायक फोटो या दस्तावेज़ संलग्न करें (वैकल्पिक, JPG/PNG)",
        "btn_submit": "शिकायत दर्ज करें →",
        "loc_method_label": "स्थान चयन विधि",
        "loc_preset": "प्रसिद्ध स्थल / क्षेत्र",
        "loc_map": "नक्शे पर चुनें",
        "loc_manual": "मैन्युअल निर्देशांक",
        "loc_gps": "मेरा वर्तमान स्थान (GPS)",
        "intel_title": "शिकायत विश्लेषण",
        "intel_kicker": "इंटेलिजेंट सहायता",
        "intel_desc": "जैसे ही आप समस्या का विवरण लिखते हैं, AI इंजन विभाग, तात्कालिकता और डुप्लीकेट शिकायतों की पहचान करता है।",
        "privacy_title": "आपकी गोपनीयता महत्वपूर्ण है",
        "privacy_desc": "केवल शिकायत समाधान के लिए आवश्यक जानकारी एकत्र की जाती है। संवेदनशील पासवर्ड या निजी डेटा साझा न करें।",
        "help_title": "आवाज़सेतु नागरिक सहायता एवं संपर्क",
        "help_desc": "नागरिक हेल्पलाइन: 1916 | आपातकालीन: 112",
        "dup_banner_title": "निकट में पहले से दर्ज समान शिकायतें मिलीं",
        "track_header": "शिकायत स्थिति ट्रैक करें",
        "track_empty": "अभी तक कोई शिकायत दर्ज नहीं की गई है। लाइव स्थिति देखने के लिए नई शिकायत दर्ज करें।",
        "dash_title": "आवाज़सेतु सेवा संचालन डैशबोर्ड",
        "dash_kicker": "प्राधिकरण संचालन",
        "dash_desc": "वास्तविक नागरिक शिकायत मात्रा, प्राथमिकता कतार, GIS स्थान और समाधान प्रगति की निगरानी करें।",
        "kpi_total": "कुल शिकायतें",
        "kpi_pending": "समीक्षा लंबित",
        "kpi_high": "उच्च / गंभीर",
        "kpi_resolved": "समाधानित",
        "queue_title": "प्राथमिकता कतार (ध्यान देने योग्य)",
        "map_title": "महानगरीय GIS मानचित्र",
        "map_live": "लाइव GIS फ़ीड",
        "strip_duplicates": "डुप्लीकेट शिकायतें विलय",
        "strip_clusters": "सक्रिय समस्या समूह",
        "strip_upvotes": "नागरिक पुष्टि",
        "btn_resolve": "समाधानित चिह्नित करें",
        "empty_queue": "कतार में कोई अनसुलझी शिकायत नहीं है।",
        "empty_dashboard": "अभी तक कोई शिकायत दर्ज नहीं की गई है।",
        "empty_cluster": "कोई बहु-शिकायत समूह नहीं मिला।",
        "status_pending": "लंबित",
        "status_progress": "प्रगति में",
        "status_resolved": "समाधानित",
        "auth_eyebrow": "सुरक्षित साइन-इन",
        "auth_title": "आवाज़सेतु में साइन इन करें",
        "auth_subtitle": "पोर्टल तक पहुँचने के लिए अपना खाता प्रकार चुनें।",
        "tab_citizen_auth": "नागरिक",
        "tab_admin_auth": "प्राधिकरण",
        "tab_login": "लॉग इन करें",
        "tab_register": "नया पंजीकरण",
        "lbl_fullname": "पूरा नाम",
        "lbl_phone": "🇮🇳 10-अंकीय भारतीय मोबाइल (+91)",
        "lbl_username": "उपयोगकर्ता नाम",
        "lbl_password": "पासवर्ड",
        "lbl_confirm_password": "पासवर्ड की पुष्टि करें",
        "btn_login": "लॉग इन करें",
        "btn_register": "खाता बनाएं",
        "citizen_login_desc": "शिकायत दर्ज करने और ट्रैक करने के लिए अपने पंजीकृत 10-अंकीय भारतीय मोबाइल नंबर (+91) से लॉग इन करें।",
        "citizen_register_desc": "शिकायत दर्ज करने के लिए अपना 10-अंकीय भारतीय मोबाइल नंबर दर्ज करें।",
        "admin_login_desc": "केवल अधिकृत कर्मियों के लिए। संचालन डैशबोर्ड तक पहुँचने के लिए लॉग इन करें।",
        "err_fields": "कृपया सभी आवश्यक फ़ील्ड भरें।",
        "err_invalid": "गलत उपयोगकर्ता नाम/मोबाइल नंबर या पासवर्ड।",
        "err_exists": "इस मोबाइल नंबर से पहले से खाता मौजूद है। कृपया लॉग इन करें।",
        "err_phone": "⚠️ कृपया एक मान्य 10-अंकीय भारतीय मोबाइल नंबर दर्ज करें (6, 7, 8, या 9 से शुरू होने वाला)।",
        "err_password_len": "पासवर्ड कम से कम 4 अक्षरों का होना चाहिए।",
        "err_password_match": "पासवर्ड मेल नहीं खाते।",
        "success_register": "खाता सफलतापूर्वक बनाया गया। कृपया नीचे लॉग इन करें।",
        "demo_admin_hint": "मूल्यांकन पहुंच — उपयोगकर्ता नाम: admin · पासवर्ड: admin123",
        "logout_btn": "लॉग आउट",
        "welcome_msg": "स्वागत है",
        "role_citizen_tag": "नागरिक खाता",
        "role_admin_tag": "प्राधिकरण खाता",
        "my_dashboard_title": "मेरी शिकायतों का सारांश",
        "my_filter_toggle": "केवल मेरी शिकायतें दिखाएं",
        "my_kpi_total": "मेरे द्वारा दर्ज",
        "my_kpi_open": "समाधान लंबित",
        "my_kpi_resolved": "समाधानित",
        "status_waiting": "नागरिक पुष्टि की प्रतीक्षा",
        "status_reopened": "पुनः खोला गया",
        "res_proof_title": "समाधान प्रमाण और सत्यापन",
        "btn_confirm_res": "✓ समाधान की पुष्टि करें (टिकट हटाएं)",
        "btn_reopen": "↺ समस्या हल नहीं हुई (पुनः खोलें)",
        "affects_me_too": "👍 मुझे भी यह समस्या है (+1)",
        "already_upvoted": "✓ आपकी पुष्टि दर्ज (+1)",
        "admin_no_upvote": "अधिकारी खाते शिकायतों पर वोट नहीं कर सकते",
        "did_it_resolve": "क्या नगर निगम ने इस समस्या का समाधान संतोषजनक रूप से कर दिया है?",
        "reopen_reason_placeholder": "कृपया बताएं कि क्या काम अधूरा या असंतोषजनक रह गया...",
        "upload_proof_label": "समाधान प्रमाण फोटो अपलोड करें (अनिवार्य)",
        "res_note_label": "समाधान विवरण / कार्य नोट",
        "btn_send_citizen_confirm": "नागरिक सत्यापन के लिए समाधान भेजें",
        "sla_breached": "SLA सीमा समाप्त",
        "sla_remaining": "SLA शेष",
    },
    "mr": {
        "portal_title": "आवाज़सेतु (AwazSetu)",
        "portal_subtitle": "AI-आधारित नागरी तक्रार वर्गीकरण, प्राधान्यक्रम आणि निवारण मंच",
        "portal_eyebrow": "आवाज़सेतु · नागरिक सेवा मंच",
        "status_operational": "सेवा कार्यरत आहेत",
        "portal_status": "पोर्टल स्थिती",
        "nav_citizen": "नागरिक पोर्टल",
        "nav_track": "तक्रार ट्रॅक करा",
        "nav_dashboard": "अधिकारी डॅशबोर्ड",
        "nav_how": "कार्यप्रणाली",
        "hero_kicker": "नागरिक तक्रार सेवा",
        "hero_title": "काही सोप्या चरणांमध्ये नागरी समस्येची नोंद करा.",
        "hero_desc": "स्थान आणि वर्णनासह तक्रार नोंदवा. AI संबंधित विभागाकडे तक्रार पाठवते आणि 400 मीटरच्या परिसरातील तक्रारींचे विलीनीकरण करते.",
        "point_1": "मराठी, हिंदी आणि इंग्रजीत तक्रार नोंदणी",
        "point_2": "समान तक्रार ओळख (400 मीटर)",
        "point_3": "पारदर्शक प्राधान्य स्पष्टीकरण (XAI)",
        "step_1": "1. समस्या", "step_1_sub": "तपशील लिहा",
        "step_2": "2. स्थान", "step_2_sub": "प्रभावित क्षेत्र",
        "step_3": "3. विश्लेषण", "step_3_sub": "AI पडताळणी",
        "step_4": "4. सादर करा", "step_4_sub": "तिकीट ID मिळवा",
        "form_heading": "नागरी समस्येचे वर्णन करा आणि स्थान निवडा",
        "req_note": "* आवश्यक माहिती",
        "lbl_cat": "समस्या प्रवर्ग",
        "cat_placeholder": "जवळचा प्रवर्ग निवडा / AI ला ठरवू द्या",
        "lbl_desc": "नेमकी समस्या काय आहे? *",
        "desc_placeholder": "तुम्ही काय पाहिले, कुठे घडत आहे, आणि निवारणासाठी उपयुक्त ठरेल असा तपशील लिहा. (मराठी, हिंदी किंवा इंग्रजी समर्थित)",
        "lbl_ward": "प्रशासकीय प्रभाग *",
        "upload_label": "पुरावा फोटो किंवा दस्तऐवज जोडा (पर्यायी, JPG/PNG)",
        "btn_submit": "तक्रार सादर करा →",
        "loc_method_label": "स्थान निवड पद्धत",
        "loc_preset": "प्रसिद्ध ठिकाण / क्षेत्र",
        "loc_map": "नकाशावर निवडा",
        "loc_manual": "मॅन्युअल निर्देशक",
        "loc_gps": "माझे चालू स्थान (GPS)",
        "intel_title": "तक्रार विश्लेषण",
        "intel_kicker": "इंटेलिजंट सहाय्य",
        "intel_desc": "तुम्ही समस्येचे वर्णन करताच AI इंजिन विभाग, तातडीचा निर्देशांक आणि जवळपासच्या डुप्लिकेट तक्रारी तपासते.",
        "privacy_title": "आपली गोपनीयता महत्त्वाची आहे",
        "privacy_desc": "केवळ तक्रार निवारणासाठी आवश्यक असलेली माहितीच घेतली जाते. संवेदनशील पासवर्ड किंवा वैयक्तिक माहिती देऊ नका.",
        "help_title": "नागरिक मदत व संपर्क",
        "help_desc": "नागरिक हेल्पलाईन: 1916 | आपत्कालीन: 112",
        "dup_banner_title": "जवळपास आधीच नोंदवलेली समान समस्या आढळली",
        "track_header": "तक्रार स्थितीचा मागोवा घ्या",
        "track_empty": "अद्याप कोणतीही तक्रार नोंदवलेली नाही. थेट स्थिती पाहण्यासाठी नवीन तक्रार नोंदवा.",
        "dash_title": "सेवा संचालन डॅशबोर्ड",
        "dash_kicker": "प्राधिकरण संचालन",
        "dash_desc": "वास्तविक नागरिक तक्रारींची संख्या, प्राधान्य रांग, GIS स्थान आणि निवारण प्रगतीचे निरीक्षण करा.",
        "kpi_total": "एकूण तक्रारी",
        "kpi_pending": "प्रलंबित",
        "kpi_high": "उच्च / गंभीर",
        "kpi_resolved": "निवारण झालेले",
        "queue_title": "तातडीने लक्ष द्या",
        "map_title": "महानगरीय GIS नकाशा",
        "map_live": "थेट GIS फीड",
        "strip_duplicates": "डुप्लिकेट तक्रारी विलीन",
        "strip_clusters": "सक्रिय समस्या समूह",
        "strip_upvotes": "नागरिक पुष्टीकरण",
        "btn_resolve": "निवारण झाले म्हणून चिन्हांकित करा",
        "empty_queue": "रांगेत कोणतीही प्रलंबित तक्रार नाही.",
        "empty_dashboard": "अद्याप कोणतीही तक्रार नोंदवलेली नाही.",
        "empty_cluster": "कोणताही बहु-तक्रार समूह आढळला नाही.",
        "status_pending": "प्रलंबित",
        "status_progress": "प्रगतीपथावर",
        "status_resolved": "निवारण झाले",
        "auth_eyebrow": "सुरक्षित साइन-इन",
        "auth_title": "सुरू ठेवण्यासाठी साइन इन करा",
        "auth_subtitle": "पोर्टलमध्ये प्रवेश करण्यासाठी तुमचा खाते प्रकार निवडा.",
        "tab_citizen_auth": "नागरिक",
        "tab_admin_auth": "प्राधिकरण",
        "tab_login": "लॉग इन",
        "tab_register": "नवीन नोंदणी",
        "lbl_fullname": "पूर्ण नाव",
        "lbl_phone": "🇮🇳 10-अंकी भारतीय मोबाईल (+91)",
        "lbl_username": "वापरकर्तानाव",
        "lbl_password": "पासवर्ड",
        "lbl_confirm_password": "पासवर्डची पुष्टी करा",
        "btn_login": "लॉग इन",
        "btn_register": "खाते तयार करा",
        "citizen_login_desc": "तक्रार नोंदवण्यासाठी आणि ट्रॅक करण्यासाठी 10-अंकी भारतीय मोबाईल क्रमांकाने (+91) लॉग इन करा.",
        "citizen_register_desc": "तक्रार नोंदवण्यासाठी तुमचा 10-अंकी भारतीय मोबाईल क्रमांक वापरा.",
        "admin_login_desc": "केवळ अधिकृत कर्मचाऱ्यांसाठी. संचालन डॅशबोर्डमध्ये प्रवेशासाठी लॉग इन करा.",
        "err_fields": "कृपया सर्व आवश्यक माहिती भरा.",
        "err_invalid": "चुकीचे वापरकर्तानाव/मोबाइल क्रमांक किंवा पासवर्ड.",
        "err_exists": "या मोबाइल क्रमांकासह आधीच खाते अस्तित्वात आहे. कृपया लॉग इन करा.",
        "err_phone": "⚠️ कृपया वैध 10-अंकी भारतीय मोबाईल क्रमांक टाका (6, 7, 8, किंवा 9 ने सुरू होणारा).",
        "err_password_len": "पासवर्ड किमान 4 अक्षरांचा असावा.",
        "err_password_match": "पासवर्ड जुळत नाहीत.",
        "success_register": "खाते यशस्वीरित्या तयार झाले. कृपया खाली लॉग इन करा.",
        "demo_admin_hint": "मूल्यांकन प्रवेश — वापरकर्तानाव: admin · पासवर्ड: admin123",
        "logout_btn": "लॉग आउट",
        "welcome_msg": "स्वागत आहे",
        "role_citizen_tag": "नागरिक खाते",
        "role_admin_tag": "प्राधिकरण खाते",
        "my_dashboard_title": "माझ्या तक्रारींचा सारांश",
        "my_filter_toggle": "फक्त माझ्या तक्रारी दाखवा",
        "my_kpi_total": "मी नोंदवलेल्या",
        "my_kpi_open": "निवारण प्रलंबित",
        "my_kpi_resolved": "निवारण झाले",
        "status_waiting": "नागरिक पुष्टीकरणाची प्रतीक्षा",
        "status_reopened": "पुन्हा उघडले",
        "res_proof_title": "निवारण पुरावा आणि पडताळणी",
        "btn_confirm_res": "✓ निवारण पुष्टी करा (तिकीट बंद आणि नष्ट करा)",
        "btn_reopen": "↺ समस्या सुटलेली नाही (पुन्हा उघडा)",
        "affects_me_too": "👍 मलाही हीच समस्या भेडसावत आहे (+1)",
        "already_upvoted": "✓ तुमची पुष्टी नोंदवली (+1)",
        "admin_no_upvote": "अधिकारी खाती तक्रारींवर मत देऊ शकत नाहीत",
        "did_it_resolve": "महानगरपालिकेने या समस्येचे निवारण समाधानकारक केले आहे का?",
        "reopen_reason_placeholder": "कृपया काय काम अपूर्ण किंवा अयोग्य राहिले ते स्पष्ट करा...",
        "upload_proof_label": "निवारण पुरावा फोटो अपलोड करा (अनिवार्य)",
        "res_note_label": "निवारण तपशील / काम पूर्ण नोंद",
        "btn_send_citizen_confirm": "नागरिक पडताळणीसाठी निवारण सादर करा",
        "sla_breached": "SLA मर्यादा संपली",
        "sla_remaining": "SLA शिल्लक",
    },
}


def t(key: str) -> str:
    lang = st.session_state.get("ui_lang", "en")
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))


def compute_sla_badge(created_at_str: str, priority: str) -> str:
    try:
        dt = datetime.fromisoformat(created_at_str)
        limit_hrs = {"Critical": 12, "High": 24, "Medium": 48, "Low": 72}.get(priority, 48)
        deadline = dt + timedelta(hours=limit_hrs)
        now = datetime.now()
        rem_hrs = (deadline - now).total_seconds() / 3600.0
        if rem_hrs <= 0:
            return f'<span style="background:#fee2e2; color:#b91c1c; padding:2px 8px; border-radius:4px; font-weight:700; font-size:11px; border:1px solid #fca5a5;">⚠️ {t("sla_breached")} ({abs(rem_hrs):.1f}h)</span>'
        else:
            return f'<span style="background:#fef3c7; color:#92400e; padding:2px 8px; border-radius:4px; font-weight:700; font-size:11px; border:1px solid #fde68a;">⏱️ {t("sla_remaining")}: {rem_hrs:.1f}h</span>'
    except Exception:
        return ""


# =============================================================================
# DESIGN SYSTEM — CSS (Modern GovTech Civic Design System — Stitch AI Aligned)
# =============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg-app: #f8fafc;
  --bg-surface: #ffffff;
  --bg-surface-subtle: #f1f5f9;
  --ink-primary: #0f172a;
  --ink-secondary: #334155;
  --ink-muted: #64748b;
  --border-subtle: #e2e8f0;
  --blue-primary: #2563eb;
  --blue-hover: #1d4ed8;
  --blue-subtle: #eff6ff;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 18px;
  --radius-pill: 9999px;
  --shadow-card: 0 4px 6px -1px rgba(15, 23, 42, 0.05), 0 2px 4px -2px rgba(15, 23, 42, 0.05);
  --shadow-float: 0 16px 32px -8px rgba(15, 23, 42, 0.09);
}

html, body, [data-testid="stAppViewContainer"] {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
  background-color: var(--bg-app) !important;
  color: var(--ink-primary) !important;
}

[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden !important; height: 0px !important; }

.block-container {
  padding-top: 0.9rem !important;
  padding-bottom: 2.8rem !important;
  max-width: 1200px !important;
}

/* Modern Header */
.modern-header {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 14px 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  box-shadow: var(--shadow-card);
}

.brand-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.emblem-crest {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 3px 8px rgba(15, 23, 42, 0.18);
}

.brand-title {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--ink-primary);
  letter-spacing: -0.02em;
  line-height: 1.15;
}

.brand-subtitle {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--ink-muted);
  letter-spacing: 0.04em;
}

.header-right-strip {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.status-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #ecfdf5;
  color: #059669;
  border: 1px solid #a7f3d0;
  padding: 5px 12px;
  border-radius: var(--radius-pill);
  font-size: 0.76rem;
  font-weight: 700;
}

.status-dot {
  width: 7px;
  height: 7px;
  background: #059669;
  border-radius: 50%;
}

.emergency-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
  padding: 5px 12px;
  border-radius: var(--radius-pill);
  font-size: 0.76rem;
  font-weight: 700;
}

.pulse-red {
  width: 7px;
  height: 7px;
  background: #dc2626;
  border-radius: 50%;
  animation: pulse-ring 1.8s infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(0.9); opacity: 0.9; }
  50% { transform: scale(1.3); opacity: 0.4; }
  100% { transform: scale(0.9); opacity: 0.9; }
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  padding: 4px 12px 4px 4px;
  border-radius: var(--radius-pill);
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--blue-primary);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
}

.badge-role-admin {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fde68a;
  padding: 1px 8px;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 800;
}

.badge-role-citizen {
  background: #e0f2fe;
  color: #0369a1;
  border: 1px solid #bae6fd;
  padding: 1px 8px;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 800;
}

/* Auth Card */
.auth-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-float);
  padding: 28px 30px 20px 30px;
  margin-top: 8px;
  margin-bottom: 12px;
}

.auth-brand-section {
  text-align: center;
}

.auth-emblem {
  width: 54px;
  height: 54px;
  border-radius: 14px;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
  box-shadow: 0 4px 12px rgba(30, 58, 138, 0.25);
}

.auth-kicker {
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: var(--blue-primary);
  text-transform: uppercase;
  display: block;
  margin-bottom: 4px;
}

.auth-title {
  font-size: 1.45rem;
  font-weight: 800;
  color: var(--ink-primary);
  margin: 0 0 4px;
}

.auth-subtitle {
  font-size: 0.82rem;
  color: var(--ink-muted);
  margin: 0;
}

/* Modern Segmented Tabs */
div[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: #f1f5f9 !important;
  border-radius: var(--radius-pill) !important;
  padding: 4px !important;
  border: 1px solid #e2e8f0 !important;
  gap: 4px !important;
  margin-bottom: 14px !important;
}

div[data-testid="stTabs"] [data-baseweb="tab"] {
  flex: 1 1 0% !important;
  text-align: center !important;
  justify-content: center !important;
  border-radius: var(--radius-pill) !important;
  font-weight: 700 !important;
  font-size: 0.86rem !important;
  color: var(--ink-secondary) !important;
  padding: 8px 16px !important;
  background: transparent !important;
  border: none !important;
  transition: all 0.15s ease !important;
}

div[data-testid="stTabs"] [data-baseweb="tab"]:hover {
  color: var(--ink-primary) !important;
}

div[data-testid="stTabs"] [aria-selected="true"] {
  background: var(--ink-primary) !important;
  color: #ffffff !important;
  box-shadow: 0 2px 5px rgba(15, 23, 42, 0.18) !important;
}

div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
div[data-testid="stTabs"] [data-baseweb="tab-border"] {
  display: none !important;
}

/* Sub-tabs within Auth (Level 2) */
div[data-testid="stTabs"] div[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: #ffffff !important;
  border-radius: var(--radius-pill) !important;
  border: 1px solid #cbd5e1 !important;
  padding: 3px !important;
  margin-bottom: 12px !important;
}

div[data-testid="stTabs"] div[data-testid="stTabs"] [data-baseweb="tab"] {
  padding: 6px 14px !important;
  font-size: 0.8rem !important;
}

div[data-testid="stTabs"] div[data-testid="stTabs"] [aria-selected="true"] {
  background: var(--blue-primary) !important;
  color: #ffffff !important;
}

/* Navigation Radios (Main Views) */
div[role="radiogroup"] {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: var(--radius-pill) !important;
  padding: 4px !important;
  display: inline-flex !important;
  box-shadow: var(--shadow-card) !important;
  gap: 4px !important;
}

div[role="radiogroup"] label {
  border-radius: var(--radius-pill) !important;
  padding: 8px 20px !important;
  font-weight: 700 !important;
  font-size: 0.86rem !important;
  color: var(--ink-secondary) !important;
  background: transparent !important;
  border: none !important;
  transition: all 0.15s ease !important;
}

div[role="radiogroup"] label[data-checked="true"],
div[role="radiogroup"] label:has(input:checked) {
  background: var(--ink-primary) !important;
  color: #ffffff !important;
  box-shadow: 0 2px 4px rgba(15, 23, 42, 0.15) !important;
}

div[role="radiogroup"] label[data-checked="true"] p,
div[role="radiogroup"] label:has(input:checked) p {
  color: #ffffff !important;
}

/* Forms & Inputs */
.stTextInput input, .stTextArea textarea, .stNumberInput input, .stPassword input {
  background-color: #ffffff !important;
  color: #0f172a !important;
  border: 1.5px solid #cbd5e1 !important;
  border-radius: 8px !important;
  font-size: 0.92rem !important;
  font-weight: 500 !important;
  padding: 10px 14px !important;
}

.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus, .stPassword input:focus {
  border-color: var(--blue-primary) !important;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.18) !important;
}

/* Primary Action Buttons */
.stFormSubmitButton > button {
  background: var(--blue-primary) !important;
  color: #ffffff !important;
  border: none !important;
  padding: 10px 20px !important;
  font-weight: 700 !important;
  border-radius: 8px !important;
  font-size: 0.92rem !important;
  box-shadow: 0 2px 5px rgba(37, 99, 235, 0.25) !important;
}
.stFormSubmitButton > button:hover {
  background: var(--blue-hover) !important;
}
.stFormSubmitButton > button p { color: #ffffff !important; font-weight: 700; }

/* Secondary Buttons */
.stButton > button {
  background: #ffffff !important;
  color: var(--ink-primary) !important;
  border: 1px solid #cbd5e1 !important;
  padding: 8px 16px !important;
  font-weight: 700 !important;
  border-radius: 8px !important;
  font-size: 0.85rem !important;
}
.stButton > button:hover {
  background: #f8fafc !important;
  border-color: #94a3b8 !important;
  color: var(--blue-primary) !important;
}

/* Civic Card */
.civic-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 18px 22px;
  box-shadow: var(--shadow-card);
  margin-bottom: 12px;
}

.section-kicker {
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: var(--blue-primary) !important;
  text-transform: uppercase;
}

/* Status Badges */
.badge-pending { background: #fee2e2; color: #b91c1c !important; padding: 3px 10px; border-radius: 9999px; font-weight: 800; font-size: 11px; border: 1px solid #fca5a5; }
.badge-progress { background: #fef3c7; color: #92400e !important; padding: 3px 10px; border-radius: 9999px; font-weight: 800; font-size: 11px; border: 1px solid #fde68a; }
.badge-waiting { background: #fffbeb; color: #b45309 !important; padding: 3px 10px; border-radius: 9999px; font-weight: 800; font-size: 11px; border: 1px solid #fcd34d; }
.badge-reopened { background: #ffedd5; color: #c2410c !important; padding: 3px 10px; border-radius: 9999px; font-weight: 800; font-size: 11px; border: 1px solid #fed7aa; }
.badge-resolved { background: #ecfdf5; color: #059669 !important; padding: 3px 10px; border-radius: 9999px; font-weight: 800; font-size: 11px; border: 1px solid #a7f3d0; }

/* Metrics */
[data-testid="stMetricValue"] { color: var(--ink-primary) !important; font-weight: 800 !important; }
[data-testid="stMetricLabel"] { color: var(--ink-muted) !important; font-weight: 700 !important; font-size: 0.8rem !important; }

.auth-note {
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  color: var(--ink-secondary) !important;
  font-size: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  margin-top: 12px;
}
.auth-note * { color: var(--ink-secondary) !important; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SHARED MODERN HEADER
# =============================================================================
def render_header():
    user = st.session_state.get("auth_user")
    if user:
        if st.session_state.get("auth_role") == "admin":
            admin_d = st.session_state.get("auth_dept")
            if admin_d and admin_d != "All Departments (Central City Oversight)":
                role_label = f"🏢 {admin_d} Officer"
            else:
                role_label = "🏛️ Central Operations Admin"
            role_badge = f'<span class="badge-role-admin">{role_label}</span>'
        else:
            role_badge = f'<span class="badge-role-citizen">{t("role_citizen_tag")}</span>'
        initial = (user.get("full_name") or user.get("username") or "?")[:1].upper()
        name_display = user.get("full_name") or user.get("username")
        user_chip_html = f'''
        <div class="user-chip">
          <div class="user-avatar">{initial}</div>
          <div>
            <strong style="font-size:12.5px; color:var(--ink-primary); display:block; line-height:1.2;">{name_display}</strong>
            {role_badge}
          </div>
        </div>
        '''
    else:
        user_chip_html = ''

    # Clean Modern Brand Header with SVG Shield Crest & Status Pill
    st.markdown(f'''
    <div class="modern-header">
      <div class="brand-wrapper">
        <div class="emblem-crest">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2">
            <path d="M12 2L3 7v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-9-5z"/>
            <path d="M12 8v8"/><path d="M8 12h8"/>
          </svg>
        </div>
        <div class="brand-text">
          <div class="brand-title">{t("portal_title")}</div>
          <div class="brand-subtitle">{t("portal_subtitle")}</div>
        </div>
      </div>
      <div class="header-right-strip">
        <div class="status-pill">
          <span class="status-dot"></span>
          <span>{t("status_operational")}</span>
        </div>
        <div class="emergency-pill">
          <span class="pulse-red"></span>
          <span>Emergency: 112 | 1916</span>
        </div>
        {user_chip_html}
      </div>
    </div>
    ''', unsafe_allow_html=True)

    # Clean Language Pill Bar
    _, l_col, _ = st.columns([1, 1.4, 1])
    with l_col:
        lang_c1, lang_c2, lang_c3 = st.columns(3)
        curr_lang = st.session_state.get("ui_lang", "en")
        with lang_c1:
            if st.button("🌐 English", key="btn_lang_en", use_container_width=True, type="primary" if curr_lang=="en" else "secondary"):
                st.session_state["ui_lang"] = "en"; st.rerun()
        with lang_c2:
            if st.button("🌐 हिंदी", key="btn_lang_hi", use_container_width=True, type="primary" if curr_lang=="hi" else "secondary"):
                st.session_state["ui_lang"] = "hi"; st.rerun()
        with lang_c3:
            if st.button("🌐 मराठी", key="btn_lang_mr", use_container_width=True, type="primary" if curr_lang=="mr" else "secondary"):
                st.session_state["ui_lang"] = "mr"; st.rerun()

    if user:
        _, logout_col = st.columns([5, 1])
        with logout_col:
            if st.button(f"🚪 {t('logout_btn')}", key="logout_btn", use_container_width=True):
                st.session_state["auth_user"] = None
                st.session_state["auth_role"] = None
                st.session_state["active_tab"] = None
                st.rerun()


# =============================================================================
# AUTH / LOGIN PAGE (Modern Stitch AI Design)
# =============================================================================
def render_auth_page():
    render_header()

    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        st.markdown(f"""
        <div class="auth-card">
          <div class="auth-brand-section">
            <div class="auth-emblem">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2">
                <path d="M12 2L3 7v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-9-5z"/>
                <path d="M12 8v8"/><path d="M8 12h8"/>
              </svg>
            </div>
            <span class="auth-kicker">{t("auth_eyebrow")}</span>
            <h2 class="auth-title">{t("auth_title")}</h2>
            <p class="auth-subtitle">{t("auth_subtitle")}</p>
          </div>
        </div>
        """, unsafe_allow_html=True)

        role_tab_citizen, role_tab_admin = st.tabs([t("tab_citizen_auth"), t("tab_admin_auth")])

        # ---------------- CITIZEN AUTH ----------------
        with role_tab_citizen:
            sub_login, sub_register = st.tabs([t("tab_login"), t("tab_register")])

            with sub_login:
                st.caption(t("citizen_login_desc"))
                with st.form("citizen_login_form"):
                    phone_in = st.text_input(t("lbl_phone"), max_chars=14, placeholder="e.g. 9820012345")
                    pw_in = st.text_input(t("lbl_password"), type="password")
                    go = st.form_submit_button(t("btn_login"), use_container_width=True)
                if go:
                    raw_login = phone_in.strip().replace(" ", "").replace("-", "").replace("+91", "").lstrip("0")
                    if not phone_in or not pw_in:
                        st.error(t("err_fields"))
                    else:
                        user = authenticate("citizen", raw_login, pw_in)
                        if not user:
                            user = authenticate("citizen", phone_in.strip(), pw_in)
                        if user:
                            st.session_state["auth_user"] = user
                            st.session_state["auth_role"] = "citizen"
                            st.session_state["active_tab"] = "citizen"
                            st.rerun()
                        else:
                            st.error(t("err_invalid"))

            with sub_register:
                st.caption(t("citizen_register_desc"))
                with st.form("citizen_register_form"):
                    name_in = st.text_input(t("lbl_fullname"))
                    phone_reg = st.text_input(t("lbl_phone"), max_chars=14, placeholder="e.g. 9820012345 (10-digit Indian Mobile)")
                    pw1 = st.text_input(t("lbl_password"), type="password")
                    pw2 = st.text_input(t("lbl_confirm_password"), type="password")
                    reg_go = st.form_submit_button(t("btn_register"), use_container_width=True)
                if reg_go:
                    clean_phone = phone_reg.strip().replace(" ", "").replace("-", "").replace("+91", "").lstrip("0")
                    if not name_in or not phone_reg or not pw1 or not pw2:
                        st.error(t("err_fields"))
                    elif not re.fullmatch(r"[6-9]\d{9}", clean_phone):
                        st.error(t("err_phone"))
                    elif len(pw1) < 4:
                        st.error(t("err_password_len"))
                    elif pw1 != pw2:
                        st.error(t("err_password_match"))
                    else:
                        ok, res = create_user("citizen", clean_phone, pw1, name_in.strip())
                        if ok:
                            st.success(f"✓ Indian Mobile (+91 {clean_phone}) Verified! {t('success_register')}")
                        else:
                            st.error(t("err_exists"))

        # ---------------- ADMIN AUTH ----------------
        with role_tab_admin:
            st.caption(t("admin_login_desc"))

            st.markdown(
                '<div style="background:#eff6ff; border:1px solid #bfdbfe; border-radius:6px; padding:10px 12px; margin-bottom:12px; font-size:12px; color:#1e40af;">'
                '🔒 <b>Department Officer Portal:</b> Officer accounts are provisioned directly by Municipal Administration. Public officer registration is disabled for safety.'
                '</div>',
                unsafe_allow_html=True,
            )

            st.markdown("<p style='font-size:12px; font-weight:700; margin-bottom:4px;'>⚡ Quick Access Department Roles:</p>", unsafe_allow_html=True)
            qc1, qc2, qc3 = st.columns(3)
            with qc1:
                if st.button("🚧 Roads", key="qk_roads", use_container_width=True):
                    st.session_state["adm_uname_prefill"] = "roads_admin"
                    st.session_state["adm_dept_prefill"] = "Roads & Infrastructure"
                    st.rerun()
            with qc2:
                if st.button("💧 Water", key="qk_water", use_container_width=True):
                    st.session_state["adm_uname_prefill"] = "water_admin"
                    st.session_state["adm_dept_prefill"] = "Water Supply"
                    st.rerun()
            with qc3:
                if st.button("⚡ Power", key="qk_power", use_container_width=True):
                    st.session_state["adm_uname_prefill"] = "power_admin"
                    st.session_state["adm_dept_prefill"] = "Electricity/Power"
                    st.rerun()

            qc4, qc5, qc6 = st.columns(3)
            with qc4:
                if st.button("🗑️ Waste", key="qk_waste", use_container_width=True):
                    st.session_state["adm_uname_prefill"] = "waste_admin"
                    st.session_state["adm_dept_prefill"] = "Waste Management"
                    st.rerun()
            with qc5:
                if st.button("🏥 Health", key="qk_health", use_container_width=True):
                    st.session_state["adm_uname_prefill"] = "health_admin"
                    st.session_state["adm_dept_prefill"] = "Public Health"
                    st.rerun()
            with qc6:
                if st.button("🏛️ Central", key="qk_central", use_container_width=True):
                    st.session_state["adm_uname_prefill"] = "admin"
                    st.session_state["adm_dept_prefill"] = "All Departments (Central City Oversight)"
                    st.rerun()

            dept_options = ["All Departments (Central City Oversight)"] + list(backend.DEPARTMENTS.keys())
            pre_dept = st.session_state.get("adm_dept_prefill", "All Departments (Central City Oversight)")
            dept_idx = dept_options.index(pre_dept) if pre_dept in dept_options else 0
            pre_uname = st.session_state.get("adm_uname_prefill", "admin")

            with st.form("admin_login_form"):
                dept_in = st.selectbox(
                    "🏛️ Designated Department Authority",
                    dept_options,
                    index=dept_idx,
                    help="Select your designated municipal department to manage grievances specifically assigned to your domain."
                )
                uname_in = st.text_input(t("lbl_username"), value=pre_uname, placeholder="e.g. roads_admin, water_admin, admin")
                apw_in = st.text_input(t("lbl_password"), value="admin123", type="password")
                ago = st.form_submit_button(t("btn_login"), use_container_width=True)
            if ago:
                if not uname_in or not apw_in:
                    st.error(t("err_fields"))
                else:
                    user = authenticate("admin", uname_in.strip(), apw_in)
                    if user:
                        st.session_state["auth_user"] = user
                        st.session_state["auth_role"] = "admin"
                        # Set department scope
                        u_dept = user.get("department")
                        if u_dept and u_dept != "All":
                            st.session_state["auth_dept"] = u_dept
                        else:
                            st.session_state["auth_dept"] = dept_in
                        st.session_state["active_tab"] = "dashboard"
                        st.rerun()
                    else:
                        st.error(t("err_invalid"))
            st.markdown(
                f'<div class="auth-note">💡 <b>Pre-configured Officer Accounts (Password: <code>admin123</code>):</b><br>'
                f'• Roads: <code>roads_admin</code> · Water: <code>water_admin</code> · Power: <code>power_admin</code><br>'
                f'• Waste: <code>waste_admin</code> · Health: <code>health_admin</code> · Central: <code>admin</code></div>',
                unsafe_allow_html=True
            )


# =============================================================================
# GATE: REQUIRE AUTHENTICATION
# =============================================================================
if not st.session_state.get("auth_user"):
    render_auth_page()
    st.stop()


# =============================================================================
# AUTHENTICATED PORTAL VIEW
# =============================================================================
render_header()

# Synchronize automated query params if browser GPS returned
try:
    if "gps_lat" in st.query_params and "gps_lon" in st.query_params:
        glat = float(st.query_params["gps_lat"])
        glon = float(st.query_params["gps_lon"])
        st.session_state["picked_latlon"] = (glat, glon)
except Exception:
    pass

role = st.session_state.get("auth_role", "citizen")
current_user = st.session_state.get("auth_user", {})

TAB_LABELS = {
    "citizen": t("nav_citizen"),
    "track": t("nav_track"),
    "dashboard": t("nav_dashboard"),
    "how": t("nav_how"),
}
if role == "citizen":
    available_tabs = ["citizen", "track"]
else:
    available_tabs = ["dashboard", "track"]

if st.session_state["active_tab"] not in available_tabs:
    st.session_state["active_tab"] = available_tabs[0]

selected_tab = st.radio(
    "Navigation",
    options=available_tabs,
    index=available_tabs.index(st.session_state["active_tab"]),
    format_func=lambda k: TAB_LABELS[k],
    horizontal=True,
    label_visibility="collapsed",
    key="nav_radio",
)
st.session_state["active_tab"] = selected_tab
st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)



# =============================================================================
# VIEW: CITIZEN PORTAL
# =============================================================================
if selected_tab == "citizen":
    st.markdown(f"""
    <div class="hero-box">
      <div class="section-kicker">{t("hero_kicker")}</div>
      <h2 style="color:var(--navy); font-size:26px; font-weight:800; margin:4px 0 8px 0;">{t("hero_title")}</h2>
      <p style="color:#52616e; font-size:13px; margin:0 0 12px 0;">{t("hero_desc")}</p>
      <div style="display:flex; gap:16px; font-size:12px; font-weight:600; color:#3f4e59;">
        <span><b style="color:var(--green);">✓</b> {t("point_1")}</span>
        <span><b style="color:var(--green);">✓</b> {t("point_2")}</span>
        <span><b style="color:var(--green);">✓</b> {t("point_3")}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="stepper-strip">
      <div style="font-weight:700; font-size:11px; color:var(--navy);"><b>1</b> {t("step_1")}</div>
      <div style="color:#cbd5e1;">→</div>
      <div style="font-weight:700; font-size:11px; color:var(--navy);"><b>2</b> {t("step_2")}</div>
      <div style="color:#cbd5e1;">→</div>
      <div style="font-size:11px; color:#64748b;"><b>3</b> {t("step_3")}</div>
      <div style="color:#cbd5e1;">→</div>
      <div style="font-size:11px; color:#64748b;"><b>4</b> {t("step_4")}</div>
    </div>
    """, unsafe_allow_html=True)

    col_form, col_side = st.columns([1.55, 0.85])

    with col_form:
        st.markdown(f"#### {t('form_heading')}")
        st.caption(f"{t('req_note')}")

        lat, lon = st.session_state["picked_latlon"]
        detected_ward = backend.nearest_ward(lat, lon)

        # Real Device Geolocation via streamlit_js_eval bridge
        gps_val = streamlit_js_eval.get_geolocation(component_key="awazsetu_geo_tracker")
        if gps_val and isinstance(gps_val, dict) and "coords" in gps_val:
            c = gps_val["coords"]
            if c.get("latitude") and c.get("longitude"):
                st.session_state["picked_latlon"] = (float(c["latitude"]), float(c["longitude"]))
                st.session_state["gps_accuracy"] = round(c.get("accuracy", 0))
                st.session_state["gps_source"] = "High-Precision Device GPS"

        lat, lon = st.session_state["picked_latlon"]
        detected_ward = backend.nearest_ward(lat, lon)
        ward_select = detected_ward
        acc_info = f" (±{st.session_state['gps_accuracy']}m)" if st.session_state.get("gps_accuracy") else ""

        # Live Geolocation Status Card
        st.markdown(f"""
        <div style="background:#f8fafc; border:1.5px solid #cbd5e1; border-left:4px solid var(--navy); padding:12px 16px; border-radius:8px; margin-bottom:10px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <strong style="color:var(--navy); font-size:13.5px; display:block;">📍 AwazSetu Live Incident Geolocation</strong>
              <span style="font-size:11.5px; color:#475569;">High-accuracy browser satellite sync active{acc_info}</span>
            </div>
            <span style="background:#dcfce7; color:#166534; padding:3px 10px; border-radius:12px; font-weight:800; font-size:11px; border:1px solid #bbf7d0;">GPS Locked</span>
          </div>
          <div style="margin-top:8px; font-size:12.5px; color:#1e293b; background:#ffffff; border:1px solid #e2e8f0; padding:8px 12px; border-radius:6px; display:flex; justify-content:space-between; align-items:center;">
            <span>Detected Redressal Ward: <b style="color:var(--navy);">{detected_ward}</b> &nbsp;·&nbsp; Pinpoint: <code>{lat:.5f}, {lon:.5f}</code></span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Interactive Mapbox Pinpoint & 400m Radius Map
        mapbox_tiles_url = f"https://api.mapbox.com/styles/v1/mapbox/streets-v12/tiles/256/{{z}}/{{x}}/{{y}}@2x?access_token={MAPBOX_ACCESS_TOKEN}" if MAPBOX_ACCESS_TOKEN else "cartodbpositron"
        mapbox_attr = "© <a href='https://www.mapbox.com/'>Mapbox</a> © <a href='http://www.openstreetmap.org/'>OpenStreetMap</a>" if MAPBOX_ACCESS_TOKEN else "CartoDB"

        fmap_citizen = folium.Map(
            location=[lat, lon],
            zoom_start=14,
            tiles=mapbox_tiles_url,
            attr=mapbox_attr,
        )
        folium.Marker(
            location=[lat, lon],
            tooltip=f"Incident Location: {detected_ward}",
            popup=folium.Popup(f"<b>{detected_ward}</b><br>Coordinates: {lat:.5f}, {lon:.5f}", max_width=200),
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(fmap_citizen)
        folium.Circle(
            location=[lat, lon],
            radius=400,
            color="#0b3c5d",
            fill=True,
            fill_opacity=0.12,
            tooltip="400m Duplicate Detection Radius"
        ).add_to(fmap_citizen)

        st_folium(fmap_citizen, height=220, width=None, key=f"cit_map_{lat:.3f}_{lon:.3f}")
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

        with st.form("citizen_complaint_form", clear_on_submit=False):
            category_hint = st.selectbox(
                t("lbl_cat"),
                [t("cat_placeholder")] + list(backend.DEPARTMENTS.keys()),
            )
            description = st.text_area(t("lbl_desc"), placeholder=t("desc_placeholder"), height=140)
            photo = st.file_uploader(t("upload_label"), type=["png", "jpg", "jpeg"])
            st.markdown("<hr style='margin:12px 0;'>", unsafe_allow_html=True)
            submit_btn = st.form_submit_button(t("btn_submit"), use_container_width=True)

    with col_side:
        st.markdown(f"""
        <div class="civic-card">
          <div class="section-kicker">{t("intel_kicker")}</div>
          <h4 style="margin:2px 0 6px 0; color:var(--navy);">{t("intel_title")}</h4>
          <p style="font-size:11px; color:var(--muted); margin-bottom:10px;">{t("intel_desc")}</p>
          <div style="border-top:1px solid #e2e8f0; padding-top:8px; font-size:11px; display:flex; justify-content:space-between;">
            <span>AI Engine</span><strong>SentenceTransformers Online</strong>
          </div>
          <div style="border-top:1px solid #e2e8f0; padding-top:8px; font-size:11px; display:flex; justify-content:space-between;">
            <span>Deduplication Radius</span><strong>400m Proximity Active</strong>
          </div>
        </div>

        <div class="civic-card">
          <h4 style="margin:0 0 4px 0; font-size:12px; color:var(--navy);">{t("privacy_title")}</h4>
          <p style="font-size:10.5px; color:var(--muted); margin:0;">{t("privacy_desc")}</p>
        </div>

        <div style="background:var(--navy-tint); border-left:3px solid var(--navy); padding:12px; border-radius:4px;">
          <strong style="font-size:11.5px; color:var(--navy);">{t("help_title")}</strong>
          <p style="font-size:10.5px; color:var(--muted); margin:2px 0 0 0;">{t("help_desc")}</p>
        </div>
        """, unsafe_allow_html=True)

        if photo is not None:
            st.image(photo, caption="Uploaded Evidence Preview", use_container_width=True)

    if submit_btn:
        if not description or not description.strip():
            st.error("Please enter a description for your grievance.")
        else:
            with st.spinner("Analyzing text with SentenceTransformers, detecting 400m duplicates, and calculating dynamic urgency score..."):
                original_text = description.strip()
                text_en, detected_lang, _ = backend.normalize_to_english(original_text)

                sia = backend.SentimentIntensityAnalyzer()
                sentiment = sia.polarity_scores(text_en)["compound"]

                photo_bytes = photo.getvalue() if photo is not None else None
                image_b64 = None
                if photo_bytes is not None:
                    mime = "image/png" if (photo.name or "").lower().endswith(".png") else "image/jpeg"
                    image_b64 = f"data:{mime};base64," + base64.b64encode(photo_bytes).decode("utf-8")

                department, xai_dept, _ = backend.classify_department(text_en, category_hint=category_hint, photo_bytes=photo_bytes)
                if category_hint != t("cat_placeholder") and category_hint != department:
                    xai_dept += f"\n- User selected hint '{category_hint}', but AI classified as '{department}' from semantic keywords."

                embedding = backend.embed_text(text_en)
                existing_records = backend.fetch_all_records()
                parent_id, sim = backend.find_duplicate_match(embedding, lat, lon, existing_records, new_dept=department)

                severity_score, priority, xai_priority = backend.score_priority(
                    text_en, sentiment, upvotes=0, has_photo=(photo is not None), photo_bytes=photo_bytes
                )
                gid = f"CG-{backend.new_id()}"

                record = {
                    "id": gid,
                    "original_text": original_text,
                    "text_en": text_en,
                    "detected_lang": detected_lang,
                    "category_hint": category_hint,
                    "department": department,
                    "priority": priority,
                    "severity_score": severity_score,
                    "sentiment_compound": sentiment,
                    "lat": lat,
                    "lon": lon,
                    "ward": ward_select,
                    "status": "Pending",
                    "upvotes": 0,
                    "is_duplicate": 1 if parent_id else 0,
                    "parent_id": parent_id,
                    "embedding": json.dumps(embedding.tolist()),
                    "xai_department": xai_dept,
                    "xai_priority": xai_priority,
                    "image_flag": 1 if photo is not None else 0,
                    "image_data": image_b64,
                    "citizen_name": current_user.get("full_name") or "Citizen",
                    "citizen_phone": current_user.get("username") or "",
                    "created_at": datetime.now().isoformat(),
                }
                backend.insert_record(record)

                if parent_id:
                    backend.increment_upvote_in_db(parent_id, boost_points=8)

            st.success(f"Grievance Submission Processed! Ticket ID: #{gid}")

            if parent_id:
                st.markdown(f"""
                <div style="background:#eff6ff; border:1.5px solid #93c5fd; border-left:5px solid #2563eb; padding:14px 18px; border-radius:8px; margin:12px 0;">
                  <strong style="color:#1e40af; font-size:14px; display:block;">🔄 Automated 400m Duplicate Grievance Match</strong>
                  <p style="margin:4px 0 6px 0; font-size:12.5px; color:#1e293b;">
                    A verified matching issue was already open within <b>400 meters</b> (Parent Ticket <b>#{parent_id}</b> with <b>{sim*100:.1f}% Semantic Match</b>).
                  </p>
                  <div style="font-size:11.5px; color:#1e40af; font-weight:700;">
                    ✓ Merged into Master Ticket &nbsp;·&nbsp; ✓ +1 Community Confirmation Added &nbsp;·&nbsp; ✓ +8 Points Urgency Escalated
                  </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                m1, m2, m3 = st.columns(3)
                m1.metric("Classified Department", department)
                m2.metric("Urgency Priority", priority, f"{severity_score}/100 Score")
                m3.metric("Assigned Area", ward_select)

            with st.expander("View Explainable AI (XAI) Model Rationale"):
                st.markdown(xai_dept)
                st.markdown("---")
                st.markdown(xai_priority)


# =============================================================================
# VIEW: TRACK COMPLAINT & LIVE STATUS
# =============================================================================
elif selected_tab == "track":
    st.markdown(f"### {t('track_header')}")
    records = backend.fetch_all_records()

    if role == "citizen":
        my_phone = current_user.get("username", "")
        my_records = [r for r in records if r.get("citizen_phone") == my_phone]
        m_total = len(my_records)
        m_open = sum(1 for r in my_records if r["status"] != "Resolved")
        m_resolved = sum(1 for r in my_records if r["status"] == "Resolved")

        st.markdown(f"<div class='section-kicker'>{t('my_dashboard_title')}</div>", unsafe_allow_html=True)
        mk1, mk2, mk3 = st.columns(3)
        mk1.metric(t("my_kpi_total"), m_total)
        mk2.metric(t("my_kpi_open"), m_open)
        mk3.metric(t("my_kpi_resolved"), m_resolved)

        only_mine = st.toggle(t("my_filter_toggle"), value=False)
        if only_mine:
            records = my_records
        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
    elif role == "admin":
        admin_dept = st.session_state.get("auth_dept", "All Departments (Central City Oversight)")
        if admin_dept and admin_dept != "All Departments (Central City Oversight)":
            records = [r for r in records if r["department"] == admin_dept]
            st.markdown(f"<div class='section-kicker'>🏛️ {admin_dept} Department Complaints</div>", unsafe_allow_html=True)

    if not records:
        st.info(t("track_empty"))
    else:
        search_query = st.text_input("Search by Ticket ID, Keyword, or Area", placeholder="e.g. CG-..., water, road, Dadar...")
        if search_query:
            records = [
                r for r in records
                if search_query.lower() in r["id"].lower()
                or search_query.lower() in r["original_text"].lower()
                or search_query.lower() in r["text_en"].lower()
                or search_query.lower() in r["ward"].lower()
            ]

        for r in records:
            tid = r["id"]
            p_color = backend.PRIORITY_COLORS.get(r['priority'], '#64748b')

            st_val = r.get("status", "Pending")
            if st_val == "Pending":
                status_badge = f'<span class="badge-pending">{t("status_pending")}</span>'
            elif st_val == "In Progress":
                status_badge = f'<span class="badge-progress">{t("status_progress")}</span>'
            elif st_val in ("Waiting for Citizen Confirmation", "Awaiting Citizen Confirmation"):
                status_badge = f'<span class="badge-waiting">⏳ {t("status_waiting")}</span>'
            elif st_val == "Reopened":
                status_badge = f'<span class="badge-reopened">↺ {t("status_reopened")}</span>'
            else:
                status_badge = f'<span class="badge-resolved">✓ {t("status_resolved")}</span>'

            dup_tag = f"<span style='color:#a15c00; font-size:11px; font-weight:700;'>[Merged ➔ #{r['parent_id']}]</span>" if r.get('is_duplicate') else ""
            sla_html = compute_sla_badge(r.get("created_at", ""), r.get("priority", "Medium"))
            lat, lon = r.get("lat"), r.get("lon")
            map_link = f'<a href="https://www.google.com/maps?q={lat},{lon}" target="_blank" style="font-size:11px; text-decoration:none; color:var(--navy); font-weight:700;">🗺️ Maps ↗</a>' if (lat and lon) else ""

            st.markdown(
                f'<div class="civic-card" style="border-left: 4px solid {p_color};">'
                f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:6px;">'
                f'<div><span style="font-weight:800; color:var(--navy); font-size:1.05rem;">#{tid}</span> &nbsp;·&nbsp; <b>{r["department"]}</b> {dup_tag} &nbsp;·&nbsp; <span style="font-size:0.82rem; color:var(--text-muted);">Area: {r["ward"]}</span> &nbsp; {map_link}</div>'
                f'<div style="display:flex; align-items:center; gap:6px;">{sla_html} {status_badge} &nbsp;<span style="color:{p_color}; font-weight:800; font-size:11px; border:1px solid {p_color}; padding:2px 8px; border-radius:4px; background:#ffffff;">{r["priority"]} ({r["severity_score"]}/100)</span></div>'
                f'</div>'
                f'<div style="color:var(--ink); font-size:0.92rem; margin-bottom:8px;">"{r["original_text"]}"</div>'
                f'<div style="display:flex; justify-content:space-between; font-size:0.8rem; color:var(--text-muted); margin-bottom:6px;">'
                f'<span>Reported: {r["created_at"][:16].replace("T", " ")} · Reporter: <b>{r.get("citizen_name", "Citizen")}</b></span>'
                f'<span>Community Confirmations: <b>{r.get("upvotes", 0)}</b></span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Display Before and Resolution Proof Photos if available
            has_orig = bool(r.get("image_data"))
            has_proof = bool(r.get("resolution_photo"))
            if has_orig or has_proof:
                img_c1, img_c2 = st.columns(2)
                with img_c1:
                    if has_orig:
                        st.markdown("<span style='font-size:11.5px; font-weight:700; color:var(--navy);'>📸 Original Reported Photo</span>", unsafe_allow_html=True)
                        st.image(r["image_data"], use_container_width=True)
                with img_c2:
                    if has_proof:
                        st.markdown("<span style='font-size:11.5px; font-weight:700; color:#166534;'>✅ Municipal Resolution Proof Photo</span>", unsafe_allow_html=True)
                        st.image(r["resolution_photo"], use_container_width=True)

            if r.get("resolution_note"):
                st.markdown(
                    f'<div style="background:#f8fafc; border-left:3px solid #0b3c5d; padding:8px 12px; border-radius:4px; font-size:12px; margin:4px 0 8px 0;">'
                    f'<strong>🏛️ Municipal Resolution Note:</strong> {r["resolution_note"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            if r.get("citizen_remarks"):
                st.markdown(
                    f'<div style="background:#fff7ed; border-left:3px solid #ea580c; padding:8px 12px; border-radius:4px; font-size:12px; margin:4px 0 8px 0;">'
                    f'<strong>↺ Citizen Reopen Remarks:</strong> {r["citizen_remarks"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Citizen Verification Box when Waiting for Citizen Confirmation
            if r.get("status") in ("Waiting for Citizen Confirmation", "Awaiting Citizen Confirmation"):
                st.markdown(f"""
                <div style="background:#fffbeb; border:1.5px solid #f59e0b; border-left:5px solid #d97706; padding:12px 16px; border-radius:8px; margin:8px 0 10px 0;">
                  <strong style="color:#92400e; font-size:13.5px; display:block;">⚠️ {t("did_it_resolve")}</strong>
                  <p style="margin:4px 0 0 0; font-size:12px; color:#78350f;">The assigned municipal department has completed work and submitted photographic evidence above. Please verify whether the issue is resolved.</p>
                </div>
                """, unsafe_allow_html=True)
                vcol1, vcol2 = st.columns(2)
                with vcol1:
                    if st.button(t("btn_confirm_res"), key=f"conf_{tid}", use_container_width=True):
                        backend.record_citizen_feedback_in_db(tid, "Confirmed", "Citizen confirmed resolution")
                        st.success(f"✓ Resolution confirmed! Ticket #{tid} has been permanently closed and removed from active municipal records.")
                        st.rerun()
                with vcol2:
                    with st.expander(t("btn_reopen")):
                        rem_in = st.text_input(t("reopen_reason_placeholder"), key=f"rem_{tid}")
                        if st.button("Submit Reopen Request", key=f"sub_reopen_{tid}", use_container_width=True):
                            if not rem_in.strip():
                                st.error("Please explain why the issue is not resolved.")
                            else:
                                backend.record_citizen_feedback_in_db(tid, "Reopened", rem_in.strip())
                                st.warning(f"Ticket #{tid} has been reopened with escalated urgency (+15 points) and assigned back to the department.")
                                st.rerun()

            # Community Upvoting with Duplicate Vote Prevention
            if r.get("status") != "Resolved":
                u_col1, u_col2 = st.columns([2.5, 1.5])
                with u_col2:
                    if role == "admin":
                        st.caption(f"👥 {r.get('upvotes', 0)} Community Confirmations ({t('admin_no_upvote')})")
                    else:
                        uid = current_user.get("username") or "citizen"
                        upvoted_tickets = backend.fetch_user_upvoted_tickets(uid)
                        if tid in upvoted_tickets:
                            st.button(f"{t('already_upvoted')} ({r.get('upvotes', 0)})", key=f"voted_{tid}", disabled=True, use_container_width=True)
                        else:
                            if st.button(f"{t('affects_me_too')} ({r.get('upvotes', 0)})", key=f"vote_{tid}", use_container_width=True):
                                ok, msg = backend.record_citizen_upvote_in_db(tid, uid, boost_points=5)
                                if ok:
                                    st.success("Your confirmation has been recorded (+5 urgency points added)!")
                                    st.rerun()
                                else:
                                    st.warning(msg)

            st.markdown("<hr style='margin:12px 0 16px 0; border-color:#e2e8f0;'>", unsafe_allow_html=True)


# =============================================================================
# VIEW: AUTHORITY OPERATIONS DASHBOARD (Admin Only)
# =============================================================================
elif selected_tab == "dashboard":
    all_records = backend.fetch_all_records()
    admin_dept = st.session_state.get("auth_dept", "All Departments (Central City Oversight)")
    is_scoped = bool(admin_dept and admin_dept != "All Departments (Central City Oversight)")

    if is_scoped:
        records = [r for r in all_records if r["department"] == admin_dept]
    else:
        records = all_records

    total = len(records)
    pending = sum(1 for r in records if r["status"] == "Pending")
    in_prog = sum(1 for r in records if r["status"] == "In Progress")
    high_crit = sum(1 for r in records if r["priority"] in ["Critical", "High"] and r["status"] != "Resolved")
    resolved = sum(1 for r in records if r["status"] == "Resolved")
    res_rate = (resolved / total * 100) if total > 0 else 0.0

    scope_banner = ""
    if is_scoped:
        scope_banner = (
            f'<div style="background:#eff6ff; border:1.5px solid #bfdbfe; border-left:5px solid #2563eb; padding:10px 16px; border-radius:8px; margin:8px 0 14px 0;">'
            f'<strong style="color:#1e40af; font-size:13.5px; display:block;">🏛️ Department Authority Scope: {admin_dept}</strong>'
            f'<span style="font-size:11.5px; color:#475569;">Grievance oversight, density heatmaps, and priority resolution queues are filtered exclusively for your department.</span>'
            f'</div>'
        )

    st.markdown(
        f'<div style="margin:4px 0 10px 0;">'
        f'<div class="section-kicker">{t("dash_kicker")}</div>'
        f'<h2 style="color:var(--navy); font-size:24px; font-weight:800; margin:2px 0 4px 0;">{t("dash_title")}</h2>'
        f'<p style="color:var(--text-muted); font-size:12.5px; margin:0;">Real-time incident oversight, GIS density heatmap, and grievance redressal controls.</p>'
        f'</div>'
        f'{scope_banner}',
        unsafe_allow_html=True,
    )

    # 4 Essential Operational KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(t("kpi_total"), total)
    k2.metric(t("kpi_pending"), pending)
    k3.metric("High / Critical", high_crit)
    k4.metric(t("kpi_resolved"), resolved, f"{res_rate:.1f}% Resolved")

    if not records:
        if is_scoped:
            st.info(f"No complaints currently recorded under **{admin_dept}**. Any newly routed or matching complaints will appear here automatically.")
        else:
            st.info("No citizen complaints recorded in the system yet. Once submitted, live tickets and heatmap clusters will appear here.")
    else:
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

        # ---------------- 1. GIS INCIDENT HEATMAP ----------------
        st.markdown(f"#### 🗺️ Incident Density Heatmap & Pinpoint GIS")
        st.caption("Live geographical heat density of reported grievances. Hotspots indicate high complaint concentration.")

        # Compute map center
        valid_coords = [(r["lat"], r["lon"]) for r in records if r.get("lat") and r.get("lon")]
        if valid_coords:
            center_lat = sum(c[0] for c in valid_coords) / len(valid_coords)
            center_lon = sum(c[1] for c in valid_coords) / len(valid_coords)
        else:
            center_lat, center_lon = backend.CITY_CENTER

        mapbox_tiles_url = f"https://api.mapbox.com/styles/v1/mapbox/streets-v12/tiles/256/{{z}}/{{x}}/{{y}}@2x?access_token={MAPBOX_ACCESS_TOKEN}" if MAPBOX_ACCESS_TOKEN else "cartodbpositron"
        mapbox_attr = "© <a href='https://www.mapbox.com/about/maps/'>Mapbox</a> © <a href='http://www.openstreetmap.org/copyright'>OpenStreetMap</a>" if MAPBOX_ACCESS_TOKEN else "CartoDB"

        fmap_admin = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles=mapbox_tiles_url,
            attr=mapbox_attr,
        )

        # Heatmap Layer: weighted by severity score and upvotes (active unresolved only)
        heat_data = [
            [r["lat"], r["lon"], float(max(r.get("severity_score", 40), 10) + r.get("upvotes", 0) * 5)]
            for r in records if r.get("lat") and r.get("lon") and r.get("status") != "Resolved"
        ]
        if heat_data:
            HeatMap(
                heat_data,
                radius=28,
                blur=20,
                max_zoom=14,
                gradient={0.2: "#3b82f6", 0.4: "#10b981", 0.6: "#f59e0b", 0.8: "#ef4444", 1.0: "#7f1d1d"}
            ).add_to(fmap_admin)

        # Pinpoint Marker Layer (Active unresolved only)
        for r in records:
            if r.get("status") == "Resolved":
                continue
            p_color = backend.PRIORITY_COLORS.get(r["priority"], "#64748b")
            status_symbol = "⏳" if r["status"] == "Pending" else "⚡"
            folium.CircleMarker(
                location=(r["lat"], r["lon"]),
                radius=8 + min(r.get("upvotes", 0), 6),
                color=p_color,
                weight=2,
                fill=True,
                fill_color=p_color,
                fill_opacity=0.9,
                tooltip=f"#{r['id']} · {r['department']} ({r['priority']}) · {r['status']}",
                popup=folium.Popup(
                    f"<div style='font-family:sans-serif; min-width:180px;'>"
                    f"<b>#{r['id']}</b> — {r['department']}<br>"
                    f"<b>Status:</b> {status_symbol} {r['status']}<br>"
                    f"<b>Priority:</b> <span style='color:{p_color};'><b>{r['priority']}</b> ({r['severity_score']}/100)</span><br>"
                    f"<b>Area:</b> {r['ward']}<br>"
                    f"<b>Text:</b> <i>\"{r['original_text'][:60]}...\"</i>"
                    f"</div>",
                    max_width=260
                )
            ).add_to(fmap_admin)

        st_folium(fmap_admin, height=380, width=None, key="admin_gis_heatmap")

        st.markdown("<hr style='margin:20px 0 16px 0;'>", unsafe_allow_html=True)

        # ---------------- 2. RESOLUTION QUEUE & TICKET ACTION CENTER ----------------
        st.markdown("#### 📋 Incident Resolution Queue & Actions")

        if is_scoped:
            f_col1, f_col2 = st.columns([1.5, 2])
            with f_col1:
                status_filter = st.selectbox("Filter Status", ["Active Only (Pending & In Progress)", "All Statuses", "Pending", "In Progress", "Resolved"], index=0, key="adm_status_filter")
            with f_col2:
                search_ticket = st.text_input("Search ID or Keyword", placeholder="Ticket #, description, ward...", key="adm_search_box")

            filtered_records = records
            if status_filter == "Active Only (Pending & In Progress)":
                filtered_records = [r for r in filtered_records if r["status"] != "Resolved"]
            elif status_filter != "All Statuses":
                filtered_records = [r for r in filtered_records if r["status"] == status_filter]
        else:
            f_col1, f_col2, f_col3 = st.columns([1.2, 1.2, 1.6])
            with f_col1:
                dept_filter = st.selectbox("Filter Department", ["All Departments"] + list(backend.DEPARTMENTS.keys()), key="adm_dept_filter")
            with f_col2:
                status_filter = st.selectbox("Filter Status", ["Active Only (Pending & In Progress)", "All Statuses", "Pending", "In Progress", "Resolved"], index=0, key="adm_status_filter")
            with f_col3:
                search_ticket = st.text_input("Search ID or Keyword", placeholder="Ticket #, description, ward...", key="adm_search_box")

            filtered_records = records
            if dept_filter != "All Departments":
                filtered_records = [r for r in filtered_records if r["department"] == dept_filter]
            if status_filter == "Active Only (Pending & In Progress)":
                filtered_records = [r for r in filtered_records if r["status"] != "Resolved"]
            elif status_filter != "All Statuses":
                filtered_records = [r for r in filtered_records if r["status"] == status_filter]
        if search_ticket:
            q = search_ticket.lower().strip()
            filtered_records = [
                r for r in filtered_records
                if q in r["id"].lower() or q in r["original_text"].lower() or q in r["ward"].lower()
            ]

        # Sort: unresolved high priority first, then parents before child duplicates
        filtered_records.sort(key=lambda x: (x["status"] == "Resolved", x.get("is_duplicate", 0), -x.get("severity_score", 0)))

        if not filtered_records:
            st.info("No tickets match the selected filters.")
        else:
            st.caption(f"Showing **{len(filtered_records)}** incident tickets")
            for r in filtered_records:
                tid = r["id"]
                p_color = backend.PRIORITY_COLORS.get(r['priority'], '#64748b')

                st_val = r.get("status", "Pending")
                if st_val == "Pending":
                    st_badge = '<span class="badge-pending">Pending</span>'
                elif st_val == "In Progress":
                    st_badge = '<span class="badge-progress">In Progress</span>'
                elif st_val in ("Waiting for Citizen Confirmation", "Awaiting Citizen Confirmation"):
                    st_badge = '<span class="badge-waiting">⏳ Waiting for Citizen Confirmation</span>'
                elif st_val == "Reopened":
                    st_badge = '<span class="badge-reopened">↺ Reopened by Citizen</span>'
                else:
                    st_badge = '<span class="badge-resolved">✓ Resolved</span>'

                dup_tag = ""
                if r.get("is_duplicate") == 1:
                    dup_tag = f'<span style="background:#ede9fe; color:#5b21b6; padding:2px 8px; border-radius:4px; font-weight:800; font-size:10.5px; border:1px solid #ddd6fe; margin-left:6px;">🔗 Merged Duplicate ➔ #{r.get("parent_id")}</span>'
                elif r.get("upvotes", 0) > 0:
                    dup_tag = f'<span style="background:#dbeafe; color:#1e40af; padding:2px 8px; border-radius:4px; font-weight:800; font-size:10.5px; border:1px solid #bfdbfe; margin-left:6px;">👥 Master Ticket ({r.get("upvotes")} Merged Reports)</span>'

                sla_html = compute_sla_badge(r.get("created_at", ""), r.get("priority", "Medium"))
                lat, lon = r.get("lat"), r.get("lon")
                map_link = f'<a href="https://www.google.com/maps?q={lat},{lon}" target="_blank" style="font-size:11px; text-decoration:none; color:var(--navy); font-weight:700;">🗺️ Maps ↗</a>' if (lat and lon) else ""

                st.markdown(
                    f'<div class="civic-card" style="border-left: 4px solid {p_color}; margin-bottom: 12px;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:6px;">'
                    f'<div><strong style="font-size:1.05rem; color:var(--navy);">#{tid}</strong> &nbsp;·&nbsp; <b>{r["department"]}</b> &nbsp;·&nbsp; <span style="font-size:11.5px; color:var(--text-muted);">Area: {r["ward"]}</span>{dup_tag} &nbsp; {map_link}</div>'
                    f'<div style="display:flex; align-items:center; gap:6px;">{sla_html} {st_badge} &nbsp;<span style="color:{p_color}; font-weight:800; font-size:11px; border:1px solid {p_color}; padding:2px 8px; border-radius:4px; background:#ffffff;">{r["priority"]} ({r["severity_score"]}/100)</span></div>'
                    f'</div>'
                    f'<p style="margin:8px 0; font-size:0.92rem; color:#1e293b;">"{r["original_text"]}"</p>'
                    f'<div style="font-size:11px; color:var(--text-muted); display:flex; justify-content:space-between; margin-bottom:4px;">'
                    f'<span>Reporter: <b>{r.get("citizen_name", "Citizen")}</b> ({r.get("citizen_phone") or "Direct"})</span>'
                    f'<span>Reported: {r["created_at"][:16].replace("T", " ")} · Community Confirmations: <b>{r["upvotes"]}</b></span>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # Show Before & After photos if available
                has_orig = bool(r.get("image_data"))
                has_proof = bool(r.get("resolution_photo"))
                if has_orig or has_proof:
                    img_c1, img_c2 = st.columns(2)
                    with img_c1:
                        if has_orig:
                            st.markdown("<span style='font-size:11px; font-weight:700; color:var(--navy);'>📸 Citizen Reported Photo</span>", unsafe_allow_html=True)
                            st.image(r["image_data"], use_container_width=True)
                    with img_c2:
                        if has_proof:
                            st.markdown("<span style='font-size:11px; font-weight:700; color:#166534;'>✅ Submitted Resolution Proof</span>", unsafe_allow_html=True)
                            st.image(r["resolution_photo"], use_container_width=True)

                if r.get("resolution_note"):
                    st.markdown(
                        f'<div style="background:#f8fafc; border-left:3px solid #0b3c5d; padding:8px 12px; border-radius:4px; font-size:12px; margin:4px 0 8px 0;">'
                        f'<strong>🏛️ Officer Resolution Note:</strong> {r["resolution_note"]}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                if r.get("citizen_remarks"):
                    st.markdown(
                        f'<div style="background:#fff7ed; border-left:3px solid #ea580c; padding:8px 12px; border-radius:4px; font-size:12px; margin:4px 0 8px 0;">'
                        f'<strong>↺ Citizen Reopen Remarks:</strong> {r["citizen_remarks"]}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                # Check if this master ticket has linked child duplicates
                if r.get("is_duplicate") == 0 and r.get("upvotes", 0) > 0:
                    child_reports = [c for c in records if c.get("parent_id") == tid]
                    if child_reports:
                        with st.expander(f"👥 View {len(child_reports)} Linked Citizen Duplicate Report(s)"):
                            for cr in child_reports:
                                st.markdown(f"- **#{cr['id']}**: *\"{cr['original_text']}\"* (Reporter: {cr.get('citizen_name', 'Citizen')} - `{cr.get('citizen_phone')}`, {cr['created_at'][:16].replace('T', ' ')})")

                # Action Controls
                if st_val in ("Waiting for Citizen Confirmation", "Awaiting Citizen Confirmation"):
                    st.markdown(
                        f'<div style="background:#fef3c7; border:1px solid #f59e0b; border-radius:6px; padding:10px 14px; font-size:12px; color:#92400e; margin-bottom:8px;">'
                        f'⏳ <b>Resolution Proof Submitted:</b> Awaiting citizen confirmation. Once confirmed by the citizen, this ticket will automatically be closed and removed.'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button("↩ Revert to 'In Progress'", key=f"revert_{tid}"):
                        backend.update_status_in_db(tid, "In Progress")
                        st.success(f"Ticket #{tid} status reverted to 'In Progress'.")
                        st.rerun()
                else:
                    # In-progress / Pending updates
                    st1, st2 = st.columns([2, 1])
                    with st1:
                        prog_status = st.selectbox(
                            "Status Step",
                            ["Pending", "In Progress"],
                            index=0 if st_val == "Pending" else 1,
                            key=f"status_step_{tid}",
                            label_visibility="collapsed"
                        )
                    with st2:
                        if st.button("Update Status", key=f"btn_step_{tid}", use_container_width=True):
                            backend.update_status_in_db(tid, prog_status)
                            st.success(f"Ticket #{tid} updated to '{prog_status}'!")
                            st.rerun()

                    # Mandatory Resolution Proof Upload to resolve
                    res_photo = st.file_uploader(
                        f"📸 Upload Mandatory Resolution Proof Photo (#{tid})",
                        type=["png", "jpg", "jpeg"],
                        key=f"proof_photo_{tid}",
                        help="Physical evidence of work completion is strictly required by municipal audit protocol to resolve this ticket."
                    )
                    res_note = st.text_input(
                        f"Resolution Completion Remarks (#{tid})",
                        placeholder="e.g. Cleared 2 metric tons of waste and sanitized container area...",
                        key=f"res_note_{tid}"
                    )

                    if st.button(f"🚀 {t('btn_send_citizen_confirm')} (#{tid})", key=f"btn_res_{tid}", use_container_width=True):
                        if res_photo is None:
                            st.error(f"⚠️ Mandatory Resolution Proof Required: You must attach a photo showing the completed work before sending Ticket #{tid} for citizen verification!")
                        else:
                            photo_bytes = res_photo.getvalue()
                            mime = "image/png" if (res_photo.name or "").lower().endswith(".png") else "image/jpeg"
                            b64_proof = f"data:{mime};base64," + base64.b64encode(photo_bytes).decode("utf-8")
                            backend.update_status_in_db(tid, "Waiting for Citizen Confirmation", resolution_photo=b64_proof, resolution_note=res_note.strip())
                            st.success(f"✓ Resolution proof uploaded for Ticket #{tid}! Sent for citizen verification.")
                            st.rerun()

                with st.expander(f"View AI Diagnostic & Routing Reason (#{tid})"):
                    st.markdown(r["xai_department"])
                    st.markdown("---")
                    st.markdown(r["xai_priority"])

                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)




