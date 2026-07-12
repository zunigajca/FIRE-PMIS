from datetime import datetime, date


def get_status(expiry_date: str):

    days = (
        datetime.strptime(expiry_date, "%Y-%m-%d").date()
        - date.today()
    ).days

    if days < 0:
        return "Expired — replace now", days, "expired"

    if days <= 30:
        return "Replace urgently", days, "urgent"

    if days <= 90:
        return "Plan replacement", days, "plan"

    if days <= 180:
        return "Monitor", days, "monitor"

    return "Serviceable", days, "good"


def get_dashboard_counts(assets):

    counts = {
        "total": len(assets),
        "healthy": 0,
        "monitor": 0,
        "plan": 0,
        "urgent": 0,
        "expired": 0,
    }

    for asset in assets:

        decision, _, _ = get_status(asset["expiry_date"])

        if decision.startswith("Expired"):
            counts["expired"] += 1

        elif decision.startswith("Replace"):
            counts["urgent"] += 1

        elif decision.startswith("Plan"):
            counts["plan"] += 1

        elif decision == "Monitor":
            counts["monitor"] += 1

        else:
            counts["healthy"] += 1

    return counts