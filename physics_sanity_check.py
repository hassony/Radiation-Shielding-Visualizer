"""
Lightweight physics sanity checks for the educational models.

This script does not try to validate the app against clinical-reference data.
Instead, it verifies:
1. Internal consistency across related outputs
2. Basic threshold behavior
3. Expected qualitative dominance trends
4. Rough agreement with common educational benchmarks

Run:
    .\\.venv\\Scripts\\python.exe physics_sanity_check.py
"""

from __future__ import annotations

import sys
import numpy as np

from modules.gamma.physics import PAIR_THRESHOLD_MEV, gamma_interactions
from modules.protons.physics import bragg_curve, csda_range, stopping_power_mass
from modules.xray.physics import interaction_components


failures: list[str] = []


def report(name: str, ok: bool, detail: str) -> None:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {detail}")
    if not ok:
        failures.append(name)


def check_xray() -> None:
    water = interaction_components(7.42, np.array([20.0, 60.0, 120.0]), 1.0, 0.1, 1.0)
    water_ok = np.all(water["Compton"] > water["Photoelectric"]) and np.all(water["Compton"] > water["Rayleigh"])
    report(
        "X-ray water dominance",
        bool(water_ok),
        "Compton stays above photoelectric and Rayleigh from 20 to 120 keV.",
    )

    lead = interaction_components(82.0, np.array([20.0, 40.0, 80.0, 120.0]), 88.0, 15.9, 11.34)
    lead_ok = np.all(lead["Photoelectric"] > lead["Compton"]) and np.all(lead["Photoelectric"] > lead["Rayleigh"])
    report(
        "X-ray lead dominance",
        bool(lead_ok),
        "Photoelectric remains the largest component in the tested diagnostic-keV range.",
    )

    edge = interaction_components(82.0, np.array([87.9, 88.1]), 88.0, 15.9, 11.34)["Photoelectric"]
    edge_ok = bool(edge[1] > edge[0])
    report(
        "X-ray K-edge behavior",
        edge_ok,
        f"Photoelectric proxy jumps upward across the lead K-edge ({edge[0]:.3f} -> {edge[1]:.3f}).",
    )

    base = interaction_components(13.0, np.array([30.0, 80.0]), 1.56, 0.09, 1.0)
    dense = interaction_components(13.0, np.array([30.0, 80.0]), 1.56, 0.09, 2.0)
    scaling_ok = all(np.allclose(dense[key], 2.0 * base[key]) for key in base)
    report(
        "X-ray density scaling",
        bool(scaling_ok),
        "Doubling density doubles all linear attenuation proxies for the same material definition.",
    )


def check_gamma() -> None:
    energies = np.array([0.5, 1.0, 2.0, 5.0])
    water = gamma_interactions(7.42, 1.0, energies)
    pair_threshold_ok = bool(np.all(water["pair_mu"][:2] == 0.0) and np.all(water["pair_mu"][2:] > 0.0))
    report(
        "Gamma pair threshold",
        pair_threshold_ok,
        "Pair production is zero below 1.022 MeV and positive above threshold.",
    )

    total_ok = bool(
        np.allclose(
            water["total_mu"],
            water["photo_mu"] + water["compton_mu"] + water["pair_mu"],
        )
    )
    report(
        "Gamma total composition",
        total_ok,
        "Total linear attenuation equals the sum of photoelectric, Compton, and pair terms.",
    )

    water_dom_ok = bool(np.all(water["compton_mu"] > water["photo_mu"]) and np.all(water["compton_mu"] > water["pair_mu"]))
    report(
        "Gamma water dominance",
        water_dom_ok,
        "Compton remains the dominant contribution in water from 0.5 to 5 MeV.",
    )

    lead = gamma_interactions(82.0, 11.34, np.array([0.05, 5.0]))
    lead_dom_ok = bool(lead["photo_mu"][0] > lead["compton_mu"][0] and lead["compton_mu"][1] > lead["photo_mu"][1])
    report(
        "Gamma lead regime shift",
        lead_dom_ok,
        "Lead is photoelectric-dominated at low energy and Compton-dominated by 5 MeV.",
    )

    rho1 = gamma_interactions(29.0, 1.0, np.array([0.3, 2.0]))
    rho2 = gamma_interactions(29.0, 2.0, np.array([0.3, 2.0]))
    density_ok = bool(np.allclose(rho2["total_mu"], 2.0 * rho1["total_mu"]) and np.allclose(rho2["total_mu_rho"], rho1["total_mu_rho"]))
    report(
        "Gamma density scaling",
        density_ok,
        "Linear attenuation scales with density while mass attenuation stays unchanged.",
    )


def check_protons() -> None:
    energies = np.array([70.0, 100.0, 150.0, 200.0, 250.0])
    stopping = np.array([stopping_power_mass(float(E), "water") for E in energies])
    stopping_ok = bool(np.all(np.diff(stopping) < 0))
    report(
        "Proton stopping-power trend",
        stopping_ok,
        "Mass stopping power decreases across 70 to 250 MeV in water.",
    )

    ranges = np.array([csda_range(float(E), "water") for E in energies])
    range_ok = bool(np.all(np.diff(ranges) > 0))
    report(
        "Proton range monotonicity",
        range_ok,
        "CSDA range increases monotonically with initial proton energy.",
    )

    benchmark_cm = {
        70.0: 4.1,
        100.0: 7.7,
        150.0: 15.8,
        200.0: 26.0,
        250.0: 38.0,
    }
    benchmark_ok = True
    benchmark_detail = []
    for energy in energies:
        predicted = float(csda_range(float(energy), "water"))
        reference = benchmark_cm[float(energy)]
        rel_err = abs(predicted - reference) / reference
        benchmark_ok &= rel_err <= 0.20
        benchmark_detail.append(f"{energy:.0f} MeV: {predicted:.2f} cm vs ~{reference:.1f} cm")
    report(
        "Proton benchmark agreement",
        benchmark_ok,
        "; ".join(benchmark_detail) + " (20% educational tolerance).",
    )

    bragg_ok = True
    bragg_detail = []
    for energy in energies:
        csda = float(csda_range(float(energy), "water"))
        depth, dose, terminal = bragg_curve(float(energy), "water", dx_cm=0.01)
        peak_depth = float(depth[int(np.argmax(dose))])
        close_to_csda = abs(terminal - csda) / csda <= 0.05
        peak_before_end = peak_depth < terminal
        bragg_ok &= close_to_csda and peak_before_end
        bragg_detail.append(f"{energy:.0f} MeV: peak {peak_depth:.2f} cm, end {terminal:.2f} cm, range {csda:.2f} cm")
    report(
        "Proton Bragg consistency",
        bragg_ok,
        "; ".join(bragg_detail),
    )


def main() -> int:
    print("Running educational physics sanity checks")
    print(f"Pair threshold used by gamma model: {PAIR_THRESHOLD_MEV:.3f} MeV")
    print("")

    check_xray()
    check_gamma()
    check_protons()

    print("")
    if failures:
        print("Failed checks:")
        for name in failures:
            print(f"- {name}")
        return 1

    print("All sanity checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
