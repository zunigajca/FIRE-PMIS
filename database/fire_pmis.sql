PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL
);

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
    FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE
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
    FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE
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
    FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE
);
