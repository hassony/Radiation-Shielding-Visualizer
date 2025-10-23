# modules/gamma/physics.py
# ------------------------------------------------------------
# Educational gamma-ray interaction models (Photoelectric + Compton + Pair)
# Units:
#   - Energy: MeV
#   - Linear attenuation μ: 1/cm
#   - Mass attenuation (μ/ρ): cm^2/g
#
# NOTE: Coefficients below are heuristic for didactic trends,
# NOT for clinical or metrology use.
# ------------------------------------------------------------

import numpy as np

PAIR_THRESHOLD_MEV = 1.022  # e- + e+ creation threshold

def energy_grid(emin_mev: float, emax_mev: float, points: int = 300, scale: str = "linear") -> np.ndarray:
    emin_mev = max(float(emin_mev), 1e-3)
    emax_mev = max(float(emax_mev), emin_mev * 1.0001)
    if scale.lower().startswith("log"):
        return np.logspace(np.log10(emin_mev), np.log10(emax_mev), points)
    return np.linspace(emin_mev, emax_mev, points)


# --- Didactic mass attenuation models (μ/ρ in cm^2/g) ---

def _photoelectric_mu_over_rho(Z: float, E_mev: np.ndarray) -> np.ndarray:
    """
    Didactic Photoelectric model.
    Strongly dependent on Z (~Z^4) and E (~1/E^3).
    """
    E = np.asarray(E_mev, dtype=float)
    # Heuristic scaling constant to produce reasonable values
    k = 4e-3
    mu_rho = k * (Z**4) / (E**3)
    return np.clip(mu_rho, 1e-6, None)


def _compton_mu_over_rho(Z: float, E_mev: np.ndarray) -> np.ndarray:
    """
    Didactic Compton mass attenuation coefficient ~ decreasing with energy.
    ~ proportional to (electron density) and ~ 1/E at MeV range.
    """
    E = np.asarray(E_mev, dtype=float)
    # base ~ 0.02 cm^2/g around ~0.2–0.5 MeV for mid-Z; gently falling
    base = 0.020 * (Z / 20.0)**0.85
    mu_rho = base / (1.0 + (E / 0.5))**0.9
    return np.clip(mu_rho, 1e-6, None)


def _pair_mu_over_rho(Z: float, E_mev: np.ndarray) -> np.ndarray:
    """
    Didactic Pair Production mass attenuation coefficient:
    0 below 1.022 MeV, then ~ Z^2 * log(E/threshold) / E
    """
    E = np.asarray(E_mev, dtype=float)
    mu_rho = np.zeros_like(E)
    mask = E >= PAIR_THRESHOLD_MEV
    if np.any(mask):
        # scale chosen to give ~1e-3 to ~1e-2 cm^2/g in several MeV range for high-Z
        scale = 0.004 * (Z / 50.0)**1.8
        mu_rho[mask] = scale * np.log(E[mask] / PAIR_THRESHOLD_MEV + 1e-9) / (E[mask]**0.7)
    return np.clip(mu_rho, 0.0, None)


def gamma_interactions(Z: float, rho_g_cm3: float, E_mev: np.ndarray):
    """
    Returns dict with all three major interactions.
    """
    E = np.asarray(E_mev, dtype=float)

    # Mass attenuation (μ/ρ): cm^2/g
    photo_mu_rho   = _photoelectric_mu_over_rho(Z, E)
    compton_mu_rho = _compton_mu_over_rho(Z, E)
    pair_mu_rho    = _pair_mu_over_rho(Z, E)
    total_mu_rho   = photo_mu_rho + compton_mu_rho + pair_mu_rho

    # Linear attenuation μ = (μ/ρ) * ρ  -> 1/cm
    rho = max(float(rho_g_cm3), 1e-6)
    photo_mu   = photo_mu_rho * rho
    compton_mu = compton_mu_rho * rho
    pair_mu    = pair_mu_rho * rho
    total_mu   = total_mu_rho * rho

    return {
        "E_mev": E,
        "photo_mu":   photo_mu,
        "compton_mu": compton_mu,
        "pair_mu":    pair_mu,
        "total_mu":   total_mu,
        "photo_mu_rho":   photo_mu_rho,
        "compton_mu_rho": compton_mu_rho,
        "pair_mu_rho":    pair_mu_rho,
        "total_mu_rho":   total_mu_rho,
        "units": {"mu": "1/cm", "mu_rho": "cm^2/g", "E": "MeV"},
        "threshold_mev": PAIR_THRESHOLD_MEV,
    }