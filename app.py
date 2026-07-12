from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for
)
import services.storage as storage

from services.predictor import get_dashboard_counts

app = Flask(__name__)


@app.route("/")
def dashboard():

    assets = storage.get_assets()
    counts = get_dashboard_counts(assets)

    return render_template(
        "dashboard.html",
        assets=assets,
        counts=counts
    )


@app.route("/assets")
def assets():

    query = request.args.get("q", "").strip().lower()

    data = storage.get_assets()

    if query:
        data = [
            asset
            for asset in data
            if query in asset["asset_id"].lower()
            or query in asset["location"].lower()
            or query in asset["type"].lower()
        ]

    return render_template(
        "assets.html",
        assets=data,
        query=query
    )


@app.route("/assets/add", methods=["GET", "POST"])
def add_asset_page():

    if request.method == "POST":

        asset = {

            "asset_id": request.form["asset_id"],
            "location": request.form["location"],
            "type": request.form["type"],
            "capacity_kg": request.form["capacity_kg"],
            "manufacture_date": request.form["manufacture_date"],
            "expiry_date": request.form["expiry_date"],
            "last_inspection": request.form["last_inspection"]

        }

        storage.add_asset(asset)

        return redirect(url_for("assets"))

    return render_template(
        "asset_form.html",
        title="Add Asset",
        asset=None
    )

@app.route("/assets/edit/<asset_id>", methods=["GET", "POST"])
def edit_asset_page(asset_id):

    asset = storage.get_asset(asset_id)

    if asset is None:
        return "Asset not found", 404

    if request.method == "POST":

        updated = {

            "asset_id": asset_id,
            "location": request.form["location"],
            "type": request.form["type"],
            "capacity_kg": request.form["capacity_kg"],
            "manufacture_date": request.form["manufacture_date"],
            "expiry_date": request.form["expiry_date"],
            "last_inspection": request.form["last_inspection"]

        }

        storage.update_asset(asset_id, updated)

        return redirect(url_for("assets"))

    return render_template(
        "asset_form.html",
        title="Edit Asset",
        asset=asset
    )

@app.route("/assets/delete/<asset_id>")
def delete_asset_page(asset_id):

    storage.delete_asset(asset_id)

    return redirect(url_for("assets"))

if __name__ == "__main__":
    app.run(debug=True)