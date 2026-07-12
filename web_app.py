"""FIRE-PMIS web prototype. Run: python web_app.py, then visit http://localhost:8000"""
from __future__ import annotations

import html
import json
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from services.storage import ROOT, get_assets, save_assets
from services.predictor import get_status
from models.extinguisher import FIELDS


def get_status(expiry: str) -> tuple[str, int, str]:
    days = (datetime.strptime(expiry, "%Y-%m-%d").date() - date.today()).days
    if days < 0: return "Expired — replace now", days, "expired"
    if days <= 30: return "Replace urgently", days, "urgent"
    if days <= 90: return "Plan replacement", days, "plan"
    if days <= 180: return "Monitor", days, "monitor"
    return "Serviceable", days, "good"


def page(body: str, title: str = "FIRE-PMIS") -> bytes:
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>{title}</title><link rel="stylesheet" href="/static/css/style.css"></head>
    <body><header><h1>FIRE-PMIS</h1><p>Fire Extinguisher Predictive Maintenance & Replacement Monitor</p></header><main>{body}</main></body></html>""".encode()


def dashboard(query: str = "", notice: str = "") -> str:
    data = sorted(get_assets(), key=lambda row: row["expiry_date"])
    counts = {"Total assets":len(data), "Replace now":0, "Urgent":0, "Plan":0, "Serviceable":0}
    for row in data:
        decision, _, _ = get_status(row["expiry_date"])
        if decision.startswith("Expired"): counts["Replace now"] += 1
        elif decision.startswith("Replace"): counts["Urgent"] += 1
        elif decision.startswith("Plan"): counts["Plan"] += 1
        elif decision == "Serviceable": counts["Serviceable"] += 1
    cards = "".join(f"<div class='card'>{html.escape(key)}<b>{value}</b></div>" for key,value in counts.items())
    rows = ""
    for row in data:
        if query.casefold() not in " ".join(row.values()).casefold(): continue
        decision, days, level = get_status(row["expiry_date"])
        rows += f"<tr><td>{html.escape(row['asset_id'])}</td><td>{html.escape(row['location'])}</td><td>{html.escape(row['type'])}</td><td>{html.escape(row['capacity_kg'])} kg</td><td>{row['expiry_date']}</td><td>{days}</td><td><span class='badge {level}'>{decision}</span></td><td>{row['last_inspection']}</td><td><a class='button secondary' href='/edit?id={html.escape(row['asset_id'])}'>Edit</a></td></tr>"
    notice_html = f"<div class='notice'>{html.escape(notice)}</div>" if notice else ""
    return f"<div class='cards'>{cards}</div>{notice_html}<div class='toolbar'><form method='get' action='/' style='padding:0;box-shadow:none;display:flex;gap:8px;max-width:400px'><input name='q' placeholder='Search ID, location, or type' value='{html.escape(query)}'><button>Search</button></form><a class='button' href='/add'>+ Add extinguisher</a></div><div class='panel'><table><thead><tr><th>Asset ID</th><th>Location</th><th>Type</th><th>Capacity</th><th>Expiry</th><th>Days left</th><th>Maintenance decision</th><th>Last inspection</th><th></th></tr></thead><tbody>{rows or '<tr><td colspan=9>No matching extinguishers.</td></tr>'}</tbody></table></div><p>Decision logic: expired = replace now · 0–30 days = urgent · 31–90 days = plan replacement · 91–180 days = monitor.</p>"


def form(existing: dict[str, str] | None = None, error: str = "") -> str:
    existing = existing or {field:"" for field in FIELDS}
    labels = {"asset_id":"Asset ID", "location":"Location", "type":"Extinguisher type", "capacity_kg":"Capacity (kg)", "manufacture_date":"Manufacture date", "expiry_date":"Expiry date", "last_inspection":"Last inspection"}
    inputs = ""
    for field in FIELDS:
        kind = "date" if "date" in field else ("number" if field == "capacity_kg" else "text")
        locked = " readonly" if field == "asset_id" and existing["asset_id"] else ""
        inputs += f"<label>{labels[field]}</label><input required name='{field}' type='{kind}' value='{html.escape(existing[field])}'{locked}>"
    heading = "Edit extinguisher" if existing["asset_id"] else "Add extinguisher"
    error_html = f"<p class='expired' style='padding:10px'>{html.escape(error)}</p>" if error else ""
    return f"<h2>{heading}</h2>{error_html}<form method='post' action='/save'>{inputs}<div class='actions'><button>Save record</button><a class='button secondary' href='/'>Cancel</a></div></form>"


class App(BaseHTTPRequestHandler):
    def send_html(self, content: str, code: int = 200) -> None:
        body = page(content)
        self.send_response(code); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self) -> None:
        if self.path.startswith("/static/"):
            file_path = ROOT / parsed.path.lstrip("/")

            if file_path.exists():
                content_type = "text/plain" 
                if file_path.suffix == ".css":
                    content_type = "text/css"
                elif file_path.suffix == ".js":
                    content_type = "application/javascript"
                elif file_path.suffix == ".png":
                    content_type = "image/png"

                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.end_headers()

                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())

                return
        
        parsed = urlparse(self.path); params = parse_qs(parsed.query)
        if parsed.path == "/": self.send_html(dashboard(params.get("q", [""])[0], params.get("notice", [""])[0]))
        elif parsed.path == "/add": self.send_html(form())
        elif parsed.path == "/edit":
            asset_id = params.get("id", [""])[0]
            item = next((row for row in get_assets() if row["asset_id"] == asset_id), None)
            self.send_html(form(item) if item else "<h2>Record not found</h2>", 200 if item else 404)
        else: self.send_error(404)
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0")); values = parse_qs(self.rfile.read(length).decode())
        item = {field: values.get(field, [""])[0].strip() for field in FIELDS}
        try:
            if not all(item.values()): raise ValueError("Please complete every field.")
            float(item["capacity_kg"])
            for field in ("manufacture_date", "expiry_date", "last_inspection"): datetime.strptime(item[field], "%Y-%m-%d")
            if item["expiry_date"] <= item["manufacture_date"]: raise ValueError("Expiry date must be after manufacture date.")
            data = get_assets(); match = next((i for i,row in enumerate(data) if row["asset_id"] == item["asset_id"]), None)
            if match is None: data.append(item)
            else: data[match] = item
            save_assets(data)
            self.send_response(303); self.send_header("Location", "/?notice=Record+saved+successfully"); self.end_headers()
        except ValueError as error: self.send_html(form(item, str(error)), 400)
    def log_message(self, fmt: str, *args: object) -> None: pass


if __name__ == "__main__":
    print("FIRE-PMIS is running at http://localhost:8000")
    ThreadingHTTPServer(("localhost", 8000), App).serve_forever()

