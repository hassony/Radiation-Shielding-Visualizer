# ============================================================
# modules/gamma/visualizer.py
# Gamma-ray Interaction Visualizer — Stable & Accurate
# ============================================================

import matplotlib.pyplot as plt
import numpy as np
from .physics import gamma_interactions, PAIR_THRESHOLD_MEV

def plot_gamma(
    Z1: float,
    E_mev: np.ndarray,
    title: str = "Gamma-ray Interactions",
    rho1: float = 1.0,
    # Optional second material:
    Z2: float | None = None,
    rho2: float | None = None,
    # Optional labels (for legend titles):
    material1: str | None = None,
    material2: str | None = None,
    show_mass_coeff: bool = False,  # False → μ(1/cm), True → μ/ρ(cm²/g)
    scale: str = "log",
):
    """
    Generates a safe and realistic gamma-ray interaction plot.
    Includes Photoelectric, Compton, Pair, and Total attenuation curves for one or two materials.
    """

    material1 = material1 or "Material 1"
    mat2_enabled = (Z2 is not None and rho2 is not None)
    if mat2_enabled:
        material2 = material2 or "Material 2"

    # ============================================================
    # 🧮 Compute interaction data
    # ============================================================
    data1 = gamma_interactions(Z1, rho1, E_mev)
    if mat2_enabled:
        data2 = gamma_interactions(Z2, rho2, E_mev)

    # Select μ or μ/ρ curves
    if not show_mass_coeff:
        y1_photo = data1["photo_mu"]; y1_compton = data1["compton_mu"]; y1_pair = data1["pair_mu"]; y1_total = data1["total_mu"]
        y_label = r"Linear attenuation $\mu$ (1/cm)"
        if mat2_enabled:
            y2_photo = data2["photo_mu"]; y2_compton = data2["compton_mu"]; y2_pair = data2["pair_mu"]; y2_total = data2["total_mu"]
    else:
        y1_photo = data1["photo_mu_rho"]; y1_compton = data1["compton_mu_rho"]; y1_pair = data1["pair_mu_rho"]; y1_total = data1["total_mu_rho"]
        y_label = r"Mass attenuation $\mu/\rho$ (cm$^2$/g)"
        if mat2_enabled:
            y2_photo = data2["photo_mu_rho"]; y2_compton = data2["compton_mu_rho"]; y2_pair = data2["pair_mu_rho"]; y2_total = data2["total_mu_rho"]

    # ============================================================
    # 🧹 Clean invalid values to prevent log-scale crashes
    # ============================================================
    def sanitize(arr):
        arr = np.nan_to_num(arr, nan=0, posinf=0, neginf=0)
        arr[arr < 1e-10] = 1e-10
        return arr

    y1_photo, y1_compton, y1_pair, y1_total = map(sanitize, [y1_photo, y1_compton, y1_pair, y1_total])
    if mat2_enabled:
        y2_photo, y2_compton, y2_pair, y2_total = map(sanitize, [y2_photo, y2_compton, y2_pair, y2_total])

    # ============================================================
    # 📈 Plot setup
    # ============================================================
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    E = data1["E_mev"]

    # Material 1 curves
    ax.plot(E, y1_photo,   label=f"{material1} — Photoelectric", linewidth=2.0)
    ax.plot(E, y1_compton, label=f"{material1} — Compton", linewidth=2.0)
    ax.plot(E, y1_pair,    label=f"{material1} — Pair", linewidth=2.0)
    ax.plot(E, y1_total,   label=f"{material1} — Total", linewidth=2.3, alpha=0.9)

    # Material 2 (if any)
    if mat2_enabled:
        ax.plot(E, y2_photo,   "--", label=f"{material2} — Photoelectric", linewidth=1.6)
        ax.plot(E, y2_compton, "--", label=f"{material2} — Compton", linewidth=1.6)
        ax.plot(E, y2_pair,    "--", label=f"{material2} — Pair", linewidth=1.6)
        ax.plot(E, y2_total,   "--", label=f"{material2} — Total", linewidth=2.0, alpha=0.9)

    # ============================================================
    # ⚡ Pair-production threshold line
    # ============================================================
    threshold = 1.022  # MeV

    if E.min() < threshold < E.max():
        # رسم الخط العمودي
        ax.axvline(x=threshold, color="red", linestyle="--", linewidth=1.4, alpha=0.7)

        # الحصول على حدود المحور الصادي
        ymin, ymax = ax.get_ylim()

        # حساب المنتصف الهندسي للمحور اللوغاريتمي
        # هذا هو التغيير الرئيسي
        mid_position_y = np.sqrt(ymin * ymax)

        # إضافة النص في المنتصف البصري الصحيح
        ax.text(
            threshold + 0.05,        # موقع X: بجوار الخط مع مسافة بسيطة
            mid_position_y,          # موقع Y: المنتصف الهندسي للمحور الصادي
            "PP Threshold (1.022 MeV)",
            rotation=90,             # تدوير النص 90 درجة
            fontsize=9,
            color="red",
            ha="left",               # المحاذاة الأفقية
            va="center"              # المحاذاة العمودية: في المنتصف
        )
    # ============================================================
    # 🧠 Axes styling
    # ============================================================
    if scale == "log":
        ax.set_xscale("log")
    else:
        ax.set_xscale("linear")

    ax.set_yscale("log")

    ax.set_xlabel("Photon Energy (MeV)", fontsize=11)
    ax.set_ylabel(y_label, fontsize=11)
    ax.set_title(title, fontsize=13, pad=8)
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    
    # Adjust legend columns based on whether a second material is present
    ax.legend(fontsize=9, ncols=2 if not mat2_enabled else 3, frameon=False)

    fig.subplots_adjust(left=0.12, right=0.96, bottom=0.16, top=0.9)

    return fig, ax