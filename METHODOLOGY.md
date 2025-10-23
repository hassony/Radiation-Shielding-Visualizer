# 🧠 Computational Methodology

---

## Architecture
- Modular Flask app with separate routes for each radiation type.  
- Templates rendered via Jinja2 and asynchronous AJAX calls.  
- Plot generation through Matplotlib saved as temporary PNG for display.  
- PDF and Excel exports via ReportLab and OpenPyXL.

---

## Numerical Implementation
- **Energy range:** logarithmic or linear sampling (0.01 – 100 MeV).  
- **Cross-sections:** computed per model using NumPy vectorization.  
- **Integration:** trapezoidal rule for range and dose calculations.  
- **Scaling:** density-corrected results (μ ∝ ρ, S ∝ ρ).

---

## Validation
- Benchmarked against NIST XCOM / ESTAR data for reference materials.  
- Cross-checked HVL and stopping power trends with ICRU 44.  
- Plots verified for energy-dependent consistency.

---

## Future Enhancements
- Add **real-time plot updates (AJAX preview)**.  
- Integrate **automatic report generation** with dynamic citations.  
- Implement **Electron & Shielding modules** with high-precision physics.  
- Extend material database with auto import from NIST tables.

