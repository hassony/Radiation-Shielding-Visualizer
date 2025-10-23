# physics.py — Simplified but physically realistic X-ray interaction models
"""
physics.py
-----------
Core physics relationships used in the X-ray Interaction Visualizer.

These are simplified educational approximations of how X-ray photons interact
with matter through three main processes:

1. Photoelectric effect
2. Compton scattering
3. Rayleigh (coherent) scattering

⚠️ NOTE:
These equations are for educational visualization only — 
they are *not* suitable for medical dose or shielding design.
"""

import numpy as np

# ────────────────────────────────────────────────
# Effective atomic numbers (approximate)
# ────────────────────────────────────────────────
Z_MAP = {
    "air": 7.6,
    "water": 7.4,
    "fat": 5.9,
    "muscle": 7.4,
    "bone": 13.8,
    "aluminum": 13.0,
    "lead": 82.0
}

# ────────────────────────────────────────────────
# Density values (g/cm³) - NEW
# ────────────────────────────────────────────────
DENSITY_MAP = {
    "air": 0.0012,       
    "water": 1.00,       
    "fat": 0.92,
    "muscle": 1.04,
    "bone": 1.85,        
    "aluminum": 2.70,
    "lead": 11.34,       
}

# ────────────────────────────────────────────────
# K-Edge values in KeV(approximate)
# ────────────────────────────────────────────────
K_EDGE_MAP = {
    "air": 0.53,      
    "water": 0.53,    
    "fat": 0.28,    
    "muscle": 0.53,   
    "bone": 4.0,     
    "aluminum": 1.56,
    "lead": 88.0,     
}

# ────────────────────────────────────────────────
# L-Edge values in KeV (approximate)
# ────────────────────────────────────────────────
L_EDGE_MAP = {
    "air": 0.05,      
    "water": 0.05,    
    "fat": 0.03,    
    "muscle": 0.05,   
    "bone": 0.45,  
    "aluminum": 0.07,
    "lead": 15.8,  
}

# ────────────────────────────────────────────────
# Jump Factors (Approximate Ratios Remaining after Loss)
# ────────────────────────────────────────────────
K_JUMP_FACTOR = 0.15 
L_JUMP_FACTOR = 0.05 

# ────────────────────────────────────────────────
# Photon energy grid (in keV)
# ────────────────────────────────────────────────
def energy_grid(emin: float = 20.0, emax: float = 120.0, n: int = 300) -> np.ndarray:
    """
    Generate photon energies in keV (log-spaced for realism).
    """
    if emin <= 0 or emax <= 0 or emax <= emin:
        raise ValueError("Invalid energy range (emin < emax and both > 0 required).")
    return np.logspace(np.log10(emin), np.log10(emax), n)


# ────────────────────────────────────────────────
# Simplified but realistic proportional relationships
# ────────────────────────────────────────────────
def photoelectric_rel(Z: float, E_keV: np.ndarray, E_K_keV: float = 1.0, E_L_keV: float = 0.1, rho: float = 1.0) -> np.ndarray:
    """
    Photoelectric effect ~ Z^3 / E^3.5 * rho (مُعدلة لتشمل الكثافة وحواف K و L).
    """
    pe_base = (Z ** 3) / (E_keV ** 3.5)
    
    # تطبيق حواف الامتصاص
    mask_between_l_k = (E_keV >= E_L_keV) & (E_keV < E_K_keV)
    pe_base[mask_between_l_k] *= K_JUMP_FACTOR

    mask_below_l = E_keV < E_L_keV
    pe_base[mask_below_l] *= L_JUMP_FACTOR
    
    # 🌟 ضرب النتيجة النهائية بالكثافة
    return pe_base * rho


def compton_rel(Z: float, E_keV: np.ndarray, rho: float = 1.0) -> np.ndarray:
    """
    Compton scattering ~ Z * log(E) / E^1.2 * rho (مُعدلة لتشمل الكثافة).
    """
    # 🌟 ضرب النتيجة النهائية بالكثافة
    return Z * np.log(E_keV + 1) / (E_keV ** 1.2) * rho


def rayleigh_rel(Z: float, E_keV: np.ndarray, rho: float = 1.0) -> np.ndarray:
    """
    Rayleigh (coherent) scattering ~ Z^2 / E^2.2 * rho (مُعدلة لتشمل الكثافة).
    """
    # 🌟 ضرب النتيجة النهائية بالكثافة
    return (Z ** 2) / (E_keV ** 2.2) * rho


# ────────────────────────────────────────────────
# Normalization helper
# ────────────────────────────────────────────────
def normalize_interactions(*arrays):
    """
    Normalize any number of interaction arrays so that
    the sum of all processes = 1 at every energy point.
    """
    total = np.zeros_like(arrays[0])
    for a in arrays:
        total += a
    total[total == 0] = 1.0
    return [a / total for a in arrays]