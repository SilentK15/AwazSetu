"""
CivicNexus Unified Python Server
Serves the clean civic public portal frontend and provides REST APIs for:
- Multilingual complaint ingestion with SentenceTransformers
- Cosine similarity + Haversine (400m) duplicate detection
- Priority & urgency scoring with VADER sentiment
- Real-time status lifecycle updates to SQLite
"""

import os
import json
import mimetypes
from http.server import HTTPServer, SimpleHTTPRequestHandler
import backend

PORT = 8080
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")


class CivicRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/grievances":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            records = backend.fetch_all_records()
            self.wfile.write(json.dumps({"records": records}).encode("utf-8"))
            return

        elif self.path == "/api/clusters":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            records = backend.fetch_all_records()
            clusters = backend.get_macro_clusters(records)
            self.wfile.write(json.dumps({"clusters": clusters}).encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if self.path == "/api/grievance":
            original_text = data.get("original_text", "").strip()
            category_hint = data.get("category_hint", "Not sure / Let AI decide")
            lat = float(data.get("lat", 19.0760))
            lon = float(data.get("lon", 72.8777))
            ward = data.get("ward", backend.nearest_ward(lat, lon))
            citizen_name = data.get("citizen_name", "Citizen")
            citizen_phone = data.get("citizen_phone", "9820123456")

            # AI Pipeline
            text_en, detected_lang, _ = backend.normalize_to_english(original_text)
            sia = backend.SentimentIntensityAnalyzer()
            sentiment = sia.polarity_scores(text_en)["compound"]
            department, xai_dept, _ = backend.classify_department(text_en)

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
                "ward": ward,
                "status": "Pending",
                "upvotes": 0,
                "is_duplicate": 1 if parent_id else 0,
                "parent_id": parent_id,
                "embedding": json.dumps(embedding.tolist()),
                "xai_department": xai_dept,
                "xai_priority": xai_priority,
                "image_flag": 0,
                "citizen_name": citizen_name,
                "citizen_phone": citizen_phone,
                "created_at": backend.datetime.now().isoformat(),
            }
            backend.insert_record(record)

            if parent_id:
                backend.increment_upvote_in_db(parent_id, boost_points=8)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "data": record}).encode("utf-8"))
            return

        elif self.path == "/api/resolve":
            ticket_id = data.get("id")
            new_status = data.get("status", "Resolved")
            if ticket_id:
                backend.update_status_in_db(ticket_id, new_status)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "status": new_status}).encode("utf-8"))
                return

        self.send_response(400)
        self.end_headers()


def run_server():
    backend.init_db()
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, CivicRequestHandler)
    print(f"CivicNexus Civic Redressal Server running on http://localhost:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
