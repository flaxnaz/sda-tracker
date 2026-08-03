"""
SGP4 propagation and geometric close-approach screening for a curated
real object set. Where Space-Track reports an official CDM for a pair,
that Pc is preferred; otherwise a geometric miss-distance is reported
without inventing a probability figure.
"""
from datetime import datetime, timedelta, timezone
import numpy as np
from sgp4.api import Satrec, jday

SCREEN_WINDOW_HOURS = 24
SCREEN_STEP_SECONDS = 30
CLOSE_APPROACH_KM = 5.0


def satrec_from_gp(gp_record):
    """Build an SGP4 Satrec from a Space-Track GP-class JSON record."""
    return Satrec.twoline2rv(gp_record["TLE_LINE1"], gp_record["TLE_LINE2"])


def propagate_eci_km(satrec, when_utc):
    jd, fr = jday(
        when_utc.year, when_utc.month, when_utc.day,
        when_utc.hour, when_utc.minute, when_utc.second + when_utc.microsecond / 1e6,
    )
    err, r, v = satrec.sgp4(jd, fr)
    if err != 0:
        return None
    return np.array(r), np.array(v)


def screen_close_approaches(gp_records, window_hours=SCREEN_WINDOW_HOURS,
                             step_s=SCREEN_STEP_SECONDS, threshold_km=CLOSE_APPROACH_KM):
    """
    Propagate every object in gp_records forward over the screening
    window and flag pairs whose minimum separation drops below
    threshold_km. This is a geometric screen, not an official
    covariance-based Pc -- reported as miss distance only unless an
    official CDM Pc for the same pair is separately available.
    """
    satrecs = {}
    for rec in gp_records:
        try:
            satrecs[rec["NORAD_CAT_ID"]] = satrec_from_gp(rec)
        except Exception:
            continue

    ids = list(satrecs.keys())
    n_steps = int((window_hours * 3600) / step_s)
    now = datetime.now(timezone.utc)
    times = [now + timedelta(seconds=i * step_s) for i in range(n_steps)]

    positions = {i: [] for i in ids}
    for t in times:
        for oid, sat in satrecs.items():
            result = propagate_eci_km(sat, t)
            positions[oid].append(result[0] if result else None)

    close_approaches = []
    for i_idx in range(len(ids)):
        for j_idx in range(i_idx + 1, len(ids)):
            a, b = ids[i_idx], ids[j_idx]
            min_dist = None
            min_t_idx = None
            for k in range(n_steps):
                pa, pb = positions[a][k], positions[b][k]
                if pa is None or pb is None:
                    continue
                d = float(np.linalg.norm(pa - pb))
                if min_dist is None or d < min_dist:
                    min_dist = d
                    min_t_idx = k
            if min_dist is not None and min_dist <= threshold_km:
                close_approaches.append({
                    "a": a,
                    "b": b,
                    "miss_distance_km": round(min_dist, 3),
                    "tca_hours_from_now": round(min_t_idx * step_s / 3600, 2),
                    "source": "geometric_screen",
                })
    return close_approaches


def tle_age_hours(gp_record, now=None):
    """
    Real proxy for propagation uncertainty: hours since the TLE epoch.
    SGP4 position error grows roughly with time-since-epoch (typically
    on the order of a few km/day for LEO); this is reported directly
    rather than fabricated as a covariance sigma.
    """
    now = now or datetime.now(timezone.utc)
    epoch = datetime.strptime(gp_record["EPOCH"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return round((now - epoch).total_seconds() / 3600, 2)
