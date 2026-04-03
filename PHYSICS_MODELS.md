# Physics Models Implemented

## X-ray
- Uses didactic attenuation-proxy curves in arbitrary units rather than direct XCOM tables.
- Photoelectric proxy scales strongly with `Z` and falls rapidly with energy, with simple K-edge and L-edge modifiers.
- Compton and Rayleigh are modeled with smooth heuristic trends suitable for qualitative comparison.
- The plot, PDF report, and Excel export now use the same absolute component curves.
- Density scales the component magnitudes, so it affects absolute attenuation level, not only internal normalization.

---

## Gamma-ray
- Uses qualitative mass-attenuation heuristics, not exact Klein-Nishina / Bethe-Heitler cross-sections.
- Photoelectric absorption is strongest near the low-energy end and drops quickly through the MeV range.
- Compton scattering dominates through most of the mid-MeV range for typical materials.
- Pair production turns on at `1.022 MeV` and grows with energy and atomic number.
- The x-axis scale follows the user selection (`linear` or `log`), while the y-axis remains logarithmic.

---

## Proton
- Uses one unified Bethe-inspired stopping-power model across all proton outputs.
- Bragg curve, stopping-power curve, and CSDA range are derived from the same material definition and the same stopping-power law.
- Custom proton materials are resolved into the same material-spec pipeline as built-in materials.
- Lateral spread uses a Highland-style estimate with an approximate radiation length inferred from effective material properties.

---

## Electron (Planned)
- Collisional and radiative loss models are planned, but not implemented in this version.

---

## Shielding (Planned)
- Exponential attenuation, HVL/TVL, and broad-beam build-up models are planned, but not implemented in this version.

---

## Scope
- These models are intended for teaching, visualization, and qualitative trend analysis.
- They are not validated for clinical dose calculation, shielding design approval, or reference-data substitution.
