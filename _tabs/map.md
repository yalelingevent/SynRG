---
# the default layout is 'page'
icon: fas fa-map
order: 3
---

<div id="map" style="height: 100vh; width: 100%;"></div>

<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

<script>
  var map = L.map('map').setView([41.314, -72.923], 16);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  L.marker([41.31449214372543, -72.92274587937527]).addTo(map)
    .bindPopup('Yale Linguistics Department')
    .openPopup();
</script>