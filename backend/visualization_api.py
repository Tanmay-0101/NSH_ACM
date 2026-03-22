from fastapi import APIRouter
from math import sqrt, atan2, asin, degrees

from state_manager import satellites, debris, collision_warnings, get_current_timestamp

router = APIRouter()

R_EARTH = 6378.137


def eci_to_lat_lon_alt(position):
    x, y, z = position

    r = sqrt(x * x + y * y + z * z)

    if r == 0:
        return 0.0, 0.0, 0.0

    lat = degrees(asin(z / r))
    lon = degrees(atan2(y, x))
    alt = r - R_EARTH

    return round(lat, 3), round(lon, 3), round(alt, 3)


def satellite_status(sat):
    return "NOMINAL"


@router.get("/api/visualization/snapshot")
def get_snapshot():
    satellite_list = []

    for sat_id, sat in satellites.items():
        lat, lon, alt = eci_to_lat_lon_alt(sat["position"])

        satellite_list.append({
            "id": sat_id,
            "lat": lat,
            "lon": lon,
            "fuel_kg": round(sat.get("fuel_kg", 0.0), 3),
            "status": satellite_status(sat)
        })

    debris_cloud = []

    for deb_id, deb in debris.items():
        lat, lon, alt = eci_to_lat_lon_alt(deb["position"])
        debris_cloud.append([deb_id, lat, lon, alt])

    return {
        "timestamp": get_current_timestamp(),
        "satellites": satellite_list,
        "debris_cloud": debris_cloud,
        "active_warnings": collision_warnings
    }