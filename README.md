## MapMind: ML-Powered Delivery ETA Predictor

**MapMind** is a full-stack intelligence layer for food delivery logistics. It leverages an ensemble of Machine Learning models to predict delivery arrival times (ETA) by synthesizing geospatial data, real-time weather, and historical delivery patterns.

The system moves beyond simple distance-based estimates by employing a "brain" of four concurrent models and a KMeans clustering engine to categorize delivery zones.

---

## Features

* **Ensemble Prediction Engine**: Utilizes four pre-trained models (2x Support Vector Regression, 2x Random Forest) to provide a robust, averaged ETA.
* **Dynamic Geocoding**: Integrated OpenStreetMap (Nominatim) support for converting addresses to precise coordinates.
* **Weather Integration**: Real-time weather fetching via OpenWeather API (optional; falls back to "Clear" weather if `OPENWEATHER_API_KEY` is not set).
* **Interactive Spatial UI**: A Leaflet-powered map interface allowing users to pick delivery points and visualize store-to-customer routes.
* **Intelligent Zoning**: Automatically assigns deliveries to `fast`, `medium`, or `slow` zones using a KMeans clusterer trained on historical delivery data.
* **Context-Aware**: Supports both "Auto" context (fetching live data) and "Manual" overrides for courier attributes and vehicle types.

---

## Tech Stack

* **Backend**: FastAPI (Python), Jinja2 Templates
* **Machine Learning**: Scikit-learn, Pandas, NumPy, Joblib
* **Frontend**: Leaflet.js, JavaScript (ES6+), CSS3
* **Data/APIs**: OpenStreetMap (Nominatim), OpenWeather API

---

## 📁 Project Structure

```text
mapmind/
├── backend/
│   ├── app.py                # Main FastAPI application & ML logic
│   └── services/
│       └── location_service.py # Geospatial & feature engineering helpers
├── models/                   # Pre-trained .pkl model files (SVR, RF, KMeans)
├── notebooks/                # Jupyter notebooks & training datasets
│   ├── deliverytime.csv      # Training data for KMeans clustering
│   ├── Food_Delivery_Times.csv
│   └── *.ipynb               # Model comparison & training notebooks
├── static/                   # CSS, JS (Leaflet logic), and assets
├── template/                 # Jinja2 HTML templates (index.html)
├── data/                     # Additional data directory
├── interpretations.md        # Model performance analysis
├── pyproject.toml            # Dependency management
├── .env                      # Environment variables (OPENWEATHER_API_KEY)
└── main.py                   # Application entry point

```

---

## How It Works

1. **Feature Engineering**: The system computes a "road-adjusted" distance using the Haversine formula multiplied by empirical road-path factors ($1.2\times$ to $1.5\times$).
2. **Model Inference**:
* **Group 1**: SVR and RF models trained on feature set A.
* **Group 2**: SVR and RF models trained on feature set B.
* The final ETA is the arithmetic mean of these four outputs.


3. **Clustering**: The backend builds a KMeans model on startup by reading `notebooks/deliverytime.csv`. It clusters deliveries into `fast`, `medium`, or `slow` zones based on distance vs. delivery time.
4. **Response**: The UI renders a breakdown of individual model predictions, the assigned zone, and the calculated route on the map.

---

## Quick Start

### 1. Prerequisites

- Python 3.11+ (see `.python-version`)
- `OPENWEATHER_API_KEY` environment variable (optional; falls back to "Clear" weather if not set)

### 2. Installation

```bash
# Install uv (modern Python package manager) if not already installed
pip install uv

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies from pyproject.toml
uv pip install -e .
```

Alternatively, with pip:
```bash
pip install -e .
```

### 3. Environment Setup

Create a `.env` file in the project root:
```
OPENWEATHER_API_KEY=your_api_key_here
```

If not provided, the app will use a fallback weather value.

### 4. Running the App

```bash
cd backend
uvicorn app:app --reload --port 8000
```

Access the interface at `http://localhost:8000`.

---


## Troubleshooting

- **"Model not found"**: Ensure all `.pkl` files exist in `models/`.
- **Geocoding fails**: Nominatim has rate limits; cached results are stored in memory. For production, consider Redis or persistent storage.
- **Weather shows "Clear"**: Either `OPENWEATHER_API_KEY` is missing or the API call timed out. Check logs.
- **Map not rendering**: Verify Leaflet CDN is accessible; check browser console for errors.

---