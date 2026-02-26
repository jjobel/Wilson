/* map.js — Leaflet map setup and management */

const CarMap = (() => {
  let map;
  let userMarker;
  let headingMarker;
  let accuracyCircle;
  let routeLayer;
  let destinationMarker;
  let followUser = true;

  const TILE_URL = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
  const TILE_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>';

  function init() {
    map = L.map('map', {
      zoomControl: false,
      attributionControl: true,
      center: [39.8283, -98.5795], // Center of US
      zoom: 4,
      maxZoom: 19,
      minZoom: 3,
    });

    L.tileLayer(TILE_URL, {
      attribution: TILE_ATTR,
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(map);

    // Disable follow mode on user drag
    map.on('dragstart', () => { followUser = false; });

    return map;
  }

  function setUserPosition(lat, lng, accuracy, heading) {
    const latlng = L.latLng(lat, lng);

    if (!userMarker) {
      const dotIcon = L.divIcon({
        className: '',
        html: '<div class="gps-dot"></div>',
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      });
      userMarker = L.marker(latlng, { icon: dotIcon, zIndexOffset: 1000 }).addTo(map);
    } else {
      userMarker.setLatLng(latlng);
    }

    // Heading indicator
    if (heading !== null && heading !== undefined) {
      if (!headingMarker) {
        const headIcon = L.divIcon({
          className: '',
          html: `<div class="gps-heading" style="transform: translateX(-50%) rotate(0deg);"></div>`,
          iconSize: [20, 24],
          iconAnchor: [10, 35],
        });
        headingMarker = L.marker(latlng, { icon: headIcon, zIndexOffset: 999 }).addTo(map);
      }
      headingMarker.setLatLng(latlng);
      const el = headingMarker.getElement();
      if (el) {
        const arrow = el.querySelector('.gps-heading');
        if (arrow) arrow.style.transform = `translateX(-50%) rotate(${heading}deg)`;
      }
    }

    // Accuracy circle
    if (accuracy) {
      if (!accuracyCircle) {
        accuracyCircle = L.circle(latlng, {
          radius: accuracy,
          className: 'gps-accuracy',
          interactive: false,
        }).addTo(map);
      } else {
        accuracyCircle.setLatLng(latlng);
        accuracyCircle.setRadius(accuracy);
      }
    }

    if (followUser) {
      map.setView(latlng, Math.max(map.getZoom(), 15), { animate: true });
    }
  }

  function centerOnUser(lat, lng) {
    followUser = true;
    map.setView([lat, lng], Math.max(map.getZoom(), 16), { animate: true });
  }

  function setDestination(lat, lng, name) {
    if (destinationMarker) {
      map.removeLayer(destinationMarker);
    }
    const icon = L.divIcon({
      className: '',
      html: `<div style="
        width: 16px; height: 16px;
        background: #f72585; border: 3px solid #fff;
        border-radius: 50%; box-shadow: 0 0 10px rgba(247,37,133,0.6);
      "></div>`,
      iconSize: [16, 16],
      iconAnchor: [8, 8],
    });
    destinationMarker = L.marker([lat, lng], { icon })
      .bindPopup(name || 'Destination')
      .addTo(map);
  }

  function drawRoute(geojson) {
    clearRoute();
    routeLayer = L.geoJSON(geojson, {
      style: {
        color: '#4cc9f0',
        weight: 6,
        opacity: 0.85,
        lineCap: 'round',
        lineJoin: 'round',
      },
    }).addTo(map);
  }

  function fitRoute() {
    if (routeLayer) {
      map.fitBounds(routeLayer.getBounds(), { padding: [60, 60] });
    }
  }

  function clearRoute() {
    if (routeLayer) {
      map.removeLayer(routeLayer);
      routeLayer = null;
    }
  }

  function clearDestination() {
    if (destinationMarker) {
      map.removeLayer(destinationMarker);
      destinationMarker = null;
    }
  }

  function setFollowUser(val) {
    followUser = val;
  }

  function getMap() {
    return map;
  }

  return {
    init,
    setUserPosition,
    centerOnUser,
    setDestination,
    drawRoute,
    fitRoute,
    clearRoute,
    clearDestination,
    setFollowUser,
    getMap,
  };
})();
