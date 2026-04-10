let selectedLat = null;
let selectedLng = null;

const restaurant = [19.0596, 72.8295];

var map = L.map('map').setView(restaurant, 12);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png')
.addTo(map);

// Restaurant marker
L.marker(restaurant).addTo(map)
.bindPopup("Store Location")
.openPopup();

let userMarker = null;
let line = null;
let zoneCircle = null;

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

    const address = document.getElementById("address").value.trim();

    if (!address) {
        alert("Enter an address");
        return;
    }

    let data = {
        address: address,

        Weather: document.getElementById("weather").value,
        Traffic_Level: document.getElementById("traffic").value,
        Time_of_Day: document.getElementById("time").value,
        Vehicle_Type: document.getElementById("vehicle").value,

        Preparation_Time_min: parseFloat(document.getElementById("prep").value),
        Courier_Experience_yrs: parseFloat(document.getElementById("exp").value),

        Delivery_person_Age: parseFloat(document.getElementById("age").value),
        Delivery_person_Ratings: parseFloat(document.getElementById("rating").value),
        Type_of_order: document.getElementById("order").value,
        Type_of_vehicle: document.getElementById("vehicle").value.toLowerCase()
    };

    try {
        let res = await fetch("/predict", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data)
        });

        let result = await res.json();

        if (result.error) {
            alert(result.error);
            return;
        }

        // Update UI
        document.getElementById("distance").innerText = result.distance;

        document.getElementById("svr1").innerText = result.svr_dataset1;
        document.getElementById("rf1").innerText  = result.rf_dataset1;

        document.getElementById("svr2").innerText = result.svr_dataset2;
        document.getElementById("rf2").innerText  = result.rf_dataset2;
        document.getElementById("zone").innerText = result.delivery_zone;

        renderRoute(result.lat, result.lng, result.delivery_zone);
        map.setView([result.lat, result.lng], 13);

    } catch (err) {
        console.error(err);
        alert("Error getting prediction");
    }
}