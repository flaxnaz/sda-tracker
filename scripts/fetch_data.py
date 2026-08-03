"""
Builds data.json consumed by the frontend dashboard.

LEO and MEO/GEO tabs: real Space-Track GP (TLE) data, propagated with
SGP4, screened geometrically for close approaches; official CDM Pc is
attached where Space-Track reports one for the same pair.

Lunar tab: real CR3BP propagation of a representative NRHO, consistent
with the thesis this project extends. No conjunction events are
fabricated for this tab since no real tracked lunar debris catalog
exists to screen against.
"""
import json
from datetime import datetime, timezone

from spacetrack_client import SpaceTrackClient
from propagate_screen import screen_close_approaches, tle_age_hours
from nrho_propagate import propagate_nrho, to_km

# Curated real object sets. NORAD catalog IDs are real; edit freely to
# track different objects.
LEO_NORAD_IDS = [
    25544,   # ISS
    43013,   # NOAA-20
    39084,   # Landsat 8
    49260,   # Sentinel-6
]
LEO_PERIGEE_BAND_KM = (380, 620)   # used to pull nearby catalog objects/debris for screening

GNSS_GEO_NORAD_IDS = [
    32711, 32260, 41328,   # GPS block examples
    28129, 28921,          # GEO comms examples
]


def build_leo_block(client):
    primary = client.gp_by_norad_ids(LEO_NORAD_IDS)
    try:
        nearby = client.gp_by_altitude_band(*LEO_PERIGEE_BAND_KM, limit=300)
    except Exception as exc:
        print(f"Altitude-band query failed, continuing with primary objects only: {exc}")
        nearby = []
    catalog = {rec["NORAD_CAT_ID"]: rec for rec in (primary + nearby)}
    records = list(catalog.values())

    conjunctions = screen_close_approaches(records, window_hours=24, threshold_km=5.0)

    objects = [{
        "norad_id": rec["NORAD_CAT_ID"],
        "name": rec.get("OBJECT_NAME", "UNKNOWN"),
        "object_type": rec.get("OBJECT_TYPE", "UNKNOWN"),
        "perigee_km": float(rec.get("PERIGEE", 0) or 0),
        "apogee_km": float(rec.get("APOGEE", 0) or 0),
        "inclination_deg": float(rec.get("INCLINATION", 0) or 0),
        "tle_age_hours": tle_age_hours(rec),
    } for rec in records]

    return {"objects": objects, "conjunctions": conjunctions}


def build_meo_geo_block(client):
    records = client.gp_by_norad_ids(GNSS_GEO_NORAD_IDS)
    conjunctions = screen_close_approaches(records, window_hours=24, threshold_km=50.0)

    objects = [{
        "norad_id": rec["NORAD_CAT_ID"],
        "name": rec.get("OBJECT_NAME", "UNKNOWN"),
        "object_type": rec.get("OBJECT_TYPE", "UNKNOWN"),
        "perigee_km": float(rec.get("PERIGEE", 0) or 0),
        "apogee_km": float(rec.get("APOGEE", 0) or 0),
        "inclination_deg": float(rec.get("INCLINATION", 0) or 0),
        "tle_age_hours": tle_age_hours(rec),
    } for rec in records]

    return {"objects": objects, "conjunctions": conjunctions}


def build_lunar_block():
    ic = [1.0215, 0.0, -0.1821, 0.0, -0.1033, 0.0]
    period = 1.51
    t, y = propagate_nrho(ic, period, n_points=200)
    pos_km = to_km(y[:3]).T.tolist()
    return {
        "trajectory_km": pos_km,
        "period_nondim": period,
        "note": (
            "Real CR3BP DOP853 propagation of a representative southern "
            "L2 NRHO, same methodology as the author's thesis. No real "
            "tracked lunar debris catalog exists, so no conjunctions "
            "are reported for this regime."
        ),
    }


def main():
    client = SpaceTrackClient()
    client.login()

    data = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "leo": build_leo_block(client),
        "meo_geo": build_meo_geo_block(client),
        "lunar": build_lunar_block(),
    }

    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Wrote data.json: {len(data['leo']['objects'])} LEO objects, "
          f"{len(data['meo_geo']['objects'])} MEO/GEO objects, "
          f"{len(data['leo']['conjunctions'])} LEO close approaches, "
          f"{len(data['meo_geo']['conjunctions'])} MEO/GEO close approaches")


if __name__ == "__main__":
    main()
