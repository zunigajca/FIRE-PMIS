from dataclasses import dataclass


@dataclass
class Extinguisher:

    asset_id: str
    building: str
    floor: str
    room: str
    location: str

    type: str
    capacity_kg: float

    manufacturer: str

    manufacture_date: str
    installation_date: str

    expiry_date: str

    last_inspection: str