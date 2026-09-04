"""
CivicNexus Unified Python Server
Serves the clean civic public portal frontend and provides REST APIs for:
- Multilingual complaint ingestion
- Cosine similarity + Haversine (400m) duplicate detection
- Priority & urgency scoring
- Real-time status lifecycle updates to SQLite
- Lightweight role-based authentication (citizen / admin)
"""

import os
import json
import hashlib
import secrets
import sqlite3
import mimetypes
from datetime import datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import backend

PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("HOST", "0.0.0.0")
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")
USERS_DB_PATH = os.environ.get("CIVIC_USERS_DB", "civic_users.db")


# =============================================================================
# LIGHTWEIGHT AUTH LAYER (mirrors app.py's auth — separate SQLite store)
# =============================================================================
def _users_conn():
    conn = sqlite3.connect(USERS_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _hash_password(password, salt):
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


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
            created_at TEXT,
            department TEXT,
            employee_id TEXT,
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


OFFICER_DEPT_SPECS = {
    "Roads & Infrastructure": {
        "prefix": "MC-RD-",
        "token": "ROADS-SECURE-2026",
    },
    "Water Supply": {
        "prefix": "MC-WS-",
        "token": "WATER-AUTH-2026",
    },
    "Electricity/Power": {
        "prefix": "MC-EE-",
        "token": "POWER-GRID-2026",
    },
    "Waste Management": {
        "prefix": "MC-WM-",
        "token": "SWM-CLEAN-2026",
    },
    "Public Health": {
        "prefix": "MC-PH-",
        "token": "HEALTH-DEPT-2026",
    },
    "All": {
        "prefix": "MC-HQ-",
        "token": "MUNICIPAL-CHIEF-2026",
    },
}


def authenticate(role, username, password):
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


def create_user(role, username, password, full_name, department=None, employee_id=None):
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
        "INSERT INTO users (id, role, username, password_hash, salt, full_name, department, employee_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (uid, role, username, pw_hash, salt, full_name, department, employee_id, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return True, uid


def _send_json(handler, data, status=200):
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(json.dumps(data).encode("utf-8"))


class CivicRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/grievances":
            records = backend.fetch_all_records()
            _send_json(self, {"records": records})
            return

        elif self.path == "/api/clusters":
            records = backend.fetch_all_records()
            clusters = backend.get_macro_clusters(records)
            _send_json(self, {"clusters": clusters})
            return

        elif self.path.startswith("/api/my_upvotes"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            user_id = qs.get("user_id", [""])[0].strip()
            upvoted_ids = backend.fetch_user_upvoted_tickets(user_id)
            _send_json(self, {"upvoted_tickets": upvoted_ids})
            return

        elif self.path.startswith("/api/geocode"):
            from urllib.parse import urlparse, parse_qs, quote
            import urllib.request
            qs = parse_qs(urlparse(self.path).query)
            q = qs.get("q", [""])[0].strip()
            if not q or len(q) < 2:
                _send_json(self, {"results": []})
                return
            try:
                url = f"https://nominatim.openstreetmap.org/search?format=json&q={quote(q)}&countrycodes=in&limit=6"
                req = urllib.request.Request(url, headers={"User-Agent": "AwazSetuCivicPortal/1.0"})
                with urllib.request.urlopen(req, timeout=4) as response:
                    raw_data = json.loads(response.read().decode("utf-8"))
                    results = []
                    for item in raw_data:
                        results.append({
                            "display_name": item.get("display_name", ""),
                            "lat": float(item.get("lat", 0)),
                            "lon": float(item.get("lon", 0)),
                            "type": item.get("type", "place")
                        })
                    _send_json(self, {"results": results})
            except Exception as e:
                _send_json(self, {"results": []})
            return

        super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        # --- AUTH: LOGIN ---
        if self.path == "/api/login":
            role = data.get("role", "").strip()
            username = data.get("username", "").strip()
            password = data.get("password", "")
            selected_dept = data.get("department", "").strip()
            if not role or not username or not password:
                _send_json(self, {"success": False, "error": "Please fill in all required fields."})
                return
            user = authenticate(role, username, password)
            if user:
                safe_user = {k: v for k, v in user.items() if k not in ("password_hash", "salt")}
                if selected_dept and selected_dept != "All":
                    safe_user["department"] = selected_dept
                elif not safe_user.get("department"):
                    safe_user["department"] = selected_dept or "All"
                _send_json(self, {"success": True, "user": safe_user})
            else:
                _send_json(self, {"success": False, "error": "Incorrect username/mobile number or password."})
            return

        # --- AUTH: REGISTER (citizen self-registration; officers provisioned via backend only) ---
        if self.path == "/api/register":
            role = data.get("role", "citizen").strip()
            if role == "admin":
                _send_json(self, {
                    "success": False,
                    "error": "Public officer registration is disabled. Municipal authority accounts are provisioned directly by Municipal IT Administration."
                }, status=403)
                return

            phone = data.get("phone", "").strip().replace(" ", "").replace("-", "").replace("+91", "").lstrip("0")
            password = data.get("password", "")
            full_name = data.get("full_name", "").strip()
            if not phone or not password or not full_name:
                _send_json(self, {"success": False, "error": "Please fill in all required fields."})
                return
            import re
            if not re.fullmatch(r"[6-9]\d{9}", phone):
                _send_json(self, {"success": False, "error": "Please enter a valid 10-digit Indian mobile number."})
                return
            if len(password) < 4:
                _send_json(self, {"success": False, "error": "Password must be at least 4 characters."})
                return
            ok, res = create_user("citizen", phone, password, full_name)
            if ok:
                _send_json(self, {"success": True, "user_id": res, "phone": phone})
            else:
                _send_json(self, {"success": False, "error": "An account with this mobile number already exists. Please log in."})
            return

        # --- GRIEVANCE SUBMISSION ---
        if self.path == "/api/grievance":
            original_text = data.get("original_text", "").strip()
            category_hint = data.get("category_hint", "Auto-Detect")
            lat = float(data.get("lat", 19.0760))
            lon = float(data.get("lon", 72.8777))
            ward = data.get("ward") or data.get("location_name") or backend.nearest_ward(lat, lon)
            citizen_name = data.get("citizen_name", "Citizen")
            citizen_phone = data.get("citizen_phone", "9820123456")
            image_data = data.get("image_data", "")

            photo_bytes = None
            if image_data and "," in image_data:
                try:
                    import base64
                    photo_bytes = base64.b64decode(image_data.split(",", 1)[1])
                except Exception:
                    photo_bytes = None

            text_en, detected_lang, _ = backend.normalize_to_english(original_text)
            sia = backend.SentimentIntensityAnalyzer()
            sentiment = sia.polarity_scores(text_en)["compound"]
            department, xai_dept, _ = backend.classify_department(text_en, category_hint=category_hint, photo_bytes=photo_bytes)

            embedding = backend.embed_text(text_en)
            existing_records = backend.fetch_all_records()
            parent_id, sim = backend.find_duplicate_match(embedding, lat, lon, existing_records, new_dept=department, new_text=text_en)

            severity_score, priority, xai_priority = backend.score_priority(
                text_en, sentiment, upvotes=0, has_photo=bool(image_data), photo_bytes=photo_bytes
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
                "ward": ward,
                "status": "Pending",
                "upvotes": 0,
                "is_duplicate": 1 if parent_id else 0,
                "parent_id": parent_id,
                "embedding": json.dumps(embedding.tolist()),
                "xai_department": xai_dept,
                "xai_priority": xai_priority,
                "image_flag": 1 if image_data else 0,
                "image_data": image_data,
                "citizen_name": citizen_name,
                "citizen_phone": citizen_phone,
                "created_at": backend.datetime.now().isoformat(),
            }
            backend.insert_record(record)

            if parent_id:
                backend.increment_upvote_in_db(parent_id, boost_points=8)

            _send_json(self, {"success": True, "data": record})
            return

        # --- STATUS UPDATE / RESOLUTION ---
        elif self.path == "/api/resolve":
            ticket_id = data.get("id")
            new_status = data.get("status", "Waiting for Citizen Confirmation")
            resolution_photo = data.get("resolution_photo")
            resolution_note = data.get("resolution_note")

            if not ticket_id:
                _send_json(self, {"success": False, "error": "Ticket ID is required."}, status=400)
                return

            # STRICT ENFORCEMENT: Mandatory photo proof before resolving / waiting for citizen confirmation
            if new_status in ("Resolved", "Waiting for Citizen Confirmation", "Awaiting Citizen Confirmation"):
                if not resolution_photo or not str(resolution_photo).strip():
                    _send_json(self, {
                        "success": False,
                        "error": "Mandatory Photographic Evidence: You must upload an 'After' completion photo before marking this complaint for citizen confirmation."
                    }, status=400)
                    return

            backend.update_status_in_db(
                ticket_id, new_status, resolution_photo=resolution_photo, resolution_note=resolution_note
            )
            _send_json(self, {"success": True, "status": new_status, "id": ticket_id})
            return

        # --- CITIZEN FEEDBACK / REOPEN / DELETE ON RESOLUTION ---
        elif self.path == "/api/feedback":
            ticket_id = data.get("id")
            feedback = data.get("feedback", "Satisfied")
            remarks = data.get("remarks", "")
            if ticket_id:
                result = backend.record_citizen_feedback_in_db(ticket_id, feedback, remarks)
                is_deleted = result.get("deleted", False) if isinstance(result, dict) else (feedback in ("Satisfied", "Confirmed", "Resolved"))
                _send_json(self, {
                    "success": True, 
                    "deleted": is_deleted, 
                    "feedback": feedback, 
                    "id": ticket_id,
                    "message": "Ticket verified as resolved by citizen and deleted from active system." if is_deleted else "Feedback recorded."
                })
                return

        # --- CITIZEN UPVOTE (+1 AFFECTS ME TOO) ---
        elif self.path == "/api/upvote":
            ticket_id = data.get("id")
            user_id = data.get("user_id") or data.get("phone") or data.get("username")
            role = data.get("role", "citizen")

            if role == "admin":
                _send_json(self, {
                    "success": False,
                    "error": "Access Denied: Municipal officers and administrators cannot upvote civic complaints."
                }, status=403)
                return

            if not ticket_id:
                _send_json(self, {"success": False, "error": "Ticket ID is required."}, status=400)
                return

            if not user_id:
                _send_json(self, {
                    "success": False,
                    "error": "You must be logged in as a citizen to support this grievance."
                }, status=401)
                return

            res, err = backend.record_citizen_upvote_in_db(ticket_id, str(user_id).strip(), boost_points=6)
            if err == "already_upvoted":
                _send_json(self, {
                    "success": False,
                    "error": "You have already registered your support for this issue (+1)."
                }, status=400)
            elif err == "not_found":
                _send_json(self, {"success": False, "error": "Ticket not found."}, status=404)
            elif res:
                _send_json(self, {"success": True, **res, "id": ticket_id})
            else:
                _send_json(self, {"success": False, "error": "Unable to process upvote."}, status=500)
            return

        # --- DELETE TICKET ---
        elif self.path == "/api/delete":
            ticket_id = data.get("id")
            if ticket_id:
                backend.delete_record_from_db(ticket_id)
                _send_json(self, {"success": True, "deleted": ticket_id})
                return

        self.send_response(400)
        self.end_headers()


def run_server():
    backend.init_db()
    init_users_db()
    server_address = (HOST, PORT)
    httpd = ThreadingHTTPServer(server_address, CivicRequestHandler)
    print(f"AwazSetu Server running on http://{HOST}:{PORT}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
