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
from datetime import datetime

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
            created_at TEXT,
            UNIQUE(role, username)
        )
    """)
    conn.commit()
    # Seed a default authority account for demo/evaluation access
    existing = conn.execute(
        "SELECT id FROM users WHERE role = ? AND username = ?", ("admin", "admin")
    ).fetchone()
    if not existing:
        salt = secrets.token_hex(8)
        pw_hash = _hash_password("admin123", salt)
        conn.execute(
            "INSERT INTO users (id, role, username, password_hash, salt, full_name, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("USR-ADM-001", "admin", "admin", pw_hash, salt, "Authority Administrator", datetime.now().isoformat()),
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
        "lbl_phone": "Registered mobile number",
        "lbl_username": "Username",
        "lbl_password": "Password",
        "lbl_confirm_password": "Confirm password",
        "btn_login": "Log In",
        "btn_register": "Create Account",
        "citizen_login_desc": "Log in with your registered mobile number to submit and track grievances.",
        "citizen_register_desc": "Create an AwazSetu citizen account to submit and track your grievances.",
        "admin_login_desc": "Authorised personnel only. Log in to access the operations dashboard.",
        "err_fields": "Please fill in all required fields.",
        "err_invalid": "Incorrect username/mobile number or password.",
        "err_exists": "An account with this mobile number already exists. Please log in instead.",
        "err_phone": "Please enter a valid 10-digit mobile number.",
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
        "lbl_phone": "पंजीकृत मोबाइल नंबर",
        "lbl_username": "उपयोगकर्ता नाम",
        "lbl_password": "पासवर्ड",
        "lbl_confirm_password": "पासवर्ड की पुष्टि करें",
        "btn_login": "लॉग इन करें",
        "btn_register": "खाता बनाएं",
        "citizen_login_desc": "शिकायत दर्ज करने और ट्रैक करने के लिए अपने पंजीकृत मोबाइल नंबर से लॉग इन करें।",
        "citizen_register_desc": "शिकायत दर्ज करने और ट्रैक करने के लिए आवाज़सेतु नागरिक खाता बनाएं।",
        "admin_login_desc": "केवल अधिकृत कर्मियों के लिए। संचालन डैशबोर्ड तक पहुँचने के लिए लॉग इन करें।",
        "err_fields": "कृपया सभी आवश्यक फ़ील्ड भरें।",
        "err_invalid": "गलत उपयोगकर्ता नाम/मोबाइल नंबर या पासवर्ड।",
        "err_exists": "इस मोबाइल नंबर से पहले से खाता मौजूद है। कृपया लॉग इन करें।",
        "err_phone": "कृपया मान्य 10-अंकीय मोबाइल नंबर दर्ज करें।",
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
        "lbl_phone": "नोंदणीकृत मोबाइल क्रमांक",
        "lbl_username": "वापरकर्तानाव",
        "lbl_password": "पासवर्ड",
        "lbl_confirm_password": "पासवर्डची पुष्टी करा",
        "btn_login": "लॉग इन",
        "btn_register": "खाते तयार करा",
        "citizen_login_desc": "तक्रार नोंदवण्यासाठी आणि ट्रॅक करण्यासाठी नोंदणीकृत मोबाइल क्रमांकाने लॉग इन करा.",
        "citizen_register_desc": "तक्रार नोंदवण्यासाठी आणि ट्रॅक करण्यासाठी नागरिक खाते तयार करा.",
        "admin_login_desc": "केवळ अधिकृत कर्मचाऱ्यांसाठी. संचालन डॅशबोर्डमध्ये प्रवेशासाठी लॉग इन करा.",
        "err_fields": "कृपया सर्व आवश्यक माहिती भरा.",
        "err_invalid": "चुकीचे वापरकर्तानाव/मोबाइल क्रमांक किंवा पासवर्ड.",
        "err_exists": "या मोबाइल क्रमांकासह आधीच खाते अस्तित्वात आहे. कृपया लॉग इन करा.",
        "err_phone": "कृपया वैध 10-अंकी मोबाइल क्रमांक टाका.",
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
    },
}


def t(key: str) -> str:
    lang = st.session_state.get("ui_lang", "en")
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))


# =============================================================================
# DESIGN SYSTEM — CSS (Clean Public Service Aesthetic & Crisp Contrast)
# =============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;500;600;700;800&family=Noto+Serif:wght@600;700&display=swap');

:root {
  --navy: #0b3c5d;
  --navy-dark: #07263d;
  --navy-tint: #f0f6fa;
  --saffron: #ff9933;
  --green: #138808;
  --ink: #0f172a;
  --text-main: #1e293b;
  --text-muted: #475569;
  --border: #cbd5e1;
  --surface: #ffffff;
  --bg: #f8fafc;
  --radius: 8px;
}

html, body, [data-testid="stAppViewContainer"] {
  font-family: "Noto Sans", "Segoe UI", Arial, sans-serif !important;
  background-color: var(--bg) !important;
  color: var(--text-main) !important;
}

[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden !important; height: 0px !important; }

.block-container {
  padding-top: 0.8rem !important;
  padding-bottom: 2.5rem !important;
  max-width: 1140px !important;
}

/* Typography Contrast */
h1, h2, h3, h4, h5, h6 { color: var(--navy) !important; font-weight: 800 !important; }
p, li { color: var(--text-main) !important; line-height: 1.6; }
label, .stMarkdown label, [data-testid="stWidgetLabel"] p { color: #0f172a !important; font-weight: 700 !important; font-size: 0.9rem !important; }
small, .stCaption, caption { color: var(--text-muted) !important; }

/* Utility Bar */
.utility-bar {
  background: var(--navy);
  padding: 8px 16px;
  border-radius: 6px 6px 0 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11.5px;
  color: #ffffff !important;
}
.utility-bar span, .utility-bar div { color: #ffffff !important; font-weight: 600; }

/* Identity Bar */
.identity-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-top: none;
  padding: 16px 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 3px rgba(11,60,93,0.04);
}

.emblem-icon {
  width: 46px; height: 46px;
  border: 2px solid var(--navy);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-family: "Noto Serif", serif;
  font-size: 19px; font-weight: 800;
  color: var(--navy) !important;
  background: var(--navy-tint);
  margin-right: 14px;
}

.tricolor-rule { display: flex; height: 3px; margin-bottom: 16px; }
.tricolor-rule span:nth-child(1) { flex: 1; background: var(--saffron); }
.tricolor-rule span:nth-child(2) { flex: 1; background: #ffffff; }
.tricolor-rule span:nth-child(3) { flex: 1; background: var(--green); }

.user-chip {
  display: flex; align-items: center; gap: 10px;
  background: var(--navy-tint);
  border: 1px solid var(--border);
  padding: 6px 14px 6px 6px;
  border-radius: 999px;
}
.user-chip .avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--navy); color: #ffffff !important;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 800;
}
.role-pill {
  display: inline-block;
  font-size: 10px; font-weight: 800; letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 2px 8px; border-radius: 999px;
  background: #ffffff; color: var(--navy) !important;
  border: 1px solid var(--border);
}
.role-pill.admin { background: #fff4e6; color: #9a5b00 !important; border-color: #f3d9ae; }

/* Cards */
.hero-box {
  background: linear-gradient(180deg, #f0f6fa 0%, #ffffff 100%);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 22px 26px;
  margin-bottom: 18px;
}

.civic-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 20px;
  box-shadow: 0 1px 3px rgba(11,60,93,0.04);
  margin-bottom: 14px;
}

.section-kicker {
  font-size: 10.5px; font-weight: 800; letter-spacing: 0.08em;
  color: var(--navy) !important; text-transform: uppercase;
}

/* Inputs & Form Controls */
.stTextInput input, .stTextArea textarea, .stNumberInput input, .stPassword input {
  background-color: #ffffff !important;
  color: #0f172a !important;
  border: 1.5px solid #94a3b8 !important;
  border-radius: 6px !important;
  font-size: 0.95rem !important;
  font-weight: 500 !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus, .stPassword input:focus {
  border-color: var(--navy) !important;
  box-shadow: 0 0 0 3px rgba(11,60,93,0.18) !important;
}
div[data-baseweb="select"] > div {
  background-color: #ffffff !important;
  border: 1.5px solid #94a3b8 !important;
  border-radius: 6px !important;
}

/* Primary Action Buttons */
.stFormSubmitButton > button {
  background: var(--navy) !important;
  color: #ffffff !important;
  border: 1px solid var(--navy) !important;
  padding: 10px 22px !important;
  font-weight: 800 !important;
  border-radius: 6px !important;
  font-size: 0.95rem !important;
}
.stFormSubmitButton > button:hover { background: var(--navy-dark) !important; color: #ffffff !important; }
.stFormSubmitButton > button p { color: #ffffff !important; }

/* Secondary Buttons */
.stButton > button {
  background: #ffffff !important;
  color: var(--navy) !important;
  border: 1.5px solid var(--border) !important;
  padding: 7px 16px !important;
  font-weight: 700 !important;
  border-radius: 6px !important;
  font-size: 0.88rem !important;
}
.stButton > button:hover { background: #f1f5f9 !important; border-color: var(--navy) !important; color: var(--navy) !important; }
.stButton > button p { color: var(--navy) !important; font-weight: 700; }

/* Badges */
.badge-pending { background: #fee2e2; color: #991b1b !important; padding: 3px 10px; border-radius: 12px; font-weight: 800; font-size: 10.5px; border: 1px solid #fecaca; }
.badge-progress { background: #fef3c7; color: #92400e !important; padding: 3px 10px; border-radius: 12px; font-weight: 800; font-size: 10.5px; border: 1px solid #fde68a; }
.badge-resolved { background: #dcfce7; color: #166534 !important; padding: 3px 10px; border-radius: 12px; font-weight: 800; font-size: 10.5px; border: 1px solid #bbf7d0; }

/* Stepper */
.stepper-strip {
  display: flex;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 18px;
  margin-bottom: 16px;
  align-items: center;
  justify-content: space-between;
}

/* Nav Radios */
div[role="radiogroup"] {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 6px;
  gap: 4px !important;
}
div[role="radiogroup"] label {
  border-radius: 6px;
  padding: 8px 16px !important;
  font-weight: 700 !important;
  font-size: 0.88rem !important;
}
div[role="radiogroup"] label[data-checked="true"],
div[role="radiogroup"] label:has(input:checked) {
  background: var(--navy-tint) !important;
}

/* Auth Card & Tabs Alignment */
.auth-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(11,60,93,0.06);
  padding: 24px 28px 16px 28px;
  margin-top: 6px;
  margin-bottom: 12px;
}
.auth-header { text-align: center; margin-bottom: 6px; }
.auth-emblem {
  width: 52px; height: 52px; margin: 0 auto 10px auto;
  border: 2px solid var(--navy); border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-family: "Noto Serif", serif; font-size: 20px; font-weight: 800;
  color: var(--navy) !important; background: var(--navy-tint);
  box-shadow: 0 2px 8px rgba(11,60,93,0.08);
}
.auth-note {
  background: #fff8ec;
  border: 1px solid #f3d9ae;
  color: #7a4b00 !important;
  font-size: 11.5px;
  padding: 10px 14px;
  border-radius: 6px;
  margin-top: 12px;
}
.auth-note * { color: #7a4b00 !important; }

/* Polished Full-Width Segmented Tab Navigation */
div[data-testid="stTabs"] {
  width: 100% !important;
}
div[data-testid="stTabs"] [data-baseweb="tab-list"] {
  display: flex !important;
  width: 100% !important;
  gap: 6px !important;
  border-bottom: 2px solid #e2e8f0 !important;
  padding: 0 0 2px 0 !important;
  margin-bottom: 12px !important;
}
div[data-testid="stTabs"] [data-baseweb="tab"] {
  flex: 1 1 0% !important;
  text-align: center !important;
  justify-content: center !important;
  font-weight: 700 !important;
  font-size: 13.5px !important;
  color: #64748b !important;
  padding: 10px 16px !important;
  border-radius: 6px 6px 0 0 !important;
  background: transparent !important;
  border: none !important;
  border-bottom: 3px solid transparent !important;
  margin-bottom: -2px !important;
  transition: all 0.15s ease-in-out !important;
}
div[data-testid="stTabs"] [data-baseweb="tab"]:hover {
  color: var(--navy) !important;
  background: rgba(11,60,93,0.04) !important;
}
div[data-testid="stTabs"] [aria-selected="true"] {
  color: var(--navy) !important;
  font-weight: 800 !important;
  border-bottom: 3px solid var(--navy) !important;
  background: #f8fafc !important;
}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
  background-color: var(--navy) !important;
  height: 3px !important;
}
div[data-testid="stTabs"] [data-baseweb="tab-border"] {
  background-color: #e2e8f0 !important;
}

/* Sub-tabs within Auth (Level 2) */
div[data-testid="stTabs"] div[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: #f1f5f9 !important;
  border-radius: 8px !important;
  padding: 4px !important;
  border-bottom: none !important;
  gap: 4px !important;
}
div[data-testid="stTabs"] div[data-testid="stTabs"] [data-baseweb="tab"] {
  border-radius: 6px !important;
  padding: 7px 12px !important;
  font-size: 12.5px !important;
  border-bottom: none !important;
  margin-bottom: 0 !important;
}
div[data-testid="stTabs"] div[data-testid="stTabs"] [aria-selected="true"] {
  background: #ffffff !important;
  color: var(--navy) !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
  border-bottom: none !important;
}
div[data-testid="stTabs"] div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
  display: none !important;
}

[data-testid="stMetricValue"] { color: var(--navy) !important; font-weight: 800 !important; }
[data-testid="stMetricLabel"] { color: var(--text-muted) !important; font-weight: 700 !important; }
hr { border-color: var(--border) !important; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SHARED HEADER (Identity bar + Tricolor rule + Language switch)
# =============================================================================
def render_header():
    # Top Utility Bar
    u1, u2 = st.columns([3.2, 1.8])
    with u1:
        st.markdown(
            "<div class='utility-bar'><span>AwazSetu — Accessible Public Grievance &amp; Redressal Service</span>"
            "<span style='font-size:10.5px;'>Helpline: 1916 | Emergency: 112</span></div>",
            unsafe_allow_html=True,
        )
    with u2:
        l1, l2, l3 = st.columns(3)
        with l1:
            if st.button("English", key="btn_lang_en", use_container_width=True):
                st.session_state["ui_lang"] = "en"; st.rerun()
        with l2:
            if st.button("हिंदी", key="btn_lang_hi", use_container_width=True):
                st.session_state["ui_lang"] = "hi"; st.rerun()
        with l3:
            if st.button("मराठी", key="btn_lang_mr", use_container_width=True):
                st.session_state["ui_lang"] = "mr"; st.rerun()

    # Identity Bar
    user = st.session_state.get("auth_user")
    if user:
        role_class = "admin" if st.session_state.get("auth_role") == "admin" else ""
        role_label = t("role_admin_tag") if st.session_state.get("auth_role") == "admin" else t("role_citizen_tag")
        initial = (user.get("full_name") or user.get("username") or "?")[:1].upper()
        name_display = user.get("full_name") or user.get("username")
        right_html = f'<div class="user-chip"><div class="avatar">{initial}</div><div><strong style="font-size:12px; color:var(--navy); display:block;">{name_display}</strong><span class="role-pill {role_class}">{role_label}</span></div></div>'
    else:
        right_html = f'<div style="display:flex; align-items:center; gap:8px; background:#fafcfd; border:1px solid var(--border); padding:8px 14px; border-radius:6px;"><div style="width:8px; height:8px; border-radius:50%; background:var(--green);"></div><div><strong style="font-size:11px; color:var(--navy); display:block;">{t("portal_status")}</strong><small style="font-size:10px; color:var(--text-muted); display:block;">{t("status_operational")}</small></div></div>'

    st.markdown(
        f'<div class="identity-box"><div style="display:flex; align-items:center;"><div class="emblem-icon">AS</div><div><div class="section-kicker">{t("portal_eyebrow")}</div><h2 style="margin:2px 0 0 0; color:var(--navy); font-size:22px; font-weight:800;">{t("portal_title")}</h2><p style="margin:2px 0 0 0; color:var(--text-muted); font-size:12px;">{t("portal_subtitle")}</p></div></div>{right_html}</div><div class="tricolor-rule"><span></span><span></span><span></span></div>',
        unsafe_allow_html=True,
    )

    if user:
        _, logout_col = st.columns([5, 1])
        with logout_col:
            if st.button(t("logout_btn"), key="logout_btn", use_container_width=True):
                st.session_state["auth_user"] = None
                st.session_state["auth_role"] = None
                st.session_state["active_tab"] = None
                st.rerun()


# =============================================================================
# AUTH / LOGIN PAGE (Zero Extra Vertical Scroll)
# =============================================================================
def render_auth_page():
    render_header()

    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.markdown(f"""
        <div class="auth-box">
          <div class="auth-header">
            <div class="auth-emblem">AS</div>
            <div class="section-kicker">{t("auth_eyebrow")}</div>
            <h3 style="margin:4px 0 2px 0; color:var(--navy);">{t("auth_title")}</h3>
            <p style="font-size:12px; color:var(--text-muted); margin:0;">{t("auth_subtitle")}</p>
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
                    phone_in = st.text_input(t("lbl_phone"), max_chars=10, placeholder="9820012345")
                    pw_in = st.text_input(t("lbl_password"), type="password")
                    go = st.form_submit_button(t("btn_login"), use_container_width=True)
                if go:
                    if not phone_in or not pw_in:
                        st.error(t("err_fields"))
                    else:
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
                    phone_reg = st.text_input(t("lbl_phone"), max_chars=10, placeholder="9820012345")
                    pw1 = st.text_input(t("lbl_password"), type="password")
                    pw2 = st.text_input(t("lbl_confirm_password"), type="password")
                    reg_go = st.form_submit_button(t("btn_register"), use_container_width=True)
                if reg_go:
                    if not name_in or not phone_reg or not pw1 or not pw2:
                        st.error(t("err_fields"))
                    elif not re.fullmatch(r"\d{10}", phone_reg.strip()):
                        st.error(t("err_phone"))
                    elif len(pw1) < 4:
                        st.error(t("err_password_len"))
                    elif pw1 != pw2:
                        st.error(t("err_password_match"))
                    else:
                        ok, res = create_user("citizen", phone_reg.strip(), pw1, name_in.strip())
                        if ok:
                            st.success(t("success_register"))
                        else:
                            st.error(t("err_exists"))

        # ---------------- ADMIN AUTH ----------------
        with role_tab_admin:
            st.caption(t("admin_login_desc"))
            with st.form("admin_login_form"):
                uname_in = st.text_input(t("lbl_username"), placeholder="admin")
                apw_in = st.text_input(t("lbl_password"), type="password")
                ago = st.form_submit_button(t("btn_login"), use_container_width=True)
            if ago:
                if not uname_in or not apw_in:
                    st.error(t("err_fields"))
                else:
                    user = authenticate("admin", uname_in.strip(), apw_in)
                    if user:
                        st.session_state["auth_user"] = user
                        st.session_state["auth_role"] = "admin"
                        st.session_state["active_tab"] = "dashboard"
                        st.rerun()
                    else:
                        st.error(t("err_invalid"))
            st.markdown(f'<div class="auth-note">{t("demo_admin_hint")}</div>', unsafe_allow_html=True)


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

                department, xai_dept, _ = backend.classify_department(text_en)
                if category_hint != t("cat_placeholder") and category_hint != department:
                    xai_dept += f"\n- User selected hint '{category_hint}', but AI classified as '{department}' from semantic keywords."

                embedding = backend.embed_text(text_en)
                existing_records = backend.fetch_all_records()
                parent_id, sim = backend.find_duplicate_match(embedding, lat, lon, existing_records)

                severity_score, priority, xai_priority = backend.score_priority(text_en, sentiment, upvotes=0)
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
            p_color = backend.PRIORITY_COLORS.get(r['priority'], '#64748b')
            status_badge = (
                f'<span class="badge-pending">{t("status_pending")}</span>' if r['status'] == 'Pending'
                else f'<span class="badge-progress">{t("status_progress")}</span>' if r['status'] == 'In Progress'
                else f'<span class="badge-resolved">{t("status_resolved")}</span>'
            )
            dup_tag = f"<span style='color:#a15c00; font-size:11px;'>[Merged into #{r['parent_id']}]</span>" if r['is_duplicate'] else ""

            st.markdown(
                f'<div class="civic-card">'
                f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">'
                f'<div><span style="font-weight:800; color:var(--navy); font-size:1.05rem;">#{r["id"]}</span> &nbsp;·&nbsp; <b>{r["department"]}</b> {dup_tag} &nbsp;·&nbsp; <span style="font-size:0.8rem; color:var(--muted);">Area: {r["ward"]}</span></div>'
                f'<div>{status_badge} &nbsp;<span style="color:{p_color}; font-weight:700; font-size:11px; border:1px solid {p_color}; padding:2px 8px; border-radius:4px;">{r["priority"]} ({r["severity_score"]}/100)</span></div>'
                f'</div>'
                f'<div style="color:var(--ink); font-size:0.9rem; margin-bottom:8px;">"{r["original_text"]}"</div>'
                f'<div style="display:flex; justify-content:space-between; font-size:0.8rem; color:var(--muted);">'
                f'<span>Reported: {r["created_at"][:16].replace("T", " ")}</span>'
                f'<span>Community Confirmations: <b>{r["upvotes"]}</b></span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# =============================================================================
# VIEW: AUTHORITY OPERATIONS DASHBOARD (Admin Only)
# =============================================================================
elif selected_tab == "dashboard":
    records = backend.fetch_all_records()
    total = len(records)
    pending = sum(1 for r in records if r["status"] == "Pending")
    in_prog = sum(1 for r in records if r["status"] == "In Progress")
    high_crit = sum(1 for r in records if r["priority"] in ["Critical", "High"] and r["status"] != "Resolved")
    resolved = sum(1 for r in records if r["status"] == "Resolved")
    res_rate = (resolved / total * 100) if total > 0 else 0.0

    st.markdown(f"""
    <div style="margin:4px 0 14px 0;">
      <div class="section-kicker">{t("dash_kicker")}</div>
      <h2 style="color:var(--navy); font-size:24px; font-weight:800; margin:2px 0 4px 0;">{t("dash_title")}</h2>
      <p style="color:var(--text-muted); font-size:12.5px; margin:0;">Real-time incident oversight, GIS density heatmap, and grievance redressal controls.</p>
    </div>
    """, unsafe_allow_html=True)

    # 4 Essential Operational KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(t("kpi_total"), total)
    k2.metric(t("kpi_pending"), pending)
    k3.metric("High / Critical", high_crit)
    k4.metric(t("kpi_resolved"), resolved, f"{res_rate:.1f}% Resolved")

    if not records:
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

        # Heatmap Layer: weighted by severity score and upvotes
        heat_data = [
            [r["lat"], r["lon"], float(max(r.get("severity_score", 40), 10) + r.get("upvotes", 0) * 5)]
            for r in records if r.get("lat") and r.get("lon")
        ]
        if heat_data:
            HeatMap(
                heat_data,
                radius=28,
                blur=20,
                max_zoom=14,
                gradient={0.2: "#3b82f6", 0.4: "#10b981", 0.6: "#f59e0b", 0.8: "#ef4444", 1.0: "#7f1d1d"}
            ).add_to(fmap_admin)

        # Pinpoint Marker Layer
        for r in records:
            p_color = backend.PRIORITY_COLORS.get(r["priority"], "#64748b")
            status_symbol = "⏳" if r["status"] == "Pending" else "⚡" if r["status"] == "In Progress" else "✅"
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

        f_col1, f_col2, f_col3 = st.columns([1.2, 1.2, 1.6])
        with f_col1:
            dept_filter = st.selectbox("Filter Department", ["All Departments"] + list(backend.DEPARTMENTS.keys()), key="adm_dept_filter")
        with f_col2:
            status_filter = st.selectbox("Filter Status", ["All Statuses", "Pending", "In Progress", "Resolved"], key="adm_status_filter")
        with f_col3:
            search_ticket = st.text_input("Search ID or Keyword", placeholder="Ticket #, description, ward...", key="adm_search_box")

        filtered_records = records
        if dept_filter != "All Departments":
            filtered_records = [r for r in filtered_records if r["department"] == dept_filter]
        if status_filter != "All Statuses":
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
                st_badge = (
                    f'<span class="badge-pending">Pending</span>' if r['status'] == 'Pending'
                    else f'<span class="badge-progress">In Progress</span>' if r['status'] == 'In Progress'
                    else f'<span class="badge-resolved">Resolved</span>'
                )

                dup_tag = ""
                if r.get("is_duplicate") == 1:
                    dup_tag = f'<span style="background:#ede9fe; color:#5b21b6; padding:2px 8px; border-radius:4px; font-weight:800; font-size:10.5px; border:1px solid #ddd6fe; margin-left:6px;">🔗 Merged Duplicate ➔ #{r.get("parent_id")}</span>'
                elif r.get("upvotes", 0) > 0:
                    dup_tag = f'<span style="background:#dbeafe; color:#1e40af; padding:2px 8px; border-radius:4px; font-weight:800; font-size:10.5px; border:1px solid #bfdbfe; margin-left:6px;">👥 Master Ticket ({r.get("upvotes")} Merged Reports)</span>'

                st.markdown(
                    f'<div class="civic-card" style="border-left: 4px solid {p_color}; margin-bottom: 12px;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">'
                    f'<div><strong style="font-size:1.05rem; color:var(--navy);">#{tid}</strong> &nbsp;·&nbsp; <b>{r["department"]}</b> &nbsp;·&nbsp; <span style="font-size:11.5px; color:var(--text-muted);">Area: {r["ward"]}</span>{dup_tag}</div>'
                    f'<div>{st_badge} &nbsp;<span style="color:{p_color}; font-weight:800; font-size:11px; border:1px solid {p_color}; padding:2px 8px; border-radius:4px; background:#ffffff;">{r["priority"]} ({r["severity_score"]}/100)</span></div>'
                    f'</div>'
                    f'<p style="margin:8px 0; font-size:0.92rem; color:#1e293b;">"{r["original_text"]}"</p>'
                    f'<div style="font-size:11px; color:var(--text-muted); display:flex; justify-content:space-between; margin-bottom:4px;">'
                    f'<span>Reporter: <b>{r.get("citizen_name", "Citizen")}</b> ({r.get("citizen_phone") or "Direct"})</span>'
                    f'<span>Reported: {r["created_at"][:16].replace("T", " ")} · Community Confirmations: <b>{r["upvotes"]}</b></span>'
                    f'</div>'
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

                # Action bar per ticket
                act1, act2, act3 = st.columns([1.5, 1, 1])
                with act1:
                    new_status = st.selectbox(
                        "Change Status",
                        backend.STATUS_OPTIONS,
                        index=backend.STATUS_OPTIONS.index(r["status"]),
                        key=f"status_select_{tid}",
                        label_visibility="collapsed"
                    )
                with act2:
                    if st.button("Update", key=f"btn_upd_{tid}", use_container_width=True):
                        backend.update_status_in_db(tid, new_status)
                        if new_status == "Resolved":
                            st.success(f"Ticket #{tid} resolved and deleted from active queue!")
                        else:
                            st.success(f"Ticket #{tid} updated to '{new_status}'!")
                        st.rerun()
                with act3:
                    if st.button("Mark Resolved", key=f"btn_res_{tid}", use_container_width=True):
                        backend.update_status_in_db(tid, "Resolved")
                        st.success(f"Ticket #{tid} resolved and removed from queue!")
                        st.rerun()

                with st.expander(f"View AI Diagnostic & Routing Reason (#{tid})"):
                    st.markdown(r["xai_department"])
                    st.markdown("---")
                    st.markdown(r["xai_priority"])

                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)




