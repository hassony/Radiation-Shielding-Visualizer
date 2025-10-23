# ===============================================================
# 📘 core/constants.py
# Medical Radiation Visualizer — Physical Constants & Material Data
# Author: HASSAN ALMOOSA
# Description:
#   Contains atomic, density, and absorption-edge data
#   for common elements and tissues used in medical physics.
#   (Values from NIST X-ray Data Booklet, v1.5, 2009)
# ===============================================================

# ⚛️ Comprehensive material dataset
MATERIALS = {
    # --- Biological / Reference ---
    "air":       {"Z": 7.3,  "rho": 0.001225, "E_K": None,  "E_L": None},
    "water":     {"Z": 7.42, "rho": 1.000,    "E_K": None,  "E_L": None},
    "bone":      {"Z": 13.8, "rho": 1.85,     "E_K": None,  "E_L": None},
    "soft_tissue": {"Z": 7.4, "rho": 1.06,    "E_K": None,  "E_L": None},

    # --- Common Metals / Filters ---
    "aluminum":  {"Z": 13, "rho": 2.70,  "E_K": 1.56,  "E_L": 0.09},
    "titanium":  {"Z": 22, "rho": 4.51,  "E_K": 4.97,  "E_L": 0.46},
    "iron":      {"Z": 26, "rho": 7.87,  "E_K": 7.11,  "E_L": 0.72},
    "copper":    {"Z": 29, "rho": 8.96,  "E_K": 8.98,  "E_L": 0.93},
    "silver":    {"Z": 47, "rho": 10.49, "E_K": 25.51, "E_L": 3.56},
    "tungsten":  {"Z": 74, "rho": 19.25, "E_K": 69.53, "E_L": 12.1},
    "lead":      {"Z": 82, "rho": 11.34, "E_K": 88.00, "E_L": 15.9},

    # --- Contrast agents / Radiology materials ---
    "iodine":    {"Z": 53, "rho": 4.93,  "E_K": 33.17, "E_L": 4.56},
    "barium":    {"Z": 56, "rho": 3.62,  "E_K": 37.44, "E_L": 5.25},

    # --- Shielding / Structural ---
    "concrete":  {"Z": 11, "rho": 2.3,   "E_K": None,  "E_L": None},
    "iron_steel": {"Z": 26, "rho": 7.9,  "E_K": 7.11,  "E_L": 0.72},
    "tungsten_alloy": {"Z": 74, "rho": 17.5, "E_K": 69.53, "E_L": 12.1}
}

# ---------------------------------------------------------------
# 🎨 Optional — Color map for plotting consistency
COLOR_MAP = {
    "air": "#B0E0E6",
    "water": "#00BFFF",
    "bone": "#DAA520",
    "soft_tissue": "#F4A460",
    "aluminum": "#C0C0C0",
    "iron": "#B22222",
    "copper": "#B87333",
    "silver": "#C0C0C0",
    "tungsten": "#333333",
    "lead": "#555555",
    "iodine": "#9932CC",
    "barium": "#800080",
}

# ---------------------------------------------------------------
# ⚙️ Helper functions (optional for easier access)

def get_material_data(name: str):
    """Return dict with all properties of a material, or None if not found."""
    return MATERIALS.get(name.lower())

def get_property(name: str, prop: str, default=None):
    """Return specific property (e.g. Z, rho, E_K) for a material."""
    mat = MATERIALS.get(name.lower())
    return mat.get(prop) if mat else default

# Example usage:
#   from core.constants import get_property
#   Z = get_property("lead", "Z")
#   rho = get_property("lead", "rho")
