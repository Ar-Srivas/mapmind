from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import joblib
import pandas as pd
import numpy as np
import requests
import os
import traceback
from datetime import datetime
from sklearn.cluster import KMeans
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "../static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "../template"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

 
svr1 = joblib.load(os.path.join(BASE_DIR, "../models/svr_dataset1.pkl"))
svr2 = joblib.load(os.path.join(BASE_DIR, "../models/svr_dataset2.pkl"))
rf1  = joblib.load(os.path.join(BASE_DIR, "../models/rf_model1.pkl"))
rf2  = joblib.load(os.path.join(BASE_DIR, "../models/rf_model2.pkl"))


@app.get("/health")
def read_root():
    return {"status": "healthy"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))


def build_delivery_zone_clusterer():
    df = pd.read_csv(os.path.join(BASE_DIR, "../notebooks/deliverytime.csv"))
    df["Distance_km"] = haversine(
        df["Restaurant_latitude"],
        df["Restaurant_longitude"],
        df["Delivery_location_latitude"],
        df["Delivery_location_longitude"],
    )

    X = df[["Distance_km", "Time_taken(min)"]].dropna()
    model = KMeans(n_clusters=3, random_state=42, n_init=10)
    model.fit(X)

    centers = model.cluster_centers_
    sorted_cluster_ids = np.argsort(centers[:, 1])

    zone_names = ["fast", "medium", "slow"]
    zone_by_cluster = {
        int(sorted_cluster_ids[0]): zone_names[0],
        int(sorted_cluster_ids[1]): zone_names[1],
        int(sorted_cluster_ids[2]): zone_names[2],
    }
    return model, zone_by_cluster


zone_model, zone_map = build_delivery_zone_clusterer()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
GEOCODE_CACHE = {}


@app.on_event("startup")
def log_startup_configuration():
    key_state = "present" if OPENWEATHER_API_KEY else "missing"
    key_preview = f"{OPENWEATHER_API_KEY[:4]}..." if OPENWEATHER_API_KEY else "<empty>"
    print(f"[startup] OPENWEATHER_API_KEY={key_state} preview={key_preview}")
    print("[startup] routes ready: /, /predict, /health")


def geocode(address):
    print(f"[geocode] address={address}")
    cache_key = address.strip().lower()
    if cache_key in GEOCODE_CACHE:
        print(f"[geocode] cache hit for {address}")
        return GEOCODE_CACHE[cache_key]

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
    }
    headers = {
        "User-Agent": "eta-app"
    }

    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"[geocode] http status={res.status_code}")
        results = res.json()
    except Exception as ex:
        print(f"[geocode] request failed: {ex}")
        return None

    if not results:
        print("[geocode] no results")
        return None

    print(f"[geocode] lat={results[0]['lat']} lon={results[0]['lon']}")
    coords = float(results[0]["lat"]), float(results[0]["lon"])
    GEOCODE_CACHE[cache_key] = coords
    return coords


def resolve_store_location(data):
    default_store_lat, default_store_lng = 19.0596, 72.8295
    store_address = str(data.get("store_address", "")).strip()

    if not store_address:
        print(f"[store] using default store coords lat={default_store_lat} lng={default_store_lng}")
        return default_store_lat, default_store_lng, "default"

    print(f"[store] store_address={store_address}")
    coords = geocode(store_address)
    if coords is None:
        print("[store] geocode failed, falling back to default store coords")
        return default_store_lat, default_store_lng, store_address

    store_lat, store_lng = coords
    print(f"[store] resolved lat={store_lat} lng={store_lng}")
    return store_lat, store_lng, store_address


def normalize_weather(api_main: str, wind_speed: float) -> str:
    main = (api_main or "").lower()

    if main in {"rain", "drizzle", "thunderstorm"}:
        return "Rainy"
    if main in {"mist", "fog", "haze", "smoke", "dust", "sand", "ash"}:
        return "Foggy"
    if wind_speed >= 8:
        return "Windy"
    return "Clear"


def get_weather(lat: float, lng: float) -> str:
    if not OPENWEATHER_API_KEY:
        print("[weather] OPENWEATHER_API_KEY missing, using fallback=Clear")
        return "Clear"

    current_url = "https://api.openweathermap.org/data/2.5/weather"
    current_params = {
        "lat": lat,
        "lon": lng,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    }

    try:
        res = requests.get(current_url, params=current_params, timeout=10)
        data = res.json()
        if not res.ok:
            print(f"[weather] current2.5 failed status={res.status_code} body={data}")
            return "Clear"

        api_main = data.get("weather", [{}])[0].get("main", "")
        wind_speed = float(data.get("wind", {}).get("speed", 0.0))
        weather = normalize_weather(api_main, wind_speed)
        print(f"[weather] current2.5 ok api_main={api_main} wind={wind_speed} mapped={weather}")
        return weather
    except Exception as ex:
        print(f"[weather] current2.5 exception: {ex}")
        return "Clear"


