# Computational Methodology

---

## Architecture
- Flask routes collect user inputs and delegate calculations to per-module physics helpers.
- Matplotlib figures are generated server-side and returned either as page fragments or embedded into PDF reports.
- Excel exports are built from the same arrays used for on-screen visualization.

---

## Numerical Implementation
- X-ray and Gamma modules use NumPy vectorization over fixed energy grids.
- X-ray plotting, PDF reporting, and Excel export share one common component-building path.
- Gamma sampling can be linear or logarithmic in energy, and the rendered x-axis follows that same choice.
- Proton range is obtained by stepwise integration of the unified stopping-power model.
- Proton Bragg curves are generated from the same stopping-power law used for stopping-power and range outputs.

---

## Validation Approach
- This version is checked for internal consistency between plot, report, and export paths.
- Qualitative regime behavior is tuned so the displayed dominance trends match the educational explanation of each module.
- The project should be treated as a didactic simulator, not as a benchmarked replacement for NIST XCOM, ESTAR, or treatment-planning software.

---

## Current Limitations
- Material properties are effective approximations, especially for compounds and custom proton materials.
- Gamma and X-ray coefficients are heuristic curves chosen for stable qualitative behavior, not for tabulated reference accuracy.
- Lateral proton scattering uses an approximate radiation-length estimate rather than a full transport model.

---

## Future Improvements
- Add optional reference-data overlays for selected materials.
- Introduce explicit uncertainty / approximation notes inside reports.
- Expand the material database with richer proton-specific properties where available.
