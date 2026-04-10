import requests
import numpy as np


# -------------------------
# 1. Geocode (text → lat/lng)
# -------------------------
def geocode(address: str):
    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": address,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "eta-app"
    }

    res = requests.get(url, params=params, headers=headers).json()

    if not res:
        return None

    lat = float(res[0]["lat"])
    lng = float(res[0]["lon"])

    return lat, lng


# -------------------------
# 2. Haversine distance
# -------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371

    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2

    return 2 * R * np.arcsin(np.sqrt(a))


# -------------------------
# 3. Feature builder
# -------------------------
def build_features(
    store_coords,
    user_coords,
    traffic: str,
    time_of_day: str,
    weather: str,
    prep_time: float,
    courier_exp: float,
    vehicle: str
):
    # base distance
    base_distance = haversine(
        store_coords[0], store_coords[1],
        user_coords[0], user_coords[1]
    )

    # road approximation
    adjusted_distance = base_distance * 1.3

    # traffic multiplier
    traffic_map = {
        "Low": 0.9,
        "Medium": 1.2,
        "High": 1.5
    }

    traffic_mult = traffic_map.get(traffic, 1.2)

    effective_distance = adjusted_distance * traffic_mult

    # optional derived feature (useful for model later)
    speed_kmh = 25 if vehicle.lower() in ["bike", "scooter"] else 20
    est_travel_time = (effective_distance / speed_kmh) * 60

    return {
        "Distance_km": effective_distance,
        "Preparation_Time_min": prep_time,
        "Courier_Experience_yrs": courier_exp,
        "Weather": weather,
        "Traffic_Level": traffic,
        "Time_of_Day": time_of_day,
        "Vehicle_Type": vehicle
        # keep only features your model was trained on
    }