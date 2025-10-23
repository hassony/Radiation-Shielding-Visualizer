"""
Medical Radiation Visualizer — Proton Plotting Module
=====================================================
This module provides pure plotting functions for the Proton Interaction Visualizer.

Responsibilities:
  • Generate plots for Bragg curve, stopping power, CSDA range, and lateral spread.
  • No Flask routes or file I/O — handled externally in app.py.
  • Returns matplotlib Figure and Axes objects.
"""

import io
import numpy as np
import matplotlib.pyplot as plt

from modules.protons.physics import (
    bragg_curve,
    stopping_power_curve,
    range_vs_energy,
    lateral_sigma_curve,
)

plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({
    "figure.figsize": (8, 5),
    "axes.labelsize": 13,
    "axes.titlesize": 15,
    "legend.fontsize": 11,
    "lines.linewidth": 2.0,
    "font.family": "DejaVu Sans",
})

# ---------------------------------------------------------------------
# Core plotting logic
# ---------------------------------------------------------------------

def plot_bragg(E0: float, material: str, dx: float = 0.01):
    depth, dose_rel, _ = bragg_curve(E0, material, dx_cm=dx)
    fig, ax = plt.subplots()
    ax.plot(depth, dose_rel, color="#0077b6", lw=2)
    ax.set_xlabel("Depth (cm)")
    ax.set_ylabel("Relative Dose (a.u.)")
    ax.set_title(f"Bragg Curve — {material.title()} ({E0} MeV)")
    ax.grid(True, linestyle="--", alpha=0.5)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    return fig, ax


def plot_stopping(emin: float, emax: float, npts: int, material: str):
    energies = np.linspace(emin, emax, npts)
    Es, S = stopping_power_curve(energies, material)
    fig, ax = plt.subplots()
    ax.plot(Es, S, color="#d62828", lw=2)
    ax.set_xlabel("Energy (MeV)")
    ax.set_ylabel("Mass Stopping Power (MeV·cm²/g)")
    ax.set_title(f"Stopping Power — {material.title()}")
    ax.grid(True, linestyle="--", alpha=0.5)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    return fig, ax


def plot_range(emin: float, emax: float, npts: int, material: str):
    energies = np.linspace(emin, emax, npts)
    Es, R = range_vs_energy(energies, material)
    fig, ax = plt.subplots()
    ax.plot(Es, R, color="#2a9d8f", lw=2)
    ax.set_xlabel("Initial Energy (MeV)")
    ax.set_ylabel("CSDA Range (cm)")
    ax.set_title(f"Range vs Energy — {material.title()}")
    ax.grid(True, linestyle="--", alpha=0.5)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    return fig, ax


def plot_lateral(E0: float, zmax: float, npts: int, material: str):
    depths = np.linspace(0.0, zmax, npts)
    zs, sig = lateral_sigma_curve(depths, E0, material)
    fig, ax = plt.subplots()
    ax.plot(zs, sig, color="#264653", lw=2)
    ax.set_xlabel("Depth (cm)")
    ax.set_ylabel("Lateral Spread σ (cm)")
    ax.set_title(f"Lateral Spread — {material.title()} ({E0} MeV)")
    ax.grid(True, linestyle="--", alpha=0.5)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    return fig, ax


# ---------------------------------------------------------------------
# Unified interface
# ---------------------------------------------------------------------

def plot_proton_interaction(mode: str, params: dict):
    mode = mode.lower()
    if mode == "bragg":
        return plot_bragg(params.get("E0", 150.0), params.get("material", "water"), params.get("dx", 0.01))
    elif mode == "stopping":
        return plot_stopping(params.get("emin", 10.0), params.get("emax", 250.0), params.get("npts", 120), params.get("material", "water"))
    elif mode == "range":
        return plot_range(params.get("emin", 10.0), params.get("emax", 250.0), params.get("npts", 120), params.get("material", "water"))
    elif mode == "lateral":
        return plot_lateral(params.get("E0", 150.0), params.get("zmax", 25.0), params.get("npts", 120), params.get("material", "water"))
    else:
        raise ValueError(f"Unknown plot mode: {mode}")
