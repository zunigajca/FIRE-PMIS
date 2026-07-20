from datetime import date, datetime, timedelta
from functools import wraps
import csv
import io
import os
import sqlite3

from flask import Flask, flash, g, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from services.predictor import assess_equipment, build_analytics


app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get("SECRET_KEY", "change-this-before-deployment"), DATABASE=os.path.join(app.instance_path, "fire_pmis.sqlite3"))
os.makedirs(app.instance_path, exist_ok=True)


def db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def ensure_table_columns(connection, table_name, columns):
    existing_columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}
    for column_sql in columns:
        column_name = column_sql.split()[0]
        if column_name not in existing_columns:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


@app.teardown_appcontext
def close_db(_error=None):
    connection = g.pop("db", None)
    if connection:
        connection.close()


def init_db():
    connection = db()
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY,
            asset_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            purchase_date TEXT,
            operational_status TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            serial_number TEXT,
            manufacturer TEXT,
            model TEXT,
            warranty_expiry TEXT,
            supplier TEXT,
            purchase_cost REAL DEFAULT 0,
            service_interval_days INTEGER DEFAULT 0,
            criticality TEXT DEFAULT 'Standard'
        );
        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY,
            equipment_id INTEGER NOT NULL,
            inspection_date TEXT NOT NULL,
            condition TEXT NOT NULL,
            findings TEXT,
            inspector TEXT NOT NULL,
            next_due_date TEXT,
            severity_level TEXT DEFAULT 'Normal',
            FOREIGN KEY(equipment_id) REFERENCES equipment(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS maintenance (
            id INTEGER PRIMARY KEY,
            equipment_id INTEGER NOT NULL,
            maintenance_date TEXT NOT NULL,
            maintenance_type TEXT NOT NULL,
            description TEXT NOT NULL,
            parts_replaced TEXT,
            assigned_personnel TEXT NOT NULL,
            cost REAL DEFAULT 0,
            work_order_no TEXT,
            status TEXT DEFAULT 'Completed',
            FOREIGN KEY(equipment_id) REFERENCES equipment(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY,
            equipment_id INTEGER NOT NULL,
            usage_date TEXT NOT NULL,
            deployment_count INTEGER NOT NULL DEFAULT 0,
            operating_hours REAL NOT NULL DEFAULT 0,
            purpose TEXT,
            recorded_by TEXT NOT NULL,
            trip_type TEXT DEFAULT 'Routine',
            FOREIGN KEY(equipment_id) REFERENCES equipment(id) ON DELETE CASCADE
        );
    """)
    ensure_table_columns(connection, "equipment", [
        "serial_number TEXT",
        "manufacturer TEXT",
        "model TEXT",
        "warranty_expiry TEXT",
        "supplier TEXT",
        "purchase_cost REAL DEFAULT 0",
        "service_interval_days INTEGER DEFAULT 0",
        "criticality TEXT DEFAULT 'Standard'",
    ])
    ensure_table_columns(connection, "inspections", [
        "severity_level TEXT DEFAULT 'Normal'",
    ])
    ensure_table_columns(connection, "maintenance", [
        "work_order_no TEXT",
        "status TEXT DEFAULT 'Completed'",
    ])
    ensure_table_columns(connection, "usage_logs", [
        "trip_type TEXT DEFAULT 'Routine'",
    ])
    connection.execute("INSERT OR IGNORE INTO users(username,password_hash,role) VALUES (?,?,?)", ("admin", generate_password_hash("admin123"), "Administrator"))
    connection.execute("INSERT OR IGNORE INTO users(username,password_hash,role) VALUES (?,?,?)", ("maintenance", generate_password_hash("maintenance123"), "Maintenance Personnel"))
    connection.execute("INSERT OR IGNORE INTO users(username,password_hash,role) VALUES (?,?,?)", ("supervisor", generate_password_hash("supervisor123"), "Station Supervisor"))

    existing_count = connection.execute("SELECT COUNT(*) FROM equipment").fetchone()[0]
    if existing_count < 8:
        today = date.today()
        samples = [
            ("ENG-001", "Fire Engine 1", "Fire Engine", "BFP Sta. Ana Garage", "2020-01-15", "Operational", "Primary response vehicle", "SN-ENG-001", "Phoenix Motors", "Model X12", "2027-01-15", "BFP Supplies", 420000.0, 180, "Critical"),
            ("PMP-002", "Portable Water Pump", "Water Pump", "Equipment Bay", "2021-06-20", "Operational", "For flood and fire support", "SN-PMP-002", "HydraTech", "WT-220", "2026-06-20", "Municipal Logistics", 120000.0, 90, "Standard"),
            ("BA-003", "SCBA Unit 3", "Breathing Apparatus", "PPE Room", "2022-03-10", "Operational", "Self-contained breathing apparatus", "SN-BA-003", "AeroSafe", "SCBA-3", "2028-03-10", "Fire Protection Depot", 45000.0, 60, "High"),
            ("TOOL-004", "Hydraulic Rescue Tool", "Critical Tool", "Rescue Locker", "2019-11-05", "Under Maintenance", "Awaiting hose inspection", "SN-TOOL-004", "RescueMax", "RHT-9", "2025-11-05", "Emergency Gear Supply", 78000.0, 30, "Critical"),
            ("ENG-005", "Fire Engine 5", "Fire Engine", "Dispatch Yard", "2018-05-12", "Operational", "Reserve response vehicle", "SN-ENG-005", "Ranger Motors", "RM-780", "2026-05-12", "Metro Fire Depot", 510000.0, 210, "Critical"),
            ("PMP-006", "Portable Water Pump 6", "Water Pump", "Operations Storage", "2023-02-14", "Under Maintenance", "Routine pump test backlog", "SN-PMP-006", "FlowMax", "PM-404", "2028-02-14", "Water Support Services", 99000.0, 120, "Standard"),
            ("BA-007", "SCBA Unit 7", "Breathing Apparatus", "Respiratory Locker", "2021-09-18", "Operational", "Used for smoke-diving drills", "SN-BA-007", "AeroSafe", "SCBA-7", "2027-09-18", "Emergency PPE Supply", 52000.0, 45, "High"),
            ("TOOL-008", "Portable Cutter Set", "Critical Tool", "Rescue Bay", "2020-11-01", "Out of Service", "Battery pack replacement pending", "SN-TOOL-008", "CutPro", "CP-21", "2025-11-01", "Rescue gear vendor", 63000.0, 25, "Critical"),
        ]
        for sample in samples:
            connection.execute(
                "INSERT OR IGNORE INTO equipment(asset_code,name,category,location,purchase_date,operational_status,notes,created_at,serial_number,manufacturer,model,warranty_expiry,supplier,purchase_cost,service_interval_days,criticality) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (*sample, today.isoformat())
            )
            equipment_id = connection.execute("SELECT id FROM equipment WHERE asset_code=?", (sample[0],)).fetchone()[0]
            if not connection.execute("SELECT 1 FROM inspections WHERE equipment_id=? LIMIT 1", (equipment_id,)).fetchone():
                condition = "Needs Repair" if sample[0] in {"TOOL-004", "TOOL-008"} else "Good"
                connection.execute("INSERT INTO inspections(equipment_id,inspection_date,condition,findings,inspector,next_due_date,severity_level) VALUES (?,?,?,?,?,?,?)", (equipment_id, (today-timedelta(days=35 if sample[0] in {"TOOL-004", "TOOL-008"} else 12)).isoformat(), condition, "Hydraulic hose shows wear" if sample[0] == "TOOL-004" else "Battery pack replacement pending" if sample[0] == "TOOL-008" else "No defects noted", "Maintenance Officer", (today+timedelta(days=20 if sample[0] in {"TOOL-004", "TOOL-008"} else 78)).isoformat(), "High" if condition != "Good" else "Normal"))
            if not connection.execute("SELECT 1 FROM maintenance WHERE equipment_id=? LIMIT 1", (equipment_id,)).fetchone():
                connection.execute("INSERT INTO maintenance(equipment_id,maintenance_date,maintenance_type,description,parts_replaced,assigned_personnel,cost,work_order_no,status) VALUES (?,?,?,?,?,?,?,?,?)", (equipment_id, (today-timedelta(days=5 if sample[0] in {"TOOL-004", "TOOL-008"} else 18)).isoformat(), "Corrective Repair" if sample[0] in {"TOOL-004", "TOOL-008"} else "Preventive", "Service record" if sample[0] not in {"TOOL-004", "TOOL-008"} else "Field repair and parts replacement", "Hydraulic hose set" if sample[0] == "TOOL-004" else "Battery pack" if sample[0] == "TOOL-008" else "Filter cartridge", "Maintenance Officer", 3500 if sample[0] in {"TOOL-004", "TOOL-008"} else 1200, f"WO-{sample[0]}", "Completed"))
            if not connection.execute("SELECT 1 FROM usage_logs WHERE equipment_id=? LIMIT 1", (equipment_id,)).fetchone():
                connection.execute("INSERT INTO usage_logs(equipment_id,usage_date,deployment_count,operating_hours,purpose,recorded_by,trip_type) VALUES (?,?,?,?,?,?,?)", (equipment_id, (today-timedelta(days=7)).isoformat(), 7 if sample[0] in {"TOOL-004", "TOOL-008"} else 2, 18 if sample[0] in {"TOOL-004", "TOOL-008"} else 4, "Training / response readiness", "Maintenance Officer", "Emergency" if sample[0] in {"TOOL-004", "TOOL-008"} else "Routine"))
    connection.commit()


@app.before_request
def ensure_database():
    init_db()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") not in roles:
                flash("Your role has read-only access to this action.", "error")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def all_equipment():
    rows = db().execute("SELECT * FROM equipment ORDER BY asset_code").fetchall()
    return [equipment_with_assessment(row) for row in rows]


def equipment_with_assessment(row):
    item = dict(row)
    item["inspections"] = [dict(x) for x in db().execute("SELECT * FROM inspections WHERE equipment_id=? ORDER BY inspection_date DESC", (item["id"],)).fetchall()]
    item["maintenance"] = [dict(x) for x in db().execute("SELECT * FROM maintenance WHERE equipment_id=? ORDER BY maintenance_date DESC", (item["id"],)).fetchall()]
    item["usage"] = [dict(x) for x in db().execute("SELECT * FROM usage_logs WHERE equipment_id=? ORDER BY usage_date DESC", (item["id"],)).fetchall()]
    item["assessment"] = assess_equipment(item)
    return item


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = db().execute("SELECT * FROM users WHERE username=?", (request.form["username"].strip(),)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session.update(user_id=user["id"], username=user["username"], role=user["role"])
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    equipment = all_equipment()
    analytics = build_analytics(equipment)
    alerts = [x for x in equipment if x["assessment"]["risk"] == "High" or x["assessment"]["inspection_overdue"]]
    return render_template("dashboard.html", equipment=equipment, analytics=analytics, alerts=alerts[:6])


@app.route("/equipment")
@login_required
def equipment_list():
    query = request.args.get("q", "").strip().lower()
    equipment = all_equipment()
    if query:
        equipment = [x for x in equipment if query in " ".join(str(x[k]).lower() for k in ("asset_code", "name", "category", "location", "operational_status"))]
    return render_template("equipment.html", equipment=equipment, query=query)


@app.route("/equipment/add", methods=["GET", "POST"])
@login_required
@role_required("Administrator", "Maintenance Personnel")
def add_equipment():
    if request.method == "POST":
        values = [request.form[x].strip() for x in ("asset_code", "name", "category", "location", "purchase_date", "operational_status", "notes")]
        extra_values = [
            request.form.get("serial_number", "").strip(),
            request.form.get("manufacturer", "").strip(),
            request.form.get("model", "").strip(),
            request.form.get("warranty_expiry", "").strip(),
            request.form.get("supplier", "").strip(),
            request.form.get("purchase_cost", "") or 0,
            request.form.get("service_interval_days", "") or 0,
            request.form.get("criticality", "Standard").strip() or "Standard",
        ]
        try:
            db().execute(
                "INSERT INTO equipment(asset_code,name,category,location,purchase_date,operational_status,notes,created_at,serial_number,manufacturer,model,warranty_expiry,supplier,purchase_cost,service_interval_days,criticality) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (*values, date.today().isoformat(), *extra_values)
            )
            db().commit(); flash("Equipment registered successfully.", "success")
            return redirect(url_for("equipment_list"))
        except sqlite3.IntegrityError:
            flash("Asset code already exists.", "error")
    return render_template("equipment_form.html", equipment=None)


@app.route("/equipment/<int:equipment_id>", methods=["GET", "POST"])
@login_required
def equipment_detail(equipment_id):
    row = db().execute("SELECT * FROM equipment WHERE id=?", (equipment_id,)).fetchone()
    if not row:
        return "Equipment not found", 404
    if request.method == "POST":
        if session.get("role") not in ("Administrator", "Maintenance Personnel"):
            flash("Your role has read-only access to this action.", "error")
            return redirect(url_for("equipment_detail", equipment_id=equipment_id))
        action = request.form.get("action")
        if action == "inspection":
            db().execute("INSERT INTO inspections(equipment_id,inspection_date,condition,findings,inspector,next_due_date) VALUES (?,?,?,?,?,?)", (equipment_id, request.form["inspection_date"], request.form["condition"], request.form["findings"], session["username"], request.form["next_due_date"]))
        elif action == "maintenance":
            db().execute("INSERT INTO maintenance(equipment_id,maintenance_date,maintenance_type,description,parts_replaced,assigned_personnel,cost) VALUES (?,?,?,?,?,?,?)", (equipment_id, request.form["maintenance_date"], request.form["maintenance_type"], request.form["description"], request.form["parts_replaced"], request.form["assigned_personnel"], request.form["cost"] or 0))
        elif action == "usage":
            db().execute("INSERT INTO usage_logs(equipment_id,usage_date,deployment_count,operating_hours,purpose,recorded_by) VALUES (?,?,?,?,?,?)", (equipment_id, request.form["usage_date"], request.form["deployment_count"] or 0, request.form["operating_hours"] or 0, request.form["purpose"], session["username"]))
        db().commit(); flash("Record saved and risk assessment refreshed.", "success")
        return redirect(url_for("equipment_detail", equipment_id=equipment_id))
    return render_template("equipment_detail.html", equipment=equipment_with_assessment(row), today=date.today().isoformat())


@app.route("/reports")
@login_required
def reports():
    equipment = all_equipment()
    return render_template("reports.html", equipment=equipment, analytics=build_analytics(equipment))


@app.route("/reports/export")
@login_required
def export_report():
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["Asset Code", "Equipment", "Category", "Location", "Status", "Risk Level", "Risk Score", "Recommendation"])
    for item in all_equipment():
        a = item["assessment"]
        writer.writerow([item["asset_code"], item["name"], item["category"], item["location"], item["operational_status"], a["risk"], a["score"], a["recommendation"]])
    data = io.BytesIO(output.getvalue().encode("utf-8-sig")); data.seek(0)
    return send_file(data, mimetype="text/csv", as_attachment=True, download_name=f"fire-pmis-risk-report-{date.today()}.csv")


if __name__ == "__main__":
    app.run(debug=True)
