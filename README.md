# FIRE-PMIS web prototype

A Python web prototype for deciding whether portable fire extinguishers need replacement based on their expiry dates.

## Run

From this folder, run:

```powershell
python web_app.py
```

Then open `http://localhost:8000` in a browser. No extra package is required: it uses Python's built-in web server and a mock JSON database (`mock_extinguishers.json`).

## Decision rules

| Time to expiry | FIRE-PMIS recommendation |
|---|---|
| Already expired | Replace now |
| 0–30 days | Replace urgently |
| 31–90 days | Plan replacement |
| 91–180 days | Monitor |
| More than 180 days | Serviceable |

Use the web dashboard to search, add, and edit records. Changes are stored in the mock JSON database immediately.

## Suggested capstone extensions

- Add QR-code labels for each asset and mobile inspection logging.
- Track pressure-gauge readings, physical condition, inspection history, and service intervals.
- Add role-based accounts for safety officers and maintenance staff.
- Produce monthly replacement forecasts and compliance reports.
