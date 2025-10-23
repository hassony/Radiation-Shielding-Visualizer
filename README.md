# 🎓 Medical Radiation Visualizer

An **interactive educational toolkit** built with **Python + Flask** to visualize how different types of radiation interact with matter — designed for **medical physics students and researchers**.

---

## 🔔 What’s New (Oct 2025)

* ✅ **X-ray**: Added **K-edge** visualization when scanning energies across high-Z materials.
* ✅ **Gamma-ray**: Added **axis toggle** between **Linear** and **Log** scales for cross-sections/attenuation plots.

---

## 🧠 Overview

This project provides simplified, didactic simulations of:

| Module                        | Description                                                                                                                       |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| ☢️ **X-ray Interactions**     | Visualizes relative probabilities of Photoelectric, Compton, and Rayleigh. Includes **K-edge** highlighting for high-Z materials. |
| ☢️ **Gamma-ray Interactions** | Shows attenuation/cross-section behavior with **Log/Linear axis toggle** (and support for pair production at higher energies).    |
| ⚡ **Electrons**               | Simulates energy loss and range of electrons in matter.                                                                           |
| 💥 **Protons (Bragg Peak)**   | Demonstrates how proton energy affects depth–dose distribution (Bragg Peak).                                                      |
| 🧱 **Dose & Shielding**       | Compares attenuation in different shielding materials using Beer–Lambert’s law.                                                   |

> 🧩 All models are **simplified for teaching** — not for clinical use.

---

## 🧱 Project Structure

```
MedicalRadiationVisualizer/
├── app.py                      # Flask entry point
│
├── core/
│   ├── utils.py                # Shared helper functions
│   └── constants.py            # Global constants (Z_MAP, materials, defaults)
│
├── modules/
│   ├── xray/                   # X-ray simulation (photoelectric, Compton, Rayleigh, K-edge)
│   ├── gamma/                  # Gamma simulation (Compton, PP, log/linear axis toggle)
│   ├── protons/                # Bragg Peak simulation
│   ├── electrons/              # Electron energy loss & range
│   └── shielding/              # Attenuation / HVL comparison
│
├── templates/                  # HTML views (Flask Jinja)
│   ├── index.html              # Main dashboard
│   ├── xray.html               # X-ray interaction interface (with K-edge highlight)
│   ├── gamma.html              # Gamma interface (axis toggle: Log/Linear)
│   ├── proton.html             # Bragg Peak simulator
│   ├── electron.html           # Electron visualization
│   └── shielding.html          # Shielding comparison
│
├── static/
│   ├── css/
│   │   └── style.css           # Unified academic styling
│   ├── js/
│   │   └── main.js             # Unified AJAX handlers for all modules
│   └── plots/                  # Generated charts (PNG)
│
└── requirements.txt
```

---

## ⚙️ Installation

### 1️⃣ Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Run the app

```bash
python app.py
```

Then open:

> 🌐 [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

---

## 🧩 Technologies Used

* **Python 3.12+**
* **Flask 3.0+**
* **Matplotlib**
* **NumPy**
* *(Optional)* **pyngrok** — to expose your app temporarily.

---

## 🧪 Educational Goals

This project helps students **visualize radiation–matter interactions** and understand:

* Differences in dose deposition between photons, electrons, and protons.
* Dependence of attenuation on atomic number and energy (incl. **K-edge** behavior).
* Bragg Peak and its medical significance.
* Comparative shielding efficiency across materials.
* Effect of **axis scaling (Log vs Linear)** on interpreting gamma data.

---

## 🔧 Feature Notes

* **X-ray (K-edge):** when a selected material has a K-shell binding energy within the scanned range, the plot highlights the **K-edge** region and can annotate the approximate edge energy.
* **Gamma (Log/Linear):** a simple toggle switch updates the plot **without page reload** via AJAX, helping students see how scaling changes interpretation of slopes and separations.

---

## 🚀 Run on Google Colab (Optional)

You can experiment with simplified versions of each module directly on Google Colab without local setup:

```python
!git clone https://github.com/YOUR_USERNAME/MedicalRadiationVisualizer.git
%cd MedicalRadiationVisualizer
!pip install -r requirements.txt

# (Optional) expose Flask via ngrok
from pyngrok import ngrok
!python app.py &
public_url = ngrok.connect(5000)
print("App running at:", public_url)
```

---

## 🧠 Example Screenshots

|               X-rays (K-edge)               |             Gamma (Log vs Linear)            |
| :-----------------------------------------: | :------------------------------------------: |
| ![X-ray Demo](static/plots/xray_sample.png) | ![Gamma Demo](static/plots/gamma_sample.png) |

*(These images are generated when running the app.)*

---

## ⚠️ Disclaimer

> This software is **for educational and research training purposes only**.
> Do not use it for clinical treatment planning or real patient dose estimation.

---

## 💖 Support the Project

This project is self-funded and developed by **Hassan Almoosa**.  
If you find it useful for education or research, consider supporting its continuation:

- ☕ Buy me a coffee: [https://buymeacoffee.com/yourlink]
- 💸 Donate via PayPal: [https://paypal.me/yourlink]
- 🌟 Or simply star the repo to show support!

Your help keeps this educational tool alive and evolving.

## 📜 License



---

## ⭐ Acknowledgements

Inspired by the goal of making **medical physics** education accessible and interactive.
Thanks to educators who blend theory with visualization.

---
