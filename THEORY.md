# Theoretical Background

This document summarizes the physical ideas behind each module and keeps the
description aligned with the implemented models.

---

## X-ray Interactions
Diagnostic-energy X-ray attenuation is governed mainly by photoelectric
absorption, Compton scattering, and Rayleigh scattering.

\[
I = I_0 e^{-\mu x}
\]

with

\[
\mu = \mu_{\mathrm{photoelectric}} + \mu_{\mathrm{Compton}} + \mu_{\mathrm{Rayleigh}}
\]

In this app, the X-ray curves are qualitative attenuation proxies in arbitrary
units. They are tuned to preserve the expected regime ordering and edge-related
behavior without reproducing full tabulated XCOM data.

---

## Gamma-ray Interactions
The gamma module uses qualitative attenuation heuristics rather than exact
cross-section calculations:

1. Compton scattering falls gradually with energy and typically dominates much
   of the mid-MeV range.
2. Pair production is constrained to remain zero below `1.022 MeV`, then grows
   with energy and atomic number above threshold.
3. Photoelectric absorption is strongest at the low-energy end and rapidly
   decreases through the MeV range.

The module reports both mass attenuation (`mu/rho`) and linear attenuation
(`mu = (mu/rho) rho`) consistently from the same internal curves.

---

## Proton Interactions
Proton energy loss is modeled with a Bethe-inspired stopping-power relation.
The same stopping-power law is then reused to generate:

- mass stopping-power curves
- CSDA range estimates
- Bragg curves
- lateral-spread estimates with a Highland-style scattering model

This keeps the proton outputs internally consistent even though the model is
still educational rather than reference-grade.

---

## Electron Interactions (Planned)
- Collisional losses
- Radiative losses
- Combined stopping power
- CSDA range
- Multiple scattering

---

## Shielding (Planned)
Shielding calculations are intended to follow the exponential attenuation law

\[
I = I_0 e^{-\mu x}
\]

with standard derived quantities such as HVL and TVL once the module is
implemented.
