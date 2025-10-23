"""
app.py — Flask backend for the Medical Radiation Visualizer
------------------------------------------------------------
Main Flask app providing a web interface to visualize:
 - X-ray interactions with matter (Photoelectric, Compton, Rayleigh, Pair Production)
 - (future) Electron range and energy loss
 - (future) Proton Bragg Peak
 - (future) Shielding attenuation

Uses the modules under /modules/ for physics and visualization logic.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.lib.units import inch
import pandas as pd
import datetime, os
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))

from flask import Flask, render_template, request, jsonify, send_file
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Disable GUI backend (for headless servers)
import matplotlib.pyplot as plt
import time
from io import BytesIO
import pandas as pd
# ────────────────────────────────────────────────
# Import X-ray interaction modules
# ────────────────────────────────────────────────
from modules.xray.physics import (
    photoelectric_rel,
    compton_rel,
    rayleigh_rel,
    normalize_interactions,
    energy_grid,
)
from modules.xray.visualizer import (
    plot_interactions,
    compare_materials,
)
from core.constants import MATERIALS, get_property

# ────────────────────────────────────────────────
# Flask app initialization
# ────────────────────────────────────────────────
app = Flask(__name__)

# ────────────────────────────────────────────────
# Constants (average atomic numbers for key materials)
# ────────────────────────────────────────────────


def energy_grid(emin: float, emax: float, points: int = 400) -> np.ndarray:
    """Generate photon energy grid (keV)."""
    return np.logspace(np.log10(emin), np.log10(emax), points)


# ────────────────────────────────────────────────
# ROUTES
# ────────────────────────────────────────────────

@app.route("/")
def home():
    """Main dashboard page."""
    return render_template("index.html")



# ────────────────────────────────────────────────
# ROUTE: X-ray Interaction Visualizer
# ────────────────────────────────────────────────
@app.route("/xray", methods=["GET", "POST"])
def xray():
    """
    X-ray interaction visualizer (Photoelectric, Compton, Rayleigh)
    Supports:
     - Material selection or custom Z
     - Custom material naming
     - AJAX updates without reload
    """
    
    materials = list(MATERIALS.keys())
    plot_path = None
    material = ""
    material2 = ""
    emin = 20
    emax = 120
    show_photo = True
    show_compton = True
    show_rayleigh = True
    selected_Z = None
    scale = 'logarithmic' 
    z1_input = ""
    z2_input = ""
    name1 = ""
    name2 = ""

    if request.method == "POST":
        # 🧾 Gather input data
        material = request.form.get("material", "bone")
        material2 = request.form.get("material2", "")
        
        # 🌟 الإصلاح: وضع التحويل إلى float داخل try/except
        try:
            emin = float(request.form.get("emin", 20))
            emax = float(request.form.get("emax", 120))
        except ValueError:
             return jsonify({"error": "⚠️ Energy inputs must be valid numbers."}), 400

        # ✅ Energy validation
        if emin <= 0:
            emin = 1
        if emax <= emin:
            return jsonify({
                "error": "⚠️ Invalid range: Maximum energy must be greater than minimum energy."
            }), 400

        # ✅ Interaction toggles
        show_photo = "show_photo" in request.form
        show_compton = "show_compton" in request.form
        show_rayleigh = "show_rayleigh" in request.form

        # ✅ Read custom Z and names
        z1_input = request.form.get("z1", "").strip()
        z2_input = request.form.get("z2", "").strip()
        name1 = request.form.get("name1", "").strip()
        name2 = request.form.get("name2", "").strip()

        # ⚛️ Determine Z1
        # 🌟 الإصلاح: استخدام try/except لمعالجة Z1
        try:
            if material == "custom" and z1_input:
                Z1 = float(z1_input)
            else:
                Z1 = MATERIALS.get(material, {}).get("Z", 7.4)
            if Z1 <= 0: raise ValueError("Z1 must be positive.")
        except ValueError:
            return jsonify({"error": "⚠️ Atomic Number (Z₁) must be a valid number."}), 400
        except Exception:
             Z1 = MATERIALS.get(material, {}).get("Z", 7.4)
        
        # 🌟 تحديد K-edge, L-edge, والكثافة للمادة 1
        E_K1 = MATERIALS.get(material, {}).get("E_K", 1.0)
        E_L1 = MATERIALS.get(material, {}).get("E_L", 0.1)
        rho1 = MATERIALS.get(material, {}).get("rho", 1.0)
        # ✅ ضمان أن القيم ليست None
        E_K1 = E_K1 or 1.0
        E_L1 = E_L1 or 0.1
        rho1 = rho1 or 1.0


        
        # 🌟 NEW: جلب قيمة الكثافة المدخلة يدوياً للمادة المخصصة
        rho1_input = request.form.get("rho1", "").strip()
        
        if material == "custom":
            E_K1 = 0.0126 * (Z1 ** 2)
            E_L1 = 0.0016 * (Z1 ** 2) 
            try:
                rho1 = float(rho1_input) if rho1_input else 1.0 # استخدام الإدخال اليدوي أو 1.0
            except ValueError:
                return jsonify({"error": "⚠️ Density (ρ₁) must be a valid number."}), 400
            
        # ⚛️ Determine Z2
        # 🌟 الإصلاح: استخدام try/except لمعالجة Z2
        Z2 = None
        E_K2 = None
        E_L2 = None 
        rho2 = None 
        
        # 🌟 NEW: جلب قيمة الكثافة المدخلة يدوياً للمادة المخصصة 2
        rho2_input = request.form.get("rho2", "").strip()
        
        if material2:
            try:
                if material2 == "custom" and z2_input:
                    Z2 = float(z2_input)
                else:
                    Z2 = MATERIALS.get(material, {}).get("Z", 7.4)

                if Z2 <= 0: raise ValueError("Z2 must be positive.")
            except ValueError:
                return jsonify({"error": "⚠️ Atomic Number (Z₂) must be a valid number."}), 400
            except Exception:
                Z2 = MATERIALS.get(material2, {}).get("Z", 7.4)
                
            # 🌟 تحديد K-edge, L-edge, والكثافة للمادة 2
            E_K2 = MATERIALS.get(material2, {}).get("E_K", 1.0)
            E_L2 = MATERIALS.get(material2, {}).get("E_L", 0.1)
            rho2 = MATERIALS.get(material2, {}).get("rho", 1.0)
            # ✅ ضمان أن القيم ليست None
            E_K2 = E_K1 or 1.0
            E_L2 = E_L1 or 0.1
            rho2 = rho1 or 1.0

            
            if material2 == "custom":
                 E_K2 = 0.0126 * (Z2 ** 2)
                 E_L2 = 0.0016 * (Z2 ** 2)
                 try:
                     rho2 = float(rho2_input) if rho2_input else 1.0 # استخدام الإدخال اليدوي أو 1.0
                 except ValueError:
                     return jsonify({"error": "⚠️ Density (ρ₂) must be a valid number."}), 400

        # ✅ Replace names for custom materials
        if material == "custom":
            material = name1 or "Custom Material 1"
        if material2 == "custom":
            material2 = name2 or "Custom Material 2"

        selected_Z = Z1
        E = energy_grid(emin, emax)

        # 🧩 Define plot title
        if material2:
            title = f"{material.capitalize()} vs {material2.capitalize()}"
            # 🌟 تمرير جميع المتغيرات الجديدة إلى compare_materials
            fig, ax = compare_materials(
                Z1, Z2, E, material, material2, 
                E_K1, E_L1, rho1, # Params for Mat 1
                E_K2, E_L2, rho2, # Params for Mat 2
                show_rayleigh=show_rayleigh
            )
        else:
            title = f"{material.capitalize()} — X-ray Interactions"
            # 🌟 تمرير جميع المتغيرات الجديدة إلى plot_interactions
            fig, ax = plot_interactions(
                Z1, E,
                title=title,
                E_K=E_K1, 
                E_L=E_L1, # 🌟 L-edge
                rho=rho1, # 🌟 الكثافة
                show_photo=show_photo,
                show_compton=show_compton,
                show_rayleigh=show_rayleigh
            )

        # 🧹 Save plot
        os.makedirs("static/plots", exist_ok=True)
        plot_path = f"static/plots/{material}_{int(time.time())}.png"
        print("Saving plot to:", os.path.abspath(plot_path))
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        # ⚙️ Return only fragment for AJAX
        if request.headers.get("X-Requested-With", "").lower() == "xmlhttprequest":
            return render_template(
                "_xray_result.html",
                plot_path=plot_path,
                selected_material=material,
                selected_material2=material2,
                selected_Z=selected_Z,
                z1=z1_input,
                z2=z2_input,
                name1=name1,
                name2=name2,
                emin=emin,
                emax=emax,
                show_rayleigh=show_rayleigh,
                scale=scale,
                rho1=rho1_input, # 🌟 تمرير قيمة الكثافة المُدخلة للقالب
                rho2=rho2_input # 🌟 تمرير قيمة الكثافة المُدخلة للقالب
            )

    # 🔙 Render full template normally
    return render_template(
        "xray.html",
        materials=materials,
        plot_path=plot_path,
        selected_material=material,
        selected_material2=material2,
        selected_Z=selected_Z,
        emin=emin,
        emax=emax,
        show_photo=show_photo,
        show_compton=show_compton,
        show_rayleigh=show_rayleigh,
        z1=z1_input,
        z2=z2_input,
        name1=name1,
        name2=name2,
        scale=scale,
        rho1=None, # 🌟 يجب تمرير قيمة فارغة أو افتراضية للـ GET
        rho2=None
    )
# ============================================================
# 📄 Enhanced X-ray Interaction Report Generator (PDF)
# ============================================================




@app.route("/xray/report", methods=["POST"])
def xray_report():
    """
    Generate a professional PDF report for selected X-ray materials.
    Includes material data, computed interaction values, comparison,
    and formatted scientific analysis.
    """
    try:
        # === Retrieve form data ===
        material = request.form.get("material", "water")
        material2 = request.form.get("material2", "")
        emin = float(request.form.get("emin", 20))
        emax = float(request.form.get("emax", 120))
        show_photo = "show_photo" in request.form
        show_compton = "show_compton" in request.form
        show_rayleigh = "show_rayleigh" in request.form

        # === Import dependencies ===
        from core.constants import MATERIALS
        from modules.xray.physics import photoelectric_rel, compton_rel, rayleigh_rel, energy_grid

        # === Load material 1 constants ===
        mat_data = MATERIALS.get(material, MATERIALS["water"])
        Z1 = mat_data.get("Z", 7.4)
        rho1 = mat_data.get("rho", 1.0)
        E_K1 = mat_data.get("E_K", 1.0)
        E_L1 = mat_data.get("E_L", 0.1)

        # === Load material 2 constants if provided ===
        mat_data2 = MATERIALS.get(material2, None) if material2 else None
        Z2 = mat_data2.get("Z") if mat_data2 else None
        rho2 = mat_data2.get("rho") if mat_data2 else None

        # === Ensure valid numeric values ===
        E_K1 = E_K1 or 1.0
        E_L1 = E_L1 or 0.1
        rho1 = rho1 or 1.0

        # === Calculate interaction data ===
        E = energy_grid(emin, emax)
        data = {"Energy (keV)": E}
        if show_photo:
            data["Photoelectric"] = photoelectric_rel(Z1, E, E_K1, E_L1, rho1)
        if show_compton:
            data["Compton"] = compton_rel(Z1, E, rho1)
        if show_rayleigh:
            data["Rayleigh"] = rayleigh_rel(Z1, E, rho1)
        df = pd.DataFrame(data)

        # === Create summary interpretation ===
        summary = []
        if Z1 > 50:
            summary.append("High-Z material — strong Photoelectric effect at low energies.")
        elif Z1 < 15:
            summary.append("Low-Z material — Compton scattering dominates most of the range.")
        if emax > 100:
            summary.append("Compton scattering becomes more significant at higher energies.")
        if rho1 > 10:
            summary.append("High density increases total attenuation coefficient.")
        if material2:
            summary.append(f"Comparison between {material.capitalize()} and {material2.capitalize()} is shown.")
        summary_text = " ".join(summary) if summary else "Standard interaction behavior observed."

        # === Detect plot file ===
        plot_folder = "static/plots"
        plot_file = None
        if os.path.exists(plot_folder):
            for f in os.listdir(plot_folder):
                if material.lower() in f.lower() and f.endswith(".png"):
                    plot_file = os.path.join(plot_folder, f)
                    break

        # ============================================================
        # === Build PDF Report ===
        # ============================================================
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        story = []

        # === Styles ===
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="Heading", fontName="DejaVuSans", fontSize=16, leading=22, textColor=colors.darkblue, spaceAfter=12))
        styles.add(ParagraphStyle(name="NormalBold", fontName="DejaVuSans", fontSize=11, leading=14, textColor=colors.black, spaceAfter=6))
        styles.add(ParagraphStyle(name="Warning", fontName="DejaVuSans", fontSize=9, leading=13, textColor=colors.red, spaceAfter=8))
        # === Header ===
        logo_path = "static/logo.png"
        if os.path.exists(logo_path):
            story.append(Image(logo_path, width=1.5 * inch, height=1.5 * inch))
        story.append(Paragraph("X-ray Interaction Analysis Report", styles["Heading"]))
        story.append(Paragraph(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # === Material Parameters Table ===
        table_data = [["Parameter", "Value"],
                      ["Primary Material", material.capitalize()],
                      ["Atomic Number (Z₁)", f"{Z1:.2f}"],
                      ["Density (ρ₁, g/cm³)", f"{rho1:.3f}"]]

        if material2:
            table_data += [["Comparison Material", material2.capitalize()]]
            if Z2:
                table_data += [["Atomic Number (Z₂)", f"{Z2:.2f}"],
                               ["Density (ρ₂, g/cm³)", f"{rho2:.3f}"]]

        table_data += [["Energy Range (keV)", f"{emin} – {emax}"],
                       ["Included Interactions",
                        ", ".join([i for i, s in [("Photoelectric", show_photo),
                                                  ("Compton", show_compton),
                                                  ("Rayleigh", show_rayleigh)] if s])]]

        table = Table(table_data, colWidths=[2.5 * inch, 3.5 * inch])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3 * inch))

        # === Plot Image ===
        if plot_file and os.path.exists(plot_file):
            story.append(Paragraph("Figure 1. Interaction Cross-Sections", styles["NormalBold"]))
            story.append(Image(plot_file, width=5.5 * inch, height=3.5 * inch))
            story.append(Spacer(1, 0.2 * inch))

        story.append(PageBreak())

        # === Scientific Analysis ===
        story.append(Paragraph("Scientific Analysis", styles["Heading"]))
        story.append(Paragraph(summary_text, styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        # === Sample Data (Formatted Table) ===
        story.append(Paragraph("Sample Data (First 5 rows)", styles["NormalBold"]))
        formatted_data = [df.columns.tolist()]
        for row in df.head(5).itertuples(index=False):
            formatted_data.append([f"{v:.3g}" if isinstance(v, (int, float)) else str(v) for v in row])
        col_widths = [1.6 * inch] + [1.1 * inch] * (len(df.columns) - 1)
        t = Table(formatted_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3 * inch))

        # === Disclaimer ===
        story.append(Paragraph("WARNING", styles["Heading"]))
        story.append(Paragraph(
            "This simulation is for educational and research purposes only. "
            "It is not intended for clinical or diagnostic use. "
            "All results are approximate and based on simplified X-ray interaction models.",
            styles["Warning"]
        ))
        story.append(Spacer(1, 0.3 * inch))

        # === References ===
        story.append(Paragraph("References", styles["Heading"]))
        story.append(Paragraph(
            "1. Hubbell, J.H. & Seltzer, S.M. (NIST) X-ray mass attenuation coefficients (1995).<br/>"
            "2. Attix, F.H. (1986) Introduction to Radiological Physics and Radiation Dosimetry.<br/>"
            "3. Johns & Cunningham, The Physics of Radiology (1983).",
            styles["Normal"]
        ))
        story.append(Spacer(1, 0.3 * inch))

        # === Footer ===
        story.append(Paragraph("Generated by: Medical Radiation Visualizer © 2025 — Hassan Almoosa", styles["Normal"]))

        # === Build and Send PDF ===
        doc.build(story)
        pdf_buffer.seek(0)

        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"{material}_xray_report.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500


# ────────────────────────────────────────────────
# ROUTE: Download Excel data (AJAX)
# ────────────────────────────────────────────────

@app.route("/xray/download", methods=["POST"])
def download_xray_data():
    try:
        material = request.form.get("material", "water")
        material2 = request.form.get("material2", "")
        emin = float(request.form.get("emin", 20))
        emax = float(request.form.get("emax", 120))

        # ⚡ استخدم نفس المنطق المستخدم للرسم
        from modules.xray.physics import photoelectric_rel, compton_rel, rayleigh_rel, energy_grid
        from core.constants import MATERIALS

        Z1 = MATERIALS.get(material, {}).get("Z", 7.4)
        rho1 = MATERIALS.get(material, {}).get("rho", 1.0)
        E_K1 = MATERIALS.get(material, {}).get("E_K", 1.0)
        E_L1 = MATERIALS.get(material, {}).get("E_L", 0.1)

        # ✅ ضمان القيم ليست None
        E_K1 = E_K1 or 1.0
        E_L1 = E_L1 or 0.1
        rho1 = rho1 or 1.0

        E = energy_grid(emin, emax)
        pe = photoelectric_rel(Z1, E, E_K1, E_L1, rho1)
        compton = compton_rel(Z1, E, rho1)
        rayleigh = rayleigh_rel(Z1, E, rho1)

        df = pd.DataFrame({
            "Energy (keV)": E,
            "Photoelectric": pe,
            "Compton": compton,
            "Rayleigh": rayleigh
        })

        # 💾 إنشاء الملف المؤقت
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name=f"{material}_xray_data.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate Excel: {str(e)}"}), 500



# ────────────────────────────────────────────────
# ROUTE: Gamma-ray Interaction Visualizer
# ────────────────────────────────────────────────

@app.route("/gamma", methods=["GET", "POST"])
def gamma():
    from modules.gamma.visualizer import plot_gamma
    from modules.gamma.physics import energy_grid
    import time
    from flask import jsonify

    materials = list(MATERIALS.keys())
    plot_path = None
    material, material2 = "", ""
    emin, emax = 0.1, 10
    z_input, z_input2 = "", ""
    name1, name2 = "", ""
    rho1, rho2 = 1.0, 1.0
    Z1, Z2 = 13.8, None
    scale = "linear"

    if request.method == "POST":
        # === Read inputs ===
        material = request.form.get("material", "lead").strip()
        material2 = request.form.get("material2", "").strip()
        z_input = (request.form.get("z1", "") or "").strip()
        z_input2 = (request.form.get("z2", "") or "").strip()
        name1 = (request.form.get("name1", "") or "").strip()
        name2 = (request.form.get("name2", "") or "").strip()
        scale = request.form.get("scale", "linear")
        rho1 = float(request.form.get("rho1", 1.0) or 1.0)
        rho2 = float(request.form.get("rho2", 1.0) or 1.0)

        # === Energy range ===
        try:
            emin = float(request.form.get("emin", 0.1))
            emax = float(request.form.get("emax", 10))
        except ValueError:
            return jsonify({"error": "⚠️ Energy inputs must be numeric."}), 400
        if emin <= 0:
            return jsonify({"error": "⚠️ Energy inputs must be positive."}), 400
        if emax <= emin:
            return jsonify({"error": "⚠️ Maximum energy must be greater than minimum energy."}), 400

        # === Z logic (custom or default) ===
        def get_Z(material_name, z_field, name_field):
            if material_name == "custom":
                if not z_field:
                    raise ValueError("For Custom material, please enter a valid atomic number (Z).")
                try:
                    z_val = float(z_field.replace(",", "."))
                except ValueError:
                    raise ValueError("Atomic number (Z) must be numeric.")
                if z_val <= 0 or z_val > 118:
                    raise ValueError("Atomic number (Z) must be between 1 and 118.")
                return z_val, name_field.strip() or "Custom Material"
            else:
                mat = MATERIALS.get(material_name, {})
                return mat.get("Z", 7.4), material_name.capitalize()

        try:
            Z1, material = get_Z(material, z_input, name1)
            if material2:
                Z2, material2 = get_Z(material2, z_input2, name2)
        except ValueError as e:
            return jsonify({"error": f"⚠️ {str(e)}"}), 400

        # === Compute and plot ===
        E = energy_grid(emin, emax, points=300, scale=scale)
        title = f"{material} — Gamma-ray Interactions"
        if material2:
            title = f"{material} vs {material2} — Gamma-ray Interactions"

        fig, ax = plot_gamma(
            Z1, E, title,
            rho1=rho1,
            Z2=Z2, rho2=rho2 if material2 else None,
            material1=material, material2=material2 if material2 else None,
            show_mass_coeff=False
        )

        # === Save plot ===
        os.makedirs("static/plots", exist_ok=True)
        plot_path = f"static/plots/{material}_gamma_{int(time.time())}.png"
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        # === AJAX partial response ===
        if request.headers.get("X-Requested-With", "").lower() == "xmlhttprequest":
            return render_template(
                "_gammaray_result.html",
                plot_path=plot_path,
                selected_material=material,
                selected_material2=material2,
                selected_Z=Z1,
                selected_Z2=Z2,
                emin=emin,
                emax=emax,
                scale=scale,
                rho1=rho1,
                rho2=rho2,
                name1=name1,
                name2=name2,
            )

    # === Full page render ===
    # 🖥️ العرض الكامل (GET أو POST بعد التوليد)
    return render_template(
        "gamma.html",
        materials=materials,
        plot_path=plot_path,
        selected_material=material,
        selected_material2=material2 if "material2" in locals() else None,
        z1=z_input,
        z2=z_input2 if "z_input2" in locals() else None,
        emin=emin,
        emax=emax,
        name1=name1,
        name2=name2 if "name2" in locals() else None,
        rho1=rho1 if "rho1" in locals() else None,
        rho2=rho2 if "rho2" in locals() else None,
        scale=scale,
    )

# ---------------- Gamma: Excel download ----------------


@app.route("/gamma/download", methods=["POST"])
def download_gamma_data():
    """
    Export Gamma-ray interaction data (Energy, Compton, Pair, Total) to Excel.
    Supports one or two materials. Energy is in MeV.
    """
    try:
        from core.constants import MATERIALS
        from modules.gamma.physics import energy_grid, gamma_interactions

        material  = (request.form.get("material", "") or "").strip()
        material2 = (request.form.get("material2", "") or "").strip()
        name1     = (request.form.get("name1", "") or "").strip()
        name2     = (request.form.get("name2", "") or "").strip()
        z1_raw    = (request.form.get("z1", "") or "").strip()
        z2_raw    = (request.form.get("z2", "") or "").strip()
        rho1      = float(request.form.get("rho1", 1.0) or 1.0)
        rho2      = float(request.form.get("rho2", 1.0) or 1.0)
        scale     = request.form.get("scale", "linear")

        # energy range in MeV
        emin = float(request.form.get("emin", 0.1))
        emax = float(request.form.get("emax", 10))

        if emin <= 0 or emax <= emin:
            return jsonify({"error": "Invalid energy range."}), 400

        def resolve_Z_and_label(mat, z_raw, fallback_label):
            if mat == "custom":
                if not z_raw:
                    raise ValueError("For custom material, please enter Z.")
                try:
                    Z = float(z_raw.replace(",", "."))
                except ValueError:
                    raise ValueError("Atomic number (Z) must be numeric.")
                if Z <= 0 or Z > 118:
                    raise ValueError("Atomic number (Z) must be 1–118.")
                label = fallback_label or "Custom Material"
            else:
                Z = MATERIALS.get(mat, {}).get("Z", 7.4)
                label = mat.capitalize() if mat else "Material"
            return Z, label

        Z1, label1 = resolve_Z_and_label(material, z1_raw, name1)
        Z2 = label2 = None
        if material2:
            Z2, label2 = resolve_Z_and_label(material2, z2_raw, name2)

        # compute energy grid (MeV)
        E = energy_grid(emin, emax, points=300, scale=scale)

        d1 = gamma_interactions(Z1, rho1, E)
        df = pd.DataFrame({
            "Energy (MeV)": E,
            f"{label1} — Compton μ (1/cm)": d1["compton_mu"],
            f"{label1} — Pair μ (1/cm)":    d1["pair_mu"],
            f"{label1} — Total μ (1/cm)":   d1["total_mu"],
        })

        if Z2 is not None:
            d2 = gamma_interactions(Z2, rho2, E)
            df[f"{label2} — Compton μ (1/cm)"] = d2["compton_mu"]
            df[f"{label2} — Pair μ (1/cm)"]    = d2["pair_mu"]
            df[f"{label2} — Total μ (1/cm)"]   = d2["total_mu"]

        # write to Excel in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Gamma")
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name=f"{label1.lower()}_gamma_data.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate Excel: {str(e)}"}), 500


# ---------------- Gamma: PDF report ----------------

# Register DejaVuSans to render symbols like μ properly
try:
    pdfmetrics.registerFont(TTFont("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
except Exception:
    pass

@app.route("/gamma/report", methods=["POST"])
def gamma_report():
    """
    Generate a Gamma-ray PDF report (parameters, plot, short analysis).
    """
    try:
        from core.constants import MATERIALS
        from modules.gamma.physics import energy_grid, gamma_interactions, PAIR_THRESHOLD_MEV
        from modules.gamma.visualizer import plot_gamma

        material  = (request.form.get("material", "") or "").strip()
        material2 = (request.form.get("material2", "") or "").strip()
        name1     = (request.form.get("name1", "") or "").strip()
        name2     = (request.form.get("name2", "") or "").strip()
        z1_raw    = (request.form.get("z1", "") or "").strip()
        z2_raw    = (request.form.get("z2", "") or "").strip()
        rho1      = float(request.form.get("rho1", 1.0) or 1.0)
        rho2      = float(request.form.get("rho2", 1.0) or 1.0)
        scale     = request.form.get("scale", "linear")
        emin      = float(request.form.get("emin", 0.1))
        emax      = float(request.form.get("emax", 10))

        if emin <= 0 or emax <= emin:
            return jsonify({"error": "Invalid energy range."}), 400

        def resolve_Z_and_label(mat, z_raw, fallback_label):
            if mat == "custom":
                if not z_raw:
                    raise ValueError("For custom material, please enter Z.")
                try:
                    Z = float(z_raw.replace(",", "."))
                except ValueError:
                    raise ValueError("Atomic number (Z) must be numeric.")
                if Z <= 0 or Z > 118:
                    raise ValueError("Atomic number (Z) must be 1–118.")
                label = fallback_label or "Custom Material"
            else:
                Z = MATERIALS.get(mat, {}).get("Z", 7.4)
                label = mat.capitalize() if mat else "Material"
            return Z, label

        Z1, label1 = resolve_Z_and_label(material, z1_raw, name1)
        Z2 = label2 = None
        if material2:
            Z2, label2 = resolve_Z_and_label(material2, z2_raw, name2)

        # Build plot (same logic as UI)
        E = energy_grid(emin, emax, points=300, scale=scale)
        title = f"{label1} — Gamma-ray Interactions" if not label2 else f"{label1} vs {label2} — Gamma-ray Interactions"
        fig, ax = plot_gamma(
            Z1, E, title, rho1=rho1,
            Z2=Z2, rho2=(rho2 if Z2 is not None else None),
            material1=label1, material2=(label2 if Z2 is not None else None),
            show_mass_coeff=False
        )

        # Save a temporary plot file to embed
        os.makedirs("static/plots", exist_ok=True)
        plot_path = f"static/plots/{label1.lower()}_gamma_report.png"
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        # Prepare PDF
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="H", fontName="DejaVuSans", fontSize=16, leading=22, textColor=colors.darkblue, spaceAfter=12))
        styles.add(ParagraphStyle(name="Warn", fontName="DejaVuSans", fontSize=9, leading=13, textColor=colors.red, spaceAfter=8))

        story = []
        story.append(Paragraph("Gamma-ray Interaction Analysis Report", styles["H"]))
        story.append(Paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        # Parameters table
        rows = [
            ["Parameter", "Value"],
            ["Primary Material", label1],
            ["Atomic Number (Z₁)", f"{Z1:.2f}"],
            ["Density (ρ₁, g/cm³)", f"{rho1:.3f}"],
            ["Energy Range (MeV)", f"{emin} – {emax} ({'Log' if scale=='log' else 'Linear'} scale)"],
        ]
        if Z2 is not None:
            rows += [
                ["Comparison Material", label2],
                ["Atomic Number (Z₂)", f"{Z2:.2f}"],
                ["Density (ρ₂, g/cm³)", f"{rho2:.3f}"],
            ]
        tbl = Table(rows, colWidths=[2.7*inch, 3.3*inch])
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,-1), "DejaVuSans"),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.25 * inch))

        # Plot image
        if os.path.exists(plot_path):
            story.append(Image(plot_path, width=5.6*inch, height=3.4*inch))
            story.append(Spacer(1, 0.2 * inch))

        # Brief interpretation
        interp = []
        if emax >= 1.022:
            interp.append("Pair production becomes available above 1.022 MeV; its contribution grows with energy and Z.")
        else:
            interp.append("Pair production is below threshold in the selected range.")
        interp.append("Compton scattering dominates the MeV range; total attenuation decreases slowly with energy.")
        story.append(Paragraph(" ".join(interp), styles["Normal"]))
        story.append(Spacer(1, 0.25 * inch))

        # Disclaimer
        story.append(Paragraph(
            "WARNING: This report is for educational and research training only and must not be used for clinical decisions.",
            styles["Warn"]
        ))

        doc.build(story)
        pdf_buffer.seek(0)

        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"{label1.lower()}_gamma_report.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500



# ============================================================
# ⚛️ Proton Interaction Visualizer — Flask Routes
# ============================================================
from modules.protons.visualizer import plot_proton_interaction
from modules.protons.physics import bragg_curve, stopping_power_curve, range_vs_energy, lateral_sigma_curve
from core.constants import MATERIALS

import io
import datetime as dt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from flask import render_template, request, send_file, jsonify
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader


# ===========================================================
# ROUTE: Proton 
# ============================================================

@app.route("/proton")
def proton_page():
    """Render Proton module page."""
    return render_template("proton.html", materials=list(MATERIALS.keys()))


@app.route("/proton/plot", methods=["POST"])
def plot_proton():
    """Generate Proton plot and return HTML partial."""
    try:
        params = request.form.to_dict() or {}
        mode = params.get("mode", "bragg")

        # ✅ ensure material exists
        material = params.get("material", "water")
        if material not in MATERIALS:
            material = "water"
        params["material"] = material

        for key in ["E0", "dx", "emin", "emax", "npts", "zmax"]:
            if key in params:
                try:
                    params[key] = float(params[key])
                except ValueError:
                    pass

        fig, ax = plot_proton_interaction(mode, params)
        plot_path = "static/plots/proton_plot.png"
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        return render_template(
            "_proton_result.html",
            plot_path=plot_path,
            material=material,
            E0=params.get("E0", 150),
            mode=mode
        )

    except Exception as e:
        import traceback
        print("❌ Proton error:", e)
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/proton/download", methods=["POST"])
def download_proton():
    """Export data as Excel file."""
    params = request.form.to_dict() or {}
    mode = params.get("mode", "bragg")
    material = params.get("material", "water")

    for key in ["E0", "dx", "emin", "emax", "npts", "zmax"]:
        if key in params:
            try:
                params[key] = float(params[key])
            except ValueError:
                pass

    # Select data generator
    if mode == "bragg":
        x, y, _ = bragg_curve(params["E0"], material, dx_cm=params.get("dx", 0.01))
        data = pd.DataFrame({"Depth (cm)": x, "Relative Dose": y})
    elif mode == "stopping":
        energies = np.linspace(params.get("emin", 10), params.get("emax", 250), int(params.get("npts", 120)))
        x, y = stopping_power_curve(energies, material)
        data = pd.DataFrame({"Energy (MeV)": x, "Mass Stopping Power (MeV·cm²/g)": y})
    elif mode == "range":
        energies = np.linspace(params.get("emin", 10), params.get("emax", 250), int(params.get("npts", 120)))
        x, y = range_vs_energy(energies, material)
        data = pd.DataFrame({"Initial Energy (MeV)": x, "CSDA Range (cm)": y})
    elif mode == "lateral":
        depths = np.linspace(0, params.get("zmax", 25), int(params.get("npts", 120)))
        x, y = lateral_sigma_curve(depths, params.get("E0", 150), material)
        data = pd.DataFrame({"Depth (cm)": x, "Lateral Spread σ (cm)": y})
    else:
        return jsonify({"ok": False, "error": "Unknown mode"}), 400

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        data.to_excel(writer, index=False, sheet_name="proton_data")
        meta = pd.DataFrame({"Parameter": list(params.keys()), "Value": list(params.values())})
        meta.to_excel(writer, index=False, sheet_name="parameters")

    buf.seek(0)
    filename = f"proton_data_{mode}_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(buf, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/proton/report", methods=["POST"])
def report_proton():
    """
    📄 Proton Interaction Report — Scientific PDF
    Generates a professional, research-style PDF report
    with figure, parameters table, sample data, and disclaimer.
    """
    try:
        from modules.protons.visualizer import plot_proton_interaction
        from modules.protons.physics import (
            bragg_curve, stopping_power_curve, range_vs_energy, lateral_sigma_curve
        )
        from core.constants import MATERIALS

        # === Extract parameters ===
        params = request.form.to_dict() or {}
        mode = params.get("mode", "bragg")
        material = params.get("material", "water")

        # Parse numeric values safely
        for key in ["E0", "dx", "emin", "emax", "npts", "zmax"]:
            if key in params:
                try:
                    params[key] = float(params[key])
                except ValueError:
                    pass

        # === Generate figure ===
        fig, ax = plot_proton_interaction(mode, params)
        os.makedirs("static/plots", exist_ok=True)
        plot_path = f"static/plots/proton_report_{int(time.time())}.png"
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        # === Compute representative data for table ===
        if mode == "bragg":
            x, y, _ = bragg_curve(params.get("E0", 150), material, dx_cm=params.get("dx", 0.01))
            df = pd.DataFrame({"Depth (cm)": x, "Relative Dose": y})
        elif mode == "stopping":
            energies = np.linspace(params.get("emin", 10), params.get("emax", 250), int(params.get("npts", 120)))
            x, y = stopping_power_curve(energies, material)
            df = pd.DataFrame({"Energy (MeV)": x, "Mass Stopping Power (MeV·cm²/g)": y})
        elif mode == "range":
            energies = np.linspace(params.get("emin", 10), params.get("emax", 250), int(params.get("npts", 120)))
            x, y = range_vs_energy(energies, material)
            df = pd.DataFrame({"Initial Energy (MeV)": x, "CSDA Range (cm)": y})
        elif mode == "lateral":
            depths = np.linspace(0, params.get("zmax", 25), int(params.get("npts", 120)))
            x, y = lateral_sigma_curve(depths, params.get("E0", 150), material)
            df = pd.DataFrame({"Depth (cm)": x, "Lateral Spread σ (cm)": y})
        else:
            raise ValueError("Unknown mode selected")

        # === Prepare PDF ===
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        story = []

        # === Styles ===
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="Heading", fontName="DejaVuSans", fontSize=16, leading=22,
                                  textColor=colors.darkblue, spaceAfter=12))
        styles.add(ParagraphStyle(name="NormalBold", fontName="DejaVuSans", fontSize=11, leading=14,
                                  textColor=colors.black, spaceAfter=6))
        styles.add(ParagraphStyle(name="Warning", fontName="DejaVuSans", fontSize=9, leading=13,
                                  textColor=colors.red, spaceAfter=8))
        styles.add(ParagraphStyle(name="Scientific", fontName="DejaVuSans", fontSize=10, leading=14,
                                  textColor=colors.black, spaceAfter=6, italic=True))

        # === Dynamic Report Title ===
        E0_val = params.get("E0", 150)
        mode_label = {
            "bragg": "Bragg Peak",
            "stopping": "Stopping Power",
            "range": "Range–Energy",
            "lateral": "Lateral Scattering"
        }.get(mode, "Interaction")

        title_text = f"Proton {mode_label} Report — {E0_val:.0f} MeV in {material.capitalize()}"
        story.append(Paragraph(title_text, styles["Heading"]))
        story.append(Paragraph(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                               styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        # === Material Parameters Table ===
        mat_data = MATERIALS.get(material, {"Z": 7.4, "rho": 1.0})
        table_data = [
            ["Parameter", "Value"],
            ["Material", material.capitalize()],
            ["Atomic Number (Z)", f"{mat_data.get('Z', 7.4):.2f}"],
            ["Density (ρ, g/cm³)", f"{mat_data.get('rho', 1.0):.3f}"],
            ["Mode", mode.capitalize()],
            ["Initial Energy (MeV)", f"{params.get('E0', 150):.2f}"],
        ]
        tbl = Table(table_data, colWidths=[2.7 * inch, 3.3 * inch])
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.3 * inch))

        # === Figure ===
        if plot_path and os.path.exists(plot_path):
            story.append(Paragraph("Figure 1. Proton Interaction Curve", styles["NormalBold"]))
            story.append(Image(plot_path, width=5.5 * inch, height=3.5 * inch))
            story.append(Spacer(1, 0.25 * inch))
            story.append(Paragraph(
                f"<i>Simulated depth–dose distribution for protons in {material.capitalize()} "
                f"(E₀ = {params.get('E0', 150)} MeV).</i>",
                styles["Scientific"]
            ))
            story.append(Spacer(1, 0.2 * inch))
        else:
            story.append(Paragraph("⚠️ No figure available for this configuration.", styles["Warning"]))
            story.append(Spacer(1, 0.25 * inch))

        # === Sample Data ===
        story.append(Paragraph("Sample Data (First 5 Rows)", styles["NormalBold"]))
        formatted_data = [df.columns.tolist()]
        for row in df.head(5).itertuples(index=False):
            formatted_data.append([f"{v:.3g}" if isinstance(v, (int, float)) else str(v) for v in row])
        col_widths = [1.6 * inch] + [1.2 * inch] * (len(df.columns) - 1)
        t = Table(formatted_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3 * inch))

        # === Scientific Analysis ===
        story.append(Paragraph("Scientific Interpretation", styles["Heading"]))
        if mode == "bragg":
            interp = "Bragg peak observed near the stopping depth — typical for therapeutic proton beams."
        elif mode == "stopping":
            interp = "Stopping power decreases gradually with increasing energy, consistent with Bethe–Bloch predictions."
        elif mode == "range":
            interp = "Range grows approximately linearly with initial energy below 200 MeV; deviations occur at higher energies."
        elif mode == "lateral":
            interp = "Lateral scattering increases slowly with depth due to multiple Coulomb scattering effects."
        else:
            interp = "Results consistent with theoretical proton–matter interactions."
        story.append(Paragraph(interp, styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        # === Disclaimer ===
        story.append(Paragraph("DISCLAIMER", styles["Heading"]))
        story.append(Paragraph(
            "This report is generated for academic and research use only. "
            "It is not intended for clinical, diagnostic, or therapeutic applications. "
            "Results are computed using simplified models of proton interactions.",
            styles["Warning"]
        ))
        story.append(Spacer(1, 0.3 * inch))

        # === Footer ===
        story.append(Paragraph(
            "Generated by: Medical Radiation Visualizer © 2025 — Hassan Almoosa",
            styles["Normal"]
        ))

        # ✅ Validate all Flowables
        valid_story = []
        for i, item in enumerate(story):
            if hasattr(item, "wrap"):
                valid_story.append(item)
            else:
                print(f"⚠️ Skipped non-flowable at index {i}: {type(item)}")

        # === Build and Send PDF ===
        doc.build(valid_story)
        pdf_buffer.seek(0)

        filename = f"{material}_proton_report_{int(time.time())}.pdf"
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf"
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate Proton report: {str(e)}"}), 500

############################################
@app.route("/electron")
def electron():
    return render_template("electron.html")


@app.route("/shielding")
def shielding():
    return render_template("shielding.html")


# ────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
