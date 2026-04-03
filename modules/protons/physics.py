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


def _effective_atomic_mass(Z: float) -> float:
    return max(2.0 * Z, 1.0)


def _mean_excitation_energy_eV(Z: float) -> float:
    return max(15.0, 16.0 * (Z ** 0.9))


def _radiation_length_g_cm2(Z: float, A: float) -> float:
    Z = max(Z, 1.0)
    log_term = max(math.log(287.0 / math.sqrt(Z)), 1e-6)
    return max(716.4 * A / (Z * (Z + 1.0) * log_term), 1.0)


def resolve_material_spec(material) -> dict:
    """Normalize built-in and custom material definitions into one spec."""
    if isinstance(material, dict):
        raw = dict(material)
        label = (raw.get("label") or raw.get("name") or "Custom Material").strip() or "Custom Material"
        Z = float(raw.get("Z", 7.42))
        rho = float(raw.get("rho", 1.0))
        name = raw.get("name") or label.lower().replace(" ", "_")
    else:
        name = str(material or "water").strip().lower() or "water"
        data = get_material_data(name) or get_material_data("water") or {"Z": 7.42, "rho": 1.0}
        resolved_name = name if get_material_data(name) else "water"
        label = resolved_name.replace("_", " ").title()
        Z = float(data.get("Z", 7.42))
        rho = float(data.get("rho", 1.0))
        raw = {}
        name = resolved_name

    Z = max(Z, 1e-6)
    rho = max(rho, 1e-6)
    A = float(raw.get("A", _effective_atomic_mass(Z)))
    I_eV = float(raw.get("I_eV", 75.0 if name == "water" else _mean_excitation_energy_eV(Z)))
    X0_gcm2 = float(raw.get("X0_g_cm2", _radiation_length_g_cm2(Z, A)))

    return {
        "name": name,
        "label": label,
        "Z": Z,
        "rho": rho,
        "A": max(A, 1e-6),
        "I_eV": max(I_eV, 1.0),
        "X0_g_cm2": max(X0_gcm2, 1e-6),
    }


def _stopping_power_mass_from_spec(E_MeV: float, spec: dict) -> float:
    if E_MeV <= 0:
        return 0.0

    beta, gamma = beta_gamma(max(E_MeV, 1e-4))
    beta2 = max(beta * beta, 1e-9)
    Wmax = max(w_max(E_MeV), 1e-9)
    I_MeV = spec["I_eV"] * 1e-6
    argument = max((2 * ME_C2 * beta2 * gamma * gamma * Wmax) / (I_MeV ** 2), 1.000001)
    # Heavy-particle Bethe stopping power uses 1/2 * ln(...) - beta^2.
    # Omitting the 1/2 doubles dE/dx and compresses the CSDA range and Bragg depth.
    term = max(0.5 * math.log(argument) - beta2, 0.05)
    dEdx_mass = K_BETHE * (spec["Z"] / spec["A"]) * (term / beta2)
    return max(dEdx_mass, 1e-6)


def stopping_power_mass(E_MeV: float, material) -> float:
    spec = resolve_material_spec(material)
    return _stopping_power_mass_from_spec(float(E_MeV), spec)


def stopping_power_linear(E, material):
    spec = resolve_material_spec(material)
    arr = np.asarray(E, dtype=float)
    scalar_input = arr.ndim == 0
    energies = np.atleast_1d(arr)
    linear = np.array([
        _stopping_power_mass_from_spec(float(max(energy, 1e-6)), spec) * spec["rho"]
        for energy in energies
    ])
    if scalar_input:
        return float(linear[0])
    return linear.reshape(arr.shape)

# ----------------------------
# CSDA range
# ----------------------------

def csda_range(E0_MeV: float, material, dE_max: float = 0.5) -> float:
    """
    Compute CSDA range (continuous slowing down approximation) using the
    same stopping-power model used for Bragg and stopping-power curves.
    """
    if E0_MeV <= 0:
        return 0.0

    spec = resolve_material_spec(material)
    E = float(E0_MeV)
    x_cm = 0.0
    steps = 0
    while E > 0.05 and steps < 200000:
        dEdx = max(stopping_power_linear(E, spec), 1e-6)
        if dEdx <= 0:
            break
        dE = min(dE_max, max(0.01, 0.02 * E))
        dx = dE / dEdx
        x_cm += dx
        E -= dE
        steps += 1

    if E > 0:
        x_cm += E / max(stopping_power_linear(max(E, 1e-3), spec), 1e-6)

    return x_cm


