"""
visualizer.py
-------------
Visualization utilities for the X-ray Interaction Visualizer project.

Handles plotting for:
 - Photoelectric
 - Compton
 - Rayleigh
"""

import matplotlib.pyplot as plt
import numpy as np
from .physics import interaction_components

# ────────────────────────────────────────────────
# Visual style
# ────────────────────────────────────────────────
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({
    "figure.figsize": (9, 5),
    "axes.labelsize": 13,
    "axes.titlesize": 15,
    "legend.fontsize": 11,
    "lines.linewidth": 2.2,
    "font.family": "DejaVu Sans",
})

COLORS = {
    "photoelectric": "#0077b6",
    "compton": "#d62828",
    "rayleigh": "#ffb703",
}


# ────────────────────────────────────────────────
# Main plot function
# ────────────────────────────────────────────────
def plot_interactions(
    Z: float,
    E_keV: np.ndarray,
    title: str = "",
    E_K: float = 1.0, 
    E_L: float = 0.1,  # 🌟 إضافة L-edge
    rho: float = 1.0,  # 🌟 إضافة الكثافة
    show_photo=True,
    show_compton=True,
    show_rayleigh=True
):
    """Plot attenuation-like interaction proxies for a single material."""

    components = interaction_components(Z, E_keV, E_K, E_L, rho)
    pe = np.clip(components["Photoelectric"], 1e-12, None)
    co = np.clip(components["Compton"], 1e-12, None)
    ra = np.clip(components["Rayleigh"], 1e-12, None)

    # Plot
    fig, ax = plt.subplots(figsize=(8, 5))

    if show_photo:
        ax.plot(E_keV, pe, color=COLORS["photoelectric"], lw=2, label="Photoelectric")
        
        # 🌟 إضافة خط K-edge العمودي 
        if E_K < E_keV.max() and E_K > E_keV.min():
            ax.axvline(x=E_K, color=COLORS["photoelectric"], linestyle=":", alpha=0.7)
            ax.text(E_K + 0.05, 0.95, f"K-edge ({E_K:.1f} keV)", color=COLORS["photoelectric"], fontsize=9, rotation=90, va="top")
        
        # 🌟 إضافة خط L-edge العمودي
        if E_L < E_keV.max() and E_L > E_keV.min():
            ax.axvline(x=E_L, color=COLORS["photoelectric"], linestyle="-.", alpha=0.4)
            
    if show_compton:
        ax.plot(E_keV, co, color=COLORS["compton"], lw=2, label="Compton")
    if show_rayleigh:
        ax.plot(E_keV, ra, color=COLORS["rayleigh"], lw=2, label="Rayleigh")

    ax.set_xlim(E_keV.min(), E_keV.max())
    ax.set_yscale("log")
    ax.set_xlabel("Photon Energy (keV)", fontsize=12)
    ax.set_ylabel("Relative Attenuation Proxy (a.u.)", fontsize=12)
    ax.set_title(title or "X-ray Interaction Components", fontsize=13)
    ax.grid(True, which="both", linestyle="--", alpha=0.4)
    ax.legend()

    # Simplify frame
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    fig.tight_layout()
    return fig, ax


# ────────────────────────────────────────────────
# Comparison helper
# ────────────────────────────────────────────────
def compare_materials(
    Z1: float,
    Z2: float,
    E_keV: np.ndarray,
    name1="Material A",
    name2="Material B",
    E_K1: float = 1.0, 
    E_L1: float = 0.1,  # 🌟 إضافة L-edge 1
    rho1: float = 1.0,  # 🌟 إضافة الكثافة 1
    E_K2: float = 1.0, 
    E_L2: float = 0.1,  # 🌟 إضافة L-edge 2
    rho2: float = 1.0,  # 🌟 إضافة الكثافة 2
    show_rayleigh: bool = True
):
    """Compare attenuation-like interaction proxies for two materials."""
    fig, ax = plt.subplots(figsize=(9, 5))

    comp1 = interaction_components(Z1, E_keV, E_K1, E_L1, rho1)
    comp2 = interaction_components(Z2, E_keV, E_K2, E_L2, rho2)
    pe1 = np.clip(comp1["Photoelectric"], 1e-12, None)
    co1 = np.clip(comp1["Compton"], 1e-12, None)
    ra1 = np.clip(comp1["Rayleigh"], 1e-12, None)
    pe2 = np.clip(comp2["Photoelectric"], 1e-12, None)
    co2 = np.clip(comp2["Compton"], 1e-12, None)
    ra2 = np.clip(comp2["Rayleigh"], 1e-12, None)

    # Photoelectric
    ax.plot(E_keV, pe1, color=COLORS["photoelectric"], linestyle="-",  label=f"{name1} - Photoelectric")
    ax.plot(E_keV, pe2, color=COLORS["photoelectric"], linestyle="--", label=f"{name2} - Photoelectric")

    # Compton
    ax.plot(E_keV, co1, color=COLORS["compton"], linestyle="-",  label=f"{name1} - Compton")
    ax.plot(E_keV, co2, color=COLORS["compton"], linestyle="--", label=f"{name2} - Compton")

    # Rayleigh 
    if show_rayleigh:
        ax.plot(E_keV, ra1, color=COLORS["rayleigh"], linestyle="-",  label=f"{name1} - Rayleigh")
        ax.plot(E_keV, ra2, color=COLORS["rayleigh"], linestyle="--", label=f"{name2} - Rayleigh")

    # 🌟 إضافة خطوط K-edge المقارنة
    if E_K1 < E_keV.max() and E_K1 > E_keV.min():
        ax.axvline(x=E_K1, color=COLORS["photoelectric"], linestyle="-.", alpha=0.5)
    if E_K2 and E_K2 < E_keV.max() and E_K2 > E_keV.min():
        ax.axvline(x=E_K2, color=COLORS["photoelectric"], linestyle=":", alpha=0.5)
        
    # 🌟 إضافة خطوط L-edge المقارنة
    if E_L1 < E_keV.max() and E_L1 > E_keV.min():
        ax.axvline(x=E_L1, color=COLORS["photoelectric"], linestyle="-.", alpha=0.3)
    if E_L2 and E_L2 < E_keV.max() and E_L2 > E_keV.min():
        ax.axvline(x=E_L2, color=COLORS["photoelectric"], linestyle=":", alpha=0.3)


    ax.set_xlabel("Photon Energy (keV)")
    ax.set_ylabel("Relative Attenuation Proxy (a.u.)")
    ax.set_title(f"Interaction Comparison: {name1} vs {name2}")
    ax.set_yscale("log")
    ax.legend(frameon=True, facecolor="white", edgecolor="#ddd")
    ax.grid(True, which="both", linestyle="--", alpha=0.4)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    fig.tight_layout()
    return fig, ax
