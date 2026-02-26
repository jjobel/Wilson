# Carlike — Free Car GPS Navigation

A Progressive Web App that turns your phone into a car-optimized GPS navigator. Built for vehicles without Apple CarPlay or Android Auto (like the 2017 Toyota Corolla SE).

**100% free — no API keys, no accounts, no subscriptions.**

## Quick Start

### Option 1: Run Locally

```bash
cd car-gps
python3 -m http.server 8000
```

Open your phone browser (same WiFi) to `http://<your-computer-ip>:8000`

### Option 2: Host for Free

Upload the `car-gps/` folder to any static host:
- [Netlify](https://netlify.com) — drag and drop the folder
- [Vercel](https://vercel.com) — connect your repo
- [GitHub Pages](https://pages.github.com) — push to `gh-pages` branch

Then open the URL on your phone.

## How to Use

1. **Open the app** on your phone browser
2. **Allow location access** when prompted
3. **Search** for a destination in the search bar
4. **Tap a result** — route appears on the map
5. **Tap "Start"** — turn-by-turn voice navigation begins
6. **Mount your phone** on your dashboard and drive

### Install as an App

For the best experience, install Carlike to your home screen:

- **iPhone**: Open in Safari → tap Share → "Add to Home Screen"
- **Android**: Open in Chrome → tap the install banner or Menu → "Add to Home Screen"

This makes it launch full-screen like a native app.

## Features

- Dark-mode map optimized for dashboard viewing
- Real-time GPS tracking with blue position dot
- Turn-by-turn voice directions
- Automatic rerouting when you go off-route
- Search any address worldwide
- Landscape and portrait support
- Works offline (cached map tiles and app shell)
- No accounts, no tracking, no ads

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Maps | [Leaflet.js](https://leafletjs.com) + [CartoDB Dark Matter](https://carto.com/basemaps) tiles |
| Routing | [OSRM](http://project-osrm.org) (Open Source Routing Machine) |
| Geocoding | [Nominatim](https://nominatim.openstreetmap.org) (OpenStreetMap) |
| GPS | Web Geolocation API |
| Voice | Web Speech Synthesis API |
| Offline | Service Worker + Cache API |

All data comes from open-source providers. Your GPS data stays on your device.

## Phone Mounting Tips for 2017 Toyota Corolla SE

The Corolla SE has a clean dashboard area above the center console. Good mount options:

- **Vent clip mount** ($10-15) — clips to the center air vents, easy to reach
- **Suction cup dash mount** ($10-15) — sticks to the smooth area below the windshield
- **CD slot mount** ($10) — slides into the CD player slot (if you don't use CDs)

## Want Actual CarPlay on Your Console Screen?

If you'd rather have Google Maps / Apple Maps on your car's built-in console screen (like CarPlay), you need a hardware upgrade since the 2017 Corolla SE doesn't support CarPlay natively:

- **VLine CarPlay System** (~$250) — plugs behind your stereo, adds wireless CarPlay + Android Auto to your existing screen
- **Beat-Sonic IF-02AEP** (~$200) — wired CarPlay interface for Toyota Entune
- **Aftermarket head unit** (Pioneer, Kenwood, Sony — $200-$400 + install) — full screen replacement with built-in CarPlay

## License

MIT — free to use, modify, and share.
