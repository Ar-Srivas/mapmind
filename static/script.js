/**
 * Geocodes an address to latitude and longitude using OpenStreetMap Nominatim API.
 * @param {string} address - The address string to geocode.
 * @returns {Promise<{lat: number, lon: number}|null>} The coordinates or null if not found.
 */
async function geocode(address) {
    // ...
}

/**
 * Calculates the distance between two geographical points using the haversine formula.
 * @param {number} lat1 - Latitude of first point.
 * @param {number} lon1 - Longitude of first point.
 * @param {number} lat2 - Latitude of second point.
 * @param {number} lon2 - Longitude of second point.
 * @returns {number} Distance in kilometers.
 */
function haversine(lat1, lon1, lat2, lon2) {
    // ...
}
