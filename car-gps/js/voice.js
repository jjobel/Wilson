/* voice.js — Web Speech API voice guidance */

const Voice = (() => {
  let enabled = true;
  let lastAnnounced = '';
  let lastAnnouncedTime = 0;

  function announce(text) {
    if (!enabled) return;
    if (!window.speechSynthesis) return;

    // Don't repeat the same announcement within 10 seconds
    const now = Date.now();
    if (text === lastAnnounced && (now - lastAnnouncedTime) < 10000) return;

    // Cancel any current speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.9;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    utterance.lang = 'en-US';

    window.speechSynthesis.speak(utterance);
    lastAnnounced = text;
    lastAnnouncedTime = now;
  }

  function announceDirection(step, distanceMeters) {
    if (!step) return;
    const dist = Router.formatDistance(distanceMeters);
    const text = `In ${dist}, ${step.instruction}`;
    announce(text);
  }

  function announceArrival() {
    announce('You have arrived at your destination.');
  }

  function announceReroute() {
    announce('Recalculating route.');
  }

  function setEnabled(val) {
    enabled = val;
    if (!val && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }

  function isEnabled() {
    return enabled;
  }

  return { announce, announceDirection, announceArrival, announceReroute, setEnabled, isEnabled };
})();