def get_time_of_day(hour: int) -> str:
    if 5 <= hour < 12:
        return "Morning"
    if 12 <= hour < 17:
        return "Afternoon"
    if 17 <= hour < 21:
        return "Evening"
    return "Night"


def estimate_traffic(hour: int) -> str:
    if 8 <= hour <= 11 or 17 <= hour <= 21:
        return "High"
    if 12 <= hour <= 16:
        return "Medium"
    return "Low"


@app.post("/predict")
async def predict(data: dict):
    try:
        print("[predict] request received")
        print(f"[predict] payload keys={list(data.keys())}")
        store_lat, store_lng, store_label = resolve_store_location(data)
        coords = geocode(data["address"])
        if coords is None:
            print("[predict] geocode failed")
            return {"error": "Location not found"}

        lat, lng = coords

        current_hour = datetime.now().hour
        context_mode = str(data.get("context_mode", "auto")).lower()
        print(f"[predict] context_mode={context_mode} hour={current_hour}")

        if context_mode == "manual":
            weather = data.get("Weather", "Clear")
            traffic = data.get("Traffic_Level", "Low")
            time_of_day = data.get("Time_of_Day", get_time_of_day(current_hour))
        else:
            weather = get_weather(lat, lng)
            time_of_day = get_time_of_day(current_hour)
            traffic = estimate_traffic(current_hour)

        air_distance = haversine(store_lat, store_lng, lat, lng)
        if air_distance < 3:
            distance = air_distance * 1.5
        elif air_distance < 5:
            distance = air_distance * 1.3
        else:
            distance = air_distance * 1.2
        print(f"[predict] air_distance={air_distance:.3f} adjusted_distance={distance:.3f}")

        df1 = pd.DataFrame([{
            "Distance_km": distance,
            "Preparation_Time_min": float(data["Preparation_Time_min"]),
            "Courier_Experience_yrs": float(data["Courier_Experience_yrs"]),
            "Weather": weather,
            "Traffic_Level": traffic,
            "Time_of_Day": time_of_day,
            "Vehicle_Type": data["Vehicle_Type"]
        }])

        df2 = pd.DataFrame([{
            "Delivery_person_Age": float(data["Delivery_person_Age"]),
            "Delivery_person_Ratings": float(data["Delivery_person_Ratings"]),
            "Distance_km": distance,
            "Type_of_order": data["Type_of_order"],
            "Type_of_vehicle": data["Type_of_vehicle"]
        }])

        eta_svr1 = svr1.predict(df1)[0]
        eta_rf1 = rf1.predict(df1)[0]
        eta_svr2 = svr2.predict(df2)[0]
        eta_rf2 = rf2.predict(df2)[0]
        avg_eta = float(np.mean([eta_svr1, eta_rf1, eta_svr2, eta_rf2]))
        print(f"[predict] eta_svr1={eta_svr1:.2f} eta_rf1={eta_rf1:.2f} eta_svr2={eta_svr2:.2f} eta_rf2={eta_rf2:.2f}")

        zone_features = pd.DataFrame([{
            "Distance_km": distance,
            "Time_taken(min)": avg_eta,
        }])
        cluster_id = int(zone_model.predict(zone_features)[0])
        delivery_zone = zone_map[cluster_id]
        print(f"[predict] cluster_id={cluster_id} zone={delivery_zone}")

        return {
            "distance": round(distance, 2),
            "lat": lat,
            "lng": lng,
            "store_lat": store_lat,
            "store_lng": store_lng,
            "store_label": store_label,
            "svr_dataset1": round(eta_svr1, 2),
            "rf_dataset1": round(eta_rf1, 2),
            "svr_dataset2": round(eta_svr2, 2),
            "rf_dataset2": round(eta_rf2, 2),
            "delivery_zone": delivery_zone,
            "weather": weather,
            "traffic_level": traffic,
            "time_of_day": time_of_day,
            "context_mode": context_mode
        }
    except Exception as ex:
        print(f"[predict] failed: {ex}")
        traceback.print_exc()
        return {"error": "Prediction failed. Check backend logs."}