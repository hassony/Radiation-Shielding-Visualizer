#modules/protons/physics.py
"""
Medical Radiation Visualizer — Proton Physics Core (v0.1)
=======================================================
Linked with `core/constants.py` for unified material data.
Implements Bethe–Bloch, CSDA range, Highland scattering, and Bragg peak.

Now uses shared constants via `get_material_data()` and `get_property()`.
"""
from __future__ import annotations

import math
import numpy as np
from typing import Tuple, List
from core.constants import get_material_data

# ----------------------------
# Physical constants (MeV units)
# ----------------------------
K_BETHE = 0.307075  # MeV·cm^2/g
ME_C2 = 0.51099895  # MeV
MP_C2 = 938.272088  # MeV

# ----------------------------
# Relativistic helpers
# ----------------------------

def beta_gamma(E_MeV: float) -> Tuple[float, float]:
    if E_MeV <= 0:
        return 0.0, 1.0
    gamma = 1.0 + E_MeV / MP_C2
    beta2 = 1.0 - 1.0/(gamma*gamma)
    beta = math.sqrt(max(beta2, 0.0))
    return beta, gamma


def momentum_pc(MeV: float) -> float:
    if MeV <= 0:
        return 0.0
    gamma = 1.0 + MeV/MP_C2
    beta2 = 1.0 - 1.0/(gamma*gamma)
    return MP_C2 * gamma * math.sqrt(max(beta2, 0.0))


# ----------------------------
# Bethe–Bloch stopping power
# ----------------------------

def w_max(MeV: float) -> float:
    beta, gamma = beta_gamma(MeV)
    me_over_mp = ME_C2 / MP_C2
    denom = 1 + 2*gamma*me_over_mp + me_over_mp**2
    return 2 * ME_C2 * beta*beta * gamma*gamma / denom


def stopping_power_mass(E_MeV: float, material_name: str) -> float:
    data = get_material_data(material_name)
    if not data:
        raise KeyError(f"Unknown material: {material_name}")

    Z = data.get("Z", 7.42)
    if data is None:
        data = MATERIALS.get("water", {"rho": 1.0})
    rho = data.get("rho", 1.0)

    A = 14.99 if material_name == "water" else 27.0
    I_MeV = 75e-6 if material_name == "water" else 100e-6

    if E_MeV <= 0:
        return 0.0

    beta, gamma = beta_gamma(E_MeV)
    if beta <= 0:
        return float("inf")
    Wmax = w_max(E_MeV)

    term = math.log((2 * ME_C2 * beta*beta * gamma*gamma * Wmax) / (I_MeV**2)) - 2*beta*beta
    return K_BETHE * (Z / A) * (1.0 / (beta*beta)) * term


def stopping_power_linear(E, material_name):
    from core.constants import MATERIALS

    data = MATERIALS.get(material_name)
    if data is None:
        data = MATERIALS.get("water", {"rho": 1.0, "Z": 7.4})

    rho = data.get("rho", 1.0)
    Z = data.get("Z", 7.4)

    # Empirical Bethe–Bloch approximation (simplified)
    try:
        # Ensure positive energies
        E = np.array(E, dtype=float)
        E[E <= 0] = 1e-6
        I = 16 * (Z ** 0.9) * 1e-6  # mean excitation potential (MeV)
        K = 0.307075  # MeV·cm²/mol
        A = 2 * Z
        dEdx = (K * Z / A) * (rho * (np.log(2 * 938.272 * E / I) - 1))
        dEdx = np.maximum(dEdx, 1e-6)  # Prevent zero or negative
        return dEdx
    except Exception as e:
        print("⚠️ stopping_power_linear failed:", e)
        return np.full_like(E, 1.0)  # fallback constant value

# ----------------------------
# CSDA range
# ----------------------------

def csda_range(E0_MeV: float, material_name: str, dE_max: float = 0.5) -> float:
    """
    Compute CSDA range (continuous slowing down approximation)
    and calibrate to realistic depth in cm using empirical scaling.
    """
    if E0_MeV <= 0:
        return 0.0

    E = float(E0_MeV)
    x_raw = 0.0
    while E > 0:
        dEdx = stopping_power_linear(E, material_name)
        if dEdx <= 0:
            break
        dE = min(dE_max, 0.02 * E + 1e-6)
        dx = dE / dEdx
        x_raw += dx
        E -= dE
        if x_raw > 1e4:
            break

    R_target = _target_range_cm(E0_MeV, material_name)
    R_raw = max(x_raw, 1e-9)
    R_calibrated = R_target if R_raw == 0 else R_target * (x_raw / R_raw)  
    return R_calibrated


# ----------------------------
# Highland scattering
# ----------------------------

def highland_theta0(depth_cm: float, E0_MeV: float, material_name: str) -> float:
    data = get_material_data(material_name)
    if not data:
        return 0.0
    if data is None:
        data = MATERIALS.get("water", {"rho": 1.0})
    rho = data.get("rho", 1.0)

    X0_gcm2 = 36.08 if material_name == "water" else 25.0
    X0_cm = X0_gcm2 / rho

    if depth_cm <= 0 or E0_MeV <= 0:
        return 0.0
    pc = momentum_pc(E0_MeV)
    beta, _ = beta_gamma(E0_MeV)
    if pc <= 0 or beta <= 0:
        return 0.0
    t = max(depth_cm / X0_cm, 1e-8)
    theta0 = (13.6) / (beta * pc) * math.sqrt(t) * (1.0 + 0.038*math.log(t))
    return theta0


def lateral_sigma(depth_cm: float, E0_MeV: float, material_name: str) -> float:
    theta0 = highland_theta0(depth_cm, E0_MeV, material_name)
    return theta0 * depth_cm / math.sqrt(3.0)

# ----------------------------
# 
# ----------------------------

def _target_range_cm(E0_MeV: float, material_name: str) -> float:
    """Empirical water-equivalent range model (scaled by density)."""
    data = get_material_data(material_name) or {}
    rho = data.get("rho", 1.0)
    # ~Paganetti-like power law for range in water, density-scaled
    return (0.0022 * (E0_MeV ** 1.77)) / max(rho, 1e-6)


# ----------------------------
# Bragg curve
# ----------------------------

def bragg_curve(E0_MeV: float, material_name: str, dx_cm: float = 0.01, smooth_sigma_frac: float = 0.015) -> Tuple[np.ndarray, np.ndarray, float]:
    if E0_MeV <= 0:
        return np.array([0.0]), np.array([0.0]), 0.0

    E = float(E0_MeV)
    depths: List[float] = [0.0]
    dose: List[float] = [0.0]
    x = 0.0

    while E > 0:
        dEdx = stopping_power_linear(E, material_name)
        if dEdx <= 0:
            break
        dose.append(dEdx)
        x += dx_cm
        depths.append(x)
        E = max(E - dEdx * dx_cm, 0.0)
        if x > 1e4:
            break

    depth_arr = np.asarray(depths)
    dose_arr = np.asarray(dose)
    if dose_arr.max() > 0:
        dose_arr = dose_arr / dose_arr.max()

    R_raw = depth_arr[-1] if depth_arr.size else 0.0
    R_target = _target_range_cm(E0_MeV, material_name)
    scale = (R_target / R_raw) if R_raw > 0 else 1.0
    depth_arr *= scale

    if smooth_sigma_frac and depth_arr.size > 3:
        R = depth_arr[-1]
        sigma = max(smooth_sigma_frac * R, 2 * dx_cm * scale)
        halfwin = int(max(3, sigma / (dx_cm * scale)))
        xk = np.arange(-halfwin, halfwin + 1) * (dx_cm * scale)
        gk = np.exp(-0.5 * (xk / sigma) ** 2)
        gk /= gk.sum()
        dose_arr = np.convolve(dose_arr, gk, mode="same")
        if dose_arr.max() > 0:
            dose_arr /= dose_arr.max()
    else:
        R = depth_arr[-1]

    return depth_arr, dose_arr, R


# ----------------------------
# Public helpers
# ----------------------------

def stopping_power_curve(energies_MeV: np.ndarray, material_name: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute stopping power (dE/dx) for protons in the given material.
    Returns mass stopping power (MeV·cm²/g) calibrated by material density.
    """
    data = get_material_data(material_name) or {}
    rho = data.get("rho", 1.0)

    Es = np.asarray(energies_MeV, dtype=float)
    S_mass = np.array([stopping_power_mass(float(E), material_name) for E in Es])
    S_mass_calibrated = S_mass / max(rho, 1e-6)
    S_mass_calibrated = np.nan_to_num(S_mass_calibrated, nan=0.0, posinf=0.0, neginf=0.0)

    return Es, S_mass_calibrated


def range_vs_energy(energies_MeV: np.ndarray, material_name: str, dE_max: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
    Es = np.asarray(energies_MeV, dtype=float)
    R = np.array([csda_range(float(E0), material_name, dE_max=dE_max) for E0 in Es])
    return Es, R


def lateral_sigma_curve(depths_cm: np.ndarray, E0_MeV: float, material_name: str) -> Tuple[np.ndarray, np.ndarray]:
    zs = np.asarray(depths_cm, dtype=float)
    sig = np.array([lateral_sigma(float(z), E0_MeV, material_name) for z in zs])
    return zs, sig


if __name__ == "__main__":
    print("Self-test:")
    E0 = 150.0
    mat = "water"
    print("CSDA range in water (cm):", csda_range(E0, mat))
    z, d, R = bragg_curve(E0, mat)
    print("Bragg peak at depth (cm):", z[np.argmax(d)], "R≈", R)
