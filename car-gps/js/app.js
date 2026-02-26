/* app.js — Main application controller */

const App = (() => {
  // State: idle | preview | navigating | arrived
  let state = 'idle';
  let destination = null;
  let currentPos = null;
  let announcedApproaching = false;

  // DOM elements
  const $searchPanel = document.getElementById('search-panel');
  const $dirBanner = document.getElementById('direction-banner');
  const $dirIcon = document.getElementById('direction-icon');
  const $dirInstruction = document.getElementById('direction-instruction');
  const $dirDistance = document.getElementById('direction-distance');
  const $routeSummary = document.getElementById('route-summary');
  const $routeDuration = document.getElementById('route-duration');
  const $routeDistance = document.getElementById('route-distance');
  const $startNavBtn = document.getElementById('start-nav-btn');
  const $cancelRouteBtn = document.getElementById('cancel-route-btn');
  const $turnListPanel = document.getElementById('turn-list-panel');
  const $turnList = document.getElementById('turn-list');
  const $closeTurns = document.getElementById('close-turns');
  const $arrivedOverlay = document.getElementById('arrived-overlay');
  const $btnCenter = document.getElementById('btn-center');
  const $btnTurns = document.getElementById('btn-turns');
  const $btnVoice = document.getElementById('btn-voice');
  const $btnStopNav = document.getElementById('btn-stop-nav');
  const $btnDismissArrived = document.getElementById('btn-dismiss-arrived');

  function init() {
    CarMap.init();

    // Start GPS tracking
    GPS.startTracking(onPositionUpdate);

    // Search
    Search.init(onDestinationSelected);

    // Button handlers
    $btnCenter.addEventListener('click', () => {
      if (currentPos) {
        CarMap.centerOnUser(currentPos.lat, currentPos.lng);
      }
    });

    $startNavBtn.addEventListener('click', startNavigation);
    $cancelRouteBtn.addEventListener('click', cancelRoute);
    $closeTurns.addEventListener('click', () => { $turnListPanel.style.display = 'none'; });

    $btnTurns.addEventListener('click', () => {
      $turnListPanel.style.display = $turnListPanel.style.display === 'none' ? '' : 'none';
    });

    $btnVoice.addEventListener('click', () => {
      Voice.setEnabled(!Voice.isEnabled());
      $btnVoice.classList.toggle('voice-off', !Voice.isEnabled());
    });

    $btnStopNav.addEventListener('click', stopNavigation);
    $btnDismissArrived.addEventListener('click', dismissArrived);
  }

  function onPositionUpdate(pos) {
    currentPos = pos;
    CarMap.setUserPosition(pos.lat, pos.lng, pos.accuracy, pos.heading);

    if (state === 'navigating') {
      updateNavigation(pos);
    }
  }

  async function onDestinationSelected(dest) {
    destination = dest;
    CarMap.setDestination(dest.lat, dest.lng, dest.name);

    if (!currentPos) {
      try {
        currentPos = await GPS.getCurrentPosition();
      } catch {
        Voice.announce('Unable to get current location.');
        return;
      }
    }

    try {
      const route = await Router.calculateRoute(
        currentPos.lat, currentPos.lng,
        dest.lat, dest.lng
      );
      showRoutePreview(route);
    } catch (err) {
      console.error('Routing error:', err);
      Voice.announce('Could not calculate route.');
    }
  }

  function showRoutePreview(route) {
    state = 'preview';

    // Draw route on map
    CarMap.drawRoute(route.geometry);
    CarMap.fitRoute();

    // Show summary
    $routeDuration.textContent = Router.formatDuration(route.duration);
    $routeDistance.textContent = Router.formatDistance(route.distance);
    $routeSummary.style.display = '';

    // Build turn list
    buildTurnList(route.steps);
    $btnTurns.style.display = '';

    // Hide search results
    Search.clearSearch();
  }

  function buildTurnList(steps) {
    $turnList.innerHTML = '';
    steps.forEach((step, i) => {
      const li = document.createElement('li');
      if (i === Router.getCurrentStepIndex()) li.classList.add('active');
      li.innerHTML = `
        <span class="turn-step-icon">${step.icon}</span>
        <span class="turn-step-text">${step.instruction}</span>
        <span class="turn-step-dist">${Router.formatDistance(step.distance)}</span>
      `;
      $turnList.appendChild(li);
    });
  }

  function startNavigation() {
    state = 'navigating';
    announcedApproaching = false;

    $routeSummary.style.display = 'none';
    $searchPanel.style.display = 'none';
    $dirBanner.style.display = '';
    $btnStopNav.style.display = '';

    CarMap.setFollowUser(true);
    if (currentPos) {
      CarMap.centerOnUser(currentPos.lat, currentPos.lng);
    }

    // Announce first step
    const route = Router.getCurrentRoute();
    if (route && route.steps.length > 0) {
      const firstStep = route.steps[0];
      updateDirectionBanner(firstStep, firstStep.distance);
      Voice.announce(firstStep.instruction);
    }
  }

  function updateNavigation(pos) {
    const progress = Router.checkProgress(pos.lat, pos.lng);
    if (!progress) return;

    switch (progress.event) {
      case 'step_reached': {
        announcedApproaching = false;
        const step = progress.step;

        // Check if we've arrived
        if (step.maneuverType === 'arrive') {
          arriveAtDestination();
          return;
        }

        updateDirectionBanner(step, step.distance);
        buildTurnList(Router.getCurrentRoute().steps);
        Voice.announce(step.instruction);
        break;
      }

      case 'on_route': {
        const step = progress.step;
        updateDirectionBanner(step, progress.distanceToManeuver);

        // Announce approaching turn at ~200m
        if (progress.distanceToManeuver < 200 && !announcedApproaching) {
          announcedApproaching = true;
          Voice.announceDirection(step, progress.distanceToManeuver);
        }
        // Reset announcement flag for next step
        if (progress.distanceToManeuver > 250) {
          announcedApproaching = false;
        }
        break;
      }

      case 'off_route': {
        Voice.announceReroute();
        reroute();
        break;
      }
    }
  }

  async function reroute() {
    if (!currentPos || !destination) return;
    try {
      const route = await Router.calculateRoute(
        currentPos.lat, currentPos.lng,
        destination.lat, destination.lng
      );
      CarMap.drawRoute(route.geometry);
      buildTurnList(route.steps);
      if (route.steps.length > 0) {
        updateDirectionBanner(route.steps[0], route.steps[0].distance);
      }
    } catch (err) {
      console.error('Reroute failed:', err);
    }
  }

  function updateDirectionBanner(step, distance) {
    $dirIcon.textContent = step.icon;
    $dirInstruction.textContent = step.instruction;
    $dirDistance.textContent = Router.formatDistance(distance);
  }

  function arriveAtDestination() {
    state = 'arrived';
    Voice.announceArrival();
    $dirBanner.style.display = 'none';
    $arrivedOverlay.style.display = '';
  }

  function stopNavigation() {
    state = 'idle';
    Router.clearRoute();
    CarMap.clearRoute();
    CarMap.clearDestination();
    destination = null;

    $dirBanner.style.display = 'none';
    $routeSummary.style.display = 'none';
    $turnListPanel.style.display = 'none';
    $btnTurns.style.display = 'none';
    $btnStopNav.style.display = 'none';
    $searchPanel.style.display = '';
    Search.clearSearch();
  }

  function cancelRoute() {
    stopNavigation();
  }

  function dismissArrived() {
    $arrivedOverlay.style.display = 'none';
    stopNavigation();
  }

  // Boot
  document.addEventListener('DOMContentLoaded', init);
})();