# ----------------------------
# Highland scattering
# ----------------------------

def highland_theta0(depth_cm: float, E0_MeV: float, material) -> float:
    spec = resolve_material_spec(material)
    X0_cm = spec["X0_g_cm2"] / spec["rho"]

    if depth_cm <= 0 or E0_MeV <= 0:
        return 0.0
    pc = momentum_pc(E0_MeV)
    beta, _ = beta_gamma(E0_MeV)
    if pc <= 0 or beta <= 0:
        return 0.0
    t = max(depth_cm / X0_cm, 1e-8)
    theta0 = (13.6) / (beta * pc) * math.sqrt(t) * (1.0 + 0.038*math.log(t))
    return theta0


def lateral_sigma(depth_cm: float, E0_MeV: float, material) -> float:
    theta0 = highland_theta0(depth_cm, E0_MeV, material)
    return theta0 * depth_cm / math.sqrt(3.0)


# ----------------------------
# Bragg curve
# ----------------------------

def bragg_curve(E0_MeV: float, material, dx_cm: float = 0.01, smooth_sigma_frac: float = 0.015) -> Tuple[np.ndarray, np.ndarray, float]:
    if E0_MeV <= 0 or dx_cm <= 0:
        return np.array([0.0]), np.array([0.0]), 0.0

    spec = resolve_material_spec(material)
    E = float(E0_MeV)
    depths: List[float] = [0.0]
    dose: List[float] = [0.0]
    x = 0.0
    steps = 0

    while E > 0.01 and steps < 200000:
        dEdx = max(stopping_power_linear(E, spec), 1e-6)
        if dEdx <= 0:
            break
        dose.append(dEdx)
        x += dx_cm
        depths.append(x)
        E = max(E - dEdx * dx_cm, 0.0)
        steps += 1

    depth_arr = np.asarray(depths)
    dose_arr = np.asarray(dose)
    if dose_arr.max() > 0:
        dose_arr = dose_arr / dose_arr.max()

    if smooth_sigma_frac and depth_arr.size > 3:
        R = depth_arr[-1]
        sigma = max(smooth_sigma_frac * R, 2 * dx_cm)
        halfwin = int(max(3, sigma / dx_cm))
        xk = np.arange(-halfwin, halfwin + 1) * dx_cm
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

def stopping_power_curve(energies_MeV: np.ndarray, material) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute stopping power (dE/dx) for protons in the given material.
    Returns mass stopping power (MeV·cm²/g) from the same unified model used
    by the Bragg and range calculations.
    """
    spec = resolve_material_spec(material)
    Es = np.asarray(energies_MeV, dtype=float)
    S_mass = np.array([_stopping_power_mass_from_spec(float(max(E, 1e-6)), spec) for E in Es])
    S_mass = np.nan_to_num(S_mass, nan=0.0, posinf=0.0, neginf=0.0)
    return Es, S_mass


def range_vs_energy(energies_MeV: np.ndarray, material, dE_max: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
    Es = np.asarray(energies_MeV, dtype=float)
    R = np.array([csda_range(float(E0), material, dE_max=dE_max) for E0 in Es])
    return Es, R


def lateral_sigma_curve(depths_cm: np.ndarray, E0_MeV: float, material) -> Tuple[np.ndarray, np.ndarray]:
    zs = np.asarray(depths_cm, dtype=float)
    sig = np.array([lateral_sigma(float(z), E0_MeV, material) for z in zs])
    return zs, sig


if __name__ == "__main__":
    print("Self-test:")
    E0 = 150.0
    mat = "water"
    print("CSDA range in water (cm):", csda_range(E0, mat))
    z, d, R = bragg_curve(E0, mat)
    print("Bragg peak at depth (cm):", z[np.argmax(d)], "R≈", R)
