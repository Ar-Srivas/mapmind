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
from sklearn.cluster import KMeans

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
    return templates.TemplateResponse("index.html", {"request": request})

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


def geocode(address):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
    }
    headers = {
        "User-Agent": "eta-app"
    }

    res = requests.get(url, params=params, headers=headers, timeout=10)
    results = res.json()

    if not results:
        return None

    return float(results[0]["lat"]), float(results[0]["lon"])


@app.post("/predict")
async def predict(data: dict):
    coords = geocode(data["address"])
    if coords is None:
        return {"error": "Location not found"}

    lat, lng = coords
    restaurant_lat, restaurant_lng = 19.0596, 72.8295

    # distance = haversine(restaurant_lat, restaurant_lng, lat, lng)

    air_distance= haversine(restaurant_lat, restaurant_lng, lat, lng) # easy fix to, else have to use an api to get directions
    if air_distance<3:
        distance = air_distance * 1.5
    elif air_distance<5:
        distance = air_distance * 1.3
    else:
        distance = air_distance * 1.2


    df1 = pd.DataFrame([{
        "Distance_km": distance,
        "Preparation_Time_min": float(data["Preparation_Time_min"]),
        "Courier_Experience_yrs": float(data["Courier_Experience_yrs"]),
        "Weather": data["Weather"],
        "Traffic_Level": data["Traffic_Level"],
        "Time_of_Day": data["Time_of_Day"],
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

    zone_features = pd.DataFrame([{
        "Distance_km": distance,
        "Time_taken(min)": avg_eta,
    }])
    cluster_id = int(zone_model.predict(zone_features)[0])
    delivery_zone = zone_map[cluster_id]

    return {
        "distance": round(distance, 2),
        "lat": lat,
        "lng": lng,
        "svr_dataset1": round(eta_svr1, 2),
        "rf_dataset1": round(eta_rf1, 2),
        "svr_dataset2": round(eta_svr2, 2),
        "rf_dataset2": round(eta_rf2, 2),
        "delivery_zone": delivery_zone
    }