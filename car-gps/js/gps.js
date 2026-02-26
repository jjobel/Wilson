/* gps.js — Geolocation tracking */

const GPS = (() => {
  let watchId = null;
  let lastPos = null;
  let lastTimestamp = 0;

  function computeHeading(prev, curr) {
    if (!prev) return null;
    const dLng = (curr.lng - prev.lng) * Math.PI / 180;
    const lat1 = prev.lat * Math.PI / 180;
    const lat2 = curr.lat * Math.PI / 180;
    const y = Math.sin(dLng) * Math.cos(lat2);
    const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLng);
    let bearing = Math.atan2(y, x) * 180 / Math.PI;
    return (bearing + 360) % 360;
  }

  function startTracking(callback) {
    if (!navigator.geolocation) {
      console.error('Geolocation not supported');
      return;
    }

    watchId = navigator.geolocation.watchPosition(
      (position) => {
        const { latitude, longitude, accuracy, heading, speed } = position.coords;
        const now = Date.now();

        const pos = { lat: latitude, lng: longitude, accuracy };

        // Use device heading if available, otherwise compute from movement
        if (heading !== null && heading !== undefined && !isNaN(heading)) {
          pos.heading = heading;
        } else if (lastPos && (now - lastTimestamp > 1000)) {
          const dist = distanceBetween(lastPos.lat, lastPos.lng, latitude, longitude);
          if (dist > 5) { // Only compute heading if moved > 5 meters
            pos.heading = computeHeading(lastPos, pos);
          } else if (lastPos.heading !== undefined) {
            pos.heading = lastPos.heading;
          }
        } else if (lastPos && lastPos.heading !== undefined) {
          pos.heading = lastPos.heading;
        }

        pos.speed = (speed !== null && speed >= 0) ? speed : null;

        lastPos = pos;
        lastTimestamp = now;

        callback(pos);
      },
      (err) => {
        console.error('GPS error:', err.message);
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 2000,
      }
    );
  }

  function stopTracking() {
    if (watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
      watchId = null;
    }
  }

  function getCurrentPosition() {
    return new Promise((resolve, reject) => {
      if (lastPos) {
        resolve(lastPos);
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          resolve({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
            heading: pos.coords.heading,
            speed: pos.coords.speed,
          });
        },
        reject,
        { enableHighAccuracy: true, timeout: 10000 }
      );
    });
  }

  function getLastPosition() {
    return lastPos;
  }

  // Haversine distance in meters
  function distanceBetween(lat1, lng1, lat2, lng2) {
    const R = 6371000;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  return { startTracking, stopTracking, getCurrentPosition, getLastPosition, distanceBetween };
})();
