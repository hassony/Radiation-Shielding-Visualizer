# ⚙️ Physics Models Implemented

## ☢️ X-ray
- Mass attenuation coefficients from NIST XCOM tables.  
- Dependence μ/ρ ≈ Z³ / E³ for photoelectric region.  
- Compton scattering via Klein–Nishina approximation.

---

## ⚛️ Gamma-ray
- **Klein–Nishina:** differential cross-section for Compton scattering.  
- **Bethe–Heitler:** pair-production cross-section for E > 1.022 MeV.  
- Density effects via ρ scaling.

---

## 💥 Proton
- **Bethe–Bloch formula** for stopping power:  
  \[
  -\frac{dE}{dx} = \frac{4\pi N_A r_e^2 m_e c^2 Z}{A\beta^2}
  \left[\ln\!\frac{2m_e c^2\beta^2\gamma^2}{I} - \beta^2\right]
  \]
- **Range:** numerical integration over E.  
- **Bragg curve:** S(E) × density correction.

---

## ⚡ Electron (Planned)
- **Bethe formula** for collisional loss.  
- **Bremsstrahlung** radiative loss ≈ C·Z·E.  
- **Total stopping power:** S_total = S_coll + S_rad.  
- **CSDA range:** R = ∫ dE / S_total(E).  
- **Highland scattering:** θ₀ ≈ (13.6 MeV)/(β p) √(x/X₀)[1 + 0.038 ln(x/X₀)].

---

## 🧱 Shielding (Planned)
- **Exponential attenuation law**.  
- **Build-up factors** for broad beam.  
- **HVL/TVL thickness** calculations.

---

### 🔬 Constants and Sources
Values of Z, A, ρ, I (eV) taken from **NIST ESTAR / ICRU 44 / NASA TP-2274**.
