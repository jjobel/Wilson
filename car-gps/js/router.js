/* router.js — OSRM routing & turn-by-turn directions */

const Router = (() => {
  const OSRM_URL = 'https://router.project-osrm.org/route/v1/driving';

  // Maneuver type → icon mapping
  const MANEUVER_ICONS = {
    'turn-left': '⬅️',
    'turn-right': '➡️',
    'turn-sharp-left': '↩️',
    'turn-sharp-right': '↪️',
    'turn-slight-left': '↰',
    'turn-slight-right': '↱',
    'straight': '⬆️',
    'depart': '🚗',
    'arrive': '🏁',
    'merge-left': '↰',
    'merge-right': '↱',
    'ramp-left': '↰',
    'ramp-right': '↱',
    'fork-left': '↰',
    'fork-right': '↱',
    'roundabout': '🔄',
    'rotary': '🔄',
    'uturn': '↩️',
  };

  let currentRoute = null;
  let currentStepIndex = 0;
  let stepPositions = [];

  async function calculateRoute(startLat, startLng, endLat, endLng) {
    const url = `${OSRM_URL}/${startLng},${startLat};${endLng},${endLat}?overview=full&geometries=geojson&steps=true&annotations=false`;

    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`OSRM error: ${resp.status}`);
    const data = await resp.json();

    if (!data.routes || data.routes.length === 0) {
      throw new Error('No route found');
    }

    const route = data.routes[0];
    const steps = route.legs[0].steps.map((step) => {
      const mod = step.maneuver.modifier || '';
      const type = step.maneuver.type || '';
      const key = mod ? `${type}-${mod}`.replace('turn-', '') : type;

      return {
        instruction: step.maneuver.instruction || formatInstruction(type, mod, step.name),
        distance: step.distance,
        duration: step.duration,
        maneuverType: type,
        modifier: mod,
        icon: MANEUVER_ICONS[key] || MANEUVER_ICONS[type] || '⬆️',
        location: step.maneuver.location, // [lng, lat]
      };
    });

    currentRoute = {
      geometry: route.geometry,
      distance: route.distance,
      duration: route.duration,
      steps,
    };
    currentStepIndex = 0;
    stepPositions = steps.map((s) => ({ lat: s.location[1], lng: s.location[0] }));

    return currentRoute;
  }

  function formatInstruction(type, modifier, streetName) {
    const street = streetName ? ` onto ${streetName}` : '';
    switch (type) {
      case 'depart': return `Head${street}`;
      case 'arrive': return 'You have arrived';
      case 'turn':
        if (modifier.includes('left')) return `Turn left${street}`;
        if (modifier.includes('right')) return `Turn right${street}`;
        return `Continue${street}`;
      case 'merge': return `Merge${street}`;
      case 'ramp': return `Take the ramp${street}`;
      case 'fork':
        if (modifier.includes('left')) return `Keep left${street}`;
        if (modifier.includes('right')) return `Keep right${street}`;
        return `Continue${street}`;
      case 'roundabout': return `Enter the roundabout${street}`;
      default: return `Continue${street}`;
    }
  }

  function checkProgress(currentLat, currentLng) {
    if (!currentRoute || currentStepIndex >= stepPositions.length) return null;

    const nextStep = stepPositions[currentStepIndex];
    const dist = GPS.distanceBetween(currentLat, currentLng, nextStep.lat, nextStep.lng);

    // Check if we've reached the current step maneuver point
    if (dist < 50 && currentStepIndex < stepPositions.length - 1) {
      currentStepIndex++;
      return {
        event: 'step_reached',
        stepIndex: currentStepIndex,
        step: currentRoute.steps[currentStepIndex],
        distanceToNext: null,
      };
    }

    // Check off-route (> 150m from the maneuver line)
    const nearestDist = distanceToRouteLine(currentLat, currentLng);
    if (nearestDist > 150) {
      return { event: 'off_route' };
    }

    return {
      event: 'on_route',
      stepIndex: currentStepIndex,
      step: currentRoute.steps[currentStepIndex],
      distanceToManeuver: dist,
    };
  }

  function distanceToRouteLine(lat, lng) {
    if (!currentRoute || !currentRoute.geometry) return 0;
    const coords = currentRoute.geometry.coordinates;
    let minDist = Infinity;
    for (let i = 0; i < coords.length; i++) {
      const d = GPS.distanceBetween(lat, lng, coords[i][1], coords[i][0]);
      if (d < minDist) minDist = d;
    }
    return minDist;
  }

  function getCurrentRoute() {
    return currentRoute;
  }

  function getCurrentStepIndex() {
    return currentStepIndex;
  }

  function clearRoute() {
    currentRoute = null;
    currentStepIndex = 0;
    stepPositions = [];
  }

  function formatDistance(meters) {
    if (meters >= 1609.34) {
      return (meters / 1609.34).toFixed(1) + ' mi';
    }
    if (meters >= 160.934) {
      return (meters / 1609.34).toFixed(1) + ' mi';
    }
    return Math.round(meters * 3.28084) + ' ft';
  }

  function formatDuration(seconds) {
    if (seconds < 60) return '< 1 min';
    const mins = Math.round(seconds / 60);
    if (mins < 60) return `${mins} min`;
    const hrs = Math.floor(mins / 60);
    const rem = mins % 60;
    return rem > 0 ? `${hrs} hr ${rem} min` : `${hrs} hr`;
  }

  return {
    calculateRoute,
    checkProgress,
    getCurrentRoute,
    getCurrentStepIndex,
    clearRoute,
    formatDistance,
    formatDuration,
    MANEUVER_ICONS,
  };
})();
