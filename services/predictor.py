from datetime import date, datetime


def _days_since(value):
    if not value:
        return 999
    return (date.today() - datetime.strptime(value, "%Y-%m-%d").date()).days


def assess_equipment(item):
    """Interpretable decision-tree risk classifier based on manually logged history.

    The branches use the inputs named in the approved scope: age, usage hours,
    deployment frequency, inspection findings, repair history and due dates.
    """
    inspections, maintenance, usage = item.get("inspections", []), item.get("maintenance", []), item.get("usage", [])
    latest = inspections[0] if inspections else None
    hours = sum(float(log["operating_hours"] or 0) for log in usage)
    deployments = sum(int(log["deployment_count"] or 0) for log in usage)
    age_years = max(0, _days_since(item.get("purchase_date")) / 365.25)
    overdue = not latest or _days_since(latest.get("inspection_date")) > 90 or (latest.get("next_due_date") and _days_since(latest["next_due_date"]) > 0)
    condition = (latest or {}).get("condition", "Unknown")
    score = 0
    reasons = []
    # Decision tree branches, ordered from critical conditions to normal monitoring.
    if item["operational_status"] in ("Out of Service", "Under Maintenance") or condition in ("Failed", "Needs Repair"):
        score += 55; reasons.append("reported operational or inspection issue")
    if overdue:
        score += 25; reasons.append("inspection is overdue or missing")
    if age_years >= 7:
        score += 15; reasons.append("equipment age exceeds seven years")
    if hours >= 100 or deployments >= 30:
        score += 15; reasons.append("high recorded operational use")
    if len(maintenance) >= 3:
        score += 10; reasons.append("repeated maintenance history")
    if score >= 55:
        risk, recommendation = "High", "Prioritize inspection and corrective maintenance before deployment."
    elif score >= 25:
        risk, recommendation = "Medium", "Schedule preventive maintenance and verify condition within 30 days."
    else:
        risk, recommendation = "Low", "Continue routine monitoring and the planned inspection schedule."
    return {"risk": risk, "score": min(score, 100), "recommendation": recommendation, "reasons": reasons or ["current records show no elevated risk indicators"], "inspection_overdue": bool(overdue)}


def build_analytics(equipment):
    risks = {"Low": 0, "Medium": 0, "High": 0}
    categories = {}
    for item in equipment:
        risks[item["assessment"]["risk"]] += 1
        categories[item["category"]] = categories.get(item["category"], 0) + 1
    return {"total": len(equipment), "risk": risks, "categories": categories, "operational": sum(x["operational_status"] == "Operational" for x in equipment)}
