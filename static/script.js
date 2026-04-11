let selectedLat = null;
let selectedLng = null;

console.log("[script] loaded v5");

let restaurant = [19.0596, 72.8295];
let restaurantMarker = null;

var map = L.map('map').setView(restaurant, 12);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png')
.addTo(map);

function renderRestaurantMarker(lat, lng) {
    restaurant = [lat, lng];

    if (restaurantMarker) {
        map.removeLayer(restaurantMarker);
    }

    restaurantMarker = L.marker(restaurant).addTo(map)
        .bindPopup("Store Location")
        .openPopup();
}

renderRestaurantMarker(restaurant[0], restaurant[1]);

let userMarker = null;
let line = null;
let zoneCircle = null;

function getEl(id) {
    return document.getElementById(id);
}

function getRequiredValue(id) {
    const el = getEl(id);
    if (!el) {
        throw new Error(`Missing element: ${id}`);
    }
    return el.value;
}

function setContextModeUI() {
    const modeEl = getEl("context_mode");
    const autoBlock = getEl("auto_context");
    const manualBlock = getEl("manual_context");
    if (!modeEl || !manualBlock || !autoBlock) {
        console.warn("[ui] context mode elements not found");
        return;
    }
    const mode = modeEl.value;
    autoBlock.style.display = mode === "auto" ? "block" : "none";
    manualBlock.style.display = mode === "manual" ? "block" : "none";
}

document.addEventListener("DOMContentLoaded", () => {
    const modeSelect = getEl("context_mode");
    if (modeSelect) {
        modeSelect.addEventListener("change", setContextModeUI);
    } else {
        console.warn("[ui] context_mode not found on DOMContentLoaded");
    }
    setContextModeUI();
});

function getZoneColor(zone) {
    if (zone === "fast") return "#22c55e";
    if (zone === "slow") return "#ef4444";
    return "#f59e0b";
}

function renderRoute(lat, lng, zone = "medium") {
    selectedLat = lat;
    selectedLng = lng;

    const zoneColor = getZoneColor(zone);

    if (userMarker) map.removeLayer(userMarker);
    if (line) map.removeLayer(line);
    if (zoneCircle) map.removeLayer(zoneCircle);

    userMarker = L.marker([lat, lng]).addTo(map)
        .bindPopup(`Delivery Zone: ${zone}`);
    line = L.polyline([restaurant, [lat, lng]], { color: zoneColor, weight: 4 }).addTo(map);
    zoneCircle = L.circle([lat, lng], {
        radius: 350,
        color: zoneColor,
        fillColor: zoneColor,
        fillOpacity: 0.2
    }).addTo(map);
}

// Select location on map
map.on('click', function(e) {
    renderRoute(e.latlng.lat, e.latlng.lng);
});


// Predict function
async function predict() {
    console.log("[predict] button clicked");

    let data;
    try {
        const address = getRequiredValue("address").trim();
        const storeAddress = getRequiredValue("store_address").trim();
        console.log("[predict] address:", address);

        if (!address) {
            console.warn("[predict] missing address");
            alert("Enter an address");
            return;
        }

        const contextMode = (getEl("context_mode")?.value || "auto");

        data = {
            store_address: storeAddress,
            address: address,
            context_mode: contextMode,
            Vehicle_Type: getRequiredValue("vehicle"),

            Preparation_Time_min: parseFloat(getRequiredValue("prep")),
            Courier_Experience_yrs: parseFloat(getRequiredValue("exp")),

            Delivery_person_Age: parseFloat(getRequiredValue("age")),
            Delivery_person_Ratings: parseFloat(getRequiredValue("rating")),
            Type_of_order: getRequiredValue("order"),
            Type_of_vehicle: getRequiredValue("vehicle").toLowerCase()
        };

        if (data.context_mode === "manual") {
            data.Weather = getRequiredValue("weather_manual");
            data.Traffic_Level = getRequiredValue("traffic_manual");
            data.Time_of_Day = getRequiredValue("time_manual");
        }
    } catch (err) {
        console.error("[predict] input/DOM error:", err);
        alert(err.message || "Missing input field in page.");
        return;
    }

    console.log("[predict] payload:", data);

    try {
        let res = await fetch("/predict", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data)
        });

        console.log("[predict] response status:", res.status);

        let result = await res.json();
        console.log("[predict] response body:", result);

        if (!res.ok) {
            alert(result.error || "Prediction failed");
            return;
        }

        if (result.error) {
            alert(result.error);
            return;
        }

        // Update UI
        document.getElementById("distance").innerText = result.distance;
        document.getElementById("store_used").innerText = result.store_label || `${result.store_lat}, ${result.store_lng}`;

        document.getElementById("svr1").innerText = result.svr_dataset1;
        document.getElementById("rf1").innerText  = result.rf_dataset1;

        document.getElementById("svr2").innerText = result.svr_dataset2;
        document.getElementById("rf2").innerText  = result.rf_dataset2;
        document.getElementById("zone").innerText = result.delivery_zone;
        document.getElementById("weather_auto").innerText = result.weather;
        document.getElementById("traffic_auto").innerText = result.traffic_level;
        document.getElementById("time_auto").innerText = result.time_of_day;

        if (typeof result.store_lat === "number" && typeof result.store_lng === "number") {
            renderRestaurantMarker(result.store_lat, result.store_lng);
        }

        renderRoute(result.lat, result.lng, result.delivery_zone);
        map.setView([result.lat, result.lng], 13);
        console.log("[predict] UI updated successfully");

    } catch (err) {
        console.error("[predict] request failed:", err);
        alert("Error getting prediction. Check backend logs.");
    }
}