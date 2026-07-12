from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "mock_extinguishers.json"


def get_assets():
    """Return all extinguisher records."""
    if not DATA_FILE.exists():
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_assets(data):
    """Save all extinguisher records."""
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def get_asset(asset_id):
    assets = get_assets()

    for asset in assets:
        if asset["asset_id"] == asset_id:
            return asset

    return None

def add_asset(asset):
    assets = get_assets()
    assets.append(asset)
    save_assets(assets)


def update_asset(asset_id, updated_asset):
    assets = get_assets()

    for index, asset in enumerate(assets):
        if asset["asset_id"] == asset_id:
            assets[index] = updated_asset
            break

    save_assets(assets)


def delete_asset(asset_id):
    assets = get_assets()

    assets = [
        asset
        for asset in assets
        if asset["asset_id"] != asset_id
    ]

    save_assets(assets)