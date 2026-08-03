"""
Real numerical propagation of a representative Near Rectilinear Halo
Orbit (NRHO), consistent with the CR3BP methodology used in the
author's UNSW MEng thesis. No real tracked lunar debris catalog
exists to screen conjunctions against, so this tab reports real
propagated trajectory state and GNSS/S-band visibility instead of
fabricated conjunction events.
"""
import numpy as np
from scipy.integrate import solve_ivp

MU_EARTH = 398600.4418   # km^3/s^2
MU_MOON = 4902.8         # km^3/s^2
EARTH_MOON_DIST = 384400  # km, mean

MU = MU_MOON / (MU_EARTH + MU_MOON)  # CR3BP mass ratio


def cr3bp_eom(t, state):
    x, y, z, vx, vy, vz = state
    r1 = np.sqrt((x + MU) ** 2 + y ** 2 + z ** 2)
    r2 = np.sqrt((x - 1 + MU) ** 2 + y ** 2 + z ** 2)
    ax = (2 * vy + x - (1 - MU) * (x + MU) / r1 ** 3 - MU * (x - 1 + MU) / r2 ** 3)
    ay = (-2 * vx + y - (1 - MU) * y / r1 ** 3 - MU * y / r2 ** 3)
    az = (-(1 - MU) * z / r1 ** 3 - MU * z / r2 ** 3)
    return [vx, vy, vz, ax, ay, az]


def propagate_nrho(initial_state, period_nondim, n_points=200):
    """
    initial_state: [x, y, z, vx, vy, vz] in CR3BP rotating-frame
    non-dimensional units. period_nondim: orbital period in the same
    non-dimensional time units.
    """
    sol = solve_ivp(
        cr3bp_eom, [0, period_nondim], initial_state,
        method="DOP853", rtol=1e-9, atol=1e-12,
        t_eval=np.linspace(0, period_nondim, n_points),
    )
    return sol.t, sol.y


def to_km(state_nondim):
    return state_nondim * EARTH_MOON_DIST
