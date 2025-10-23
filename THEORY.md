# ⚛️ Theoretical Background

This document summarizes the physical principles behind each interaction type.

---

## ☢️ X-ray Interactions
Dominated by **photoelectric absorption**, **Compton scattering**, and **Rayleigh scattering**.  
Linear attenuation coefficient:
\[
I = I_0 e^{-\mu x}
\]
with μ = μ_pe + μ_coh + μ_incoh.

---

## ⚛️ Gamma-ray Interactions
1. **Compton Scattering** — modeled by the Klein–Nishina formula.  
2. **Pair Production** — modeled using the Bethe–Heitler approximation.  
3. **Photoelectric Effect** — significant at low energies ( E < 0.1 MeV ).

---

## 💥 Proton Interactions
Energy loss governed by the **Bethe–Bloch equation**.  
Characteristic Bragg peak near the end of the range.

---

## ⚡ Electron Interactions (Planned)
- **Collisional losses:** Bethe formula with low-energy corrections.  
- **Radiative losses:** Bremsstrahlung.  
- **Total stopping power:** sum of both.  
- **CSDA range:** numerical integration of 1/(dE/dx).  
- **Highland formula:** multiple Coulomb scattering angle.

---

## 🧱 Shielding (Planned)
Attenuation follows the exponential law:
\[
I = I_0 e^{-\mu x}
\]
Half-value layer (HVL) = ln(2)/μ, Tenth-value layer (TVL) = ln(10)/μ.
