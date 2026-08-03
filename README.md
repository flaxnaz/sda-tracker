# SDA Live Tracker

Live space domain awareness dashboard: real Space-Track GP (TLE) data for LEO and MEO/GEO objects, SGP4 propagation, geometric close-approach screening, and a real CR3BP-propagated Near Rectilinear Halo Orbit for the lunar tab, using the same DOP853 methodology as the author's UNSW MEng thesis.

**Live dashboard:** deploy `index.html` via GitHub Pages, or open it locally against `data.json`.

## What's real vs. what isn't

- **LEO / MEO-GEO objects and orbital elements**: real, pulled live from Space-Track's GP class endpoint.
- **Close approaches**: real geometric screening (minimum separation over a 24h SGP4-propagated window). Where Space-Track has a public CDM for the same pair, its officially reported Pc is preferred; otherwise only a miss distance is reported, not a fabricated probability.
- **TLE age**: real, reported directly as a proxy for propagation uncertainty rather than an invented covariance sigma.
- **Lunar trajectory**: a real numerically propagated NRHO (CR3BP, DOP853, rtol 1e-9), same approach as [nrho-visibility](https://github.com/flaxnaz/nrho-visibility). No conjunction events are shown for this tab because there is no real, publicly tracked lunar debris catalog to screen against.

## Setup

```bash
pip install -r requirements.txt
```

Set Space-Track credentials as environment variables (never commit these):

```bash
export SPACETRACK_USER="you@example.com"
export SPACETRACK_PASS="your-password"
python scripts/fetch_data.py
```

## Deployment status

This repo is live at `github.com/flaxnaz/sda-tracker`. The workflow runs every 6 hours and commits a fresh `data.json` automatically; trigger it manually from the Actions tab if you want an update sooner.

To adapt this for your own Space-Track account:

1. Fork or clone this repo.
2. In your fork's Settings → Secrets and variables → Actions, add `SPACETRACK_USER` and `SPACETRACK_PASS`.
3. Enable GitHub Pages (Settings → Pages → deploy from `main`, root) to serve `index.html` live.

## Stack

Python (sgp4, scipy, requests), Space-Track REST API, GitHub Actions, vanilla JS/canvas frontend.
