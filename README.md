# FIRE-PMIS

FIRE-PMIS is a web-based predictive maintenance information system for BFP Sta. Ana, Manila. It centralizes equipment records and the manually entered inspection, maintenance, and usage histories required for maintenance decision support.

## Delivered capstone scope

- Role-based login for Administrator, Maintenance Personnel, and Station Supervisor accounts.
- Centralized registry for fire engines, water pumps, breathing apparatus, critical tools, and other equipment.
- Per-equipment inspection, maintenance, repair/parts, and deployment/operating-hour logs.
- Explainable Low, Medium, and High risk classification using a decision-tree-style rule model based on equipment age, usage, inspection findings, repair history, operational status, and inspection due dates.
- Dashboard alerts, readiness overview, charts, analytics, recommendations, and CSV report export.
- Simulated starter records, consistent with the study limitation that sample data may be used while historical records are limited.

The predictive output is advisory. It supports, but does not replace, a maintenance officer’s professional decision. The system uses only manually entered records; it has no real-time IoT/sensor functionality.

## Run locally

```bash
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

| Role | Username | Password |
| --- | --- | --- |
| Administrator | `admin` | `admin123` |
| Maintenance Personnel | `maintenance` | `maintenance123` |
| Station Supervisor (read-only) | `supervisor` | `supervisor123` |

The self-contained prototype stores its working data in `instance/fire_pmis.sqlite3`. This makes the capstone immediately runnable without server configuration. For a production deployment matching the paper’s MySQL target, migrate the included table design to MySQL and set managed database credentials before deployment.
