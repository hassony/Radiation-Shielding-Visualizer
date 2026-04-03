"""
Medical Radiation Visualizer — Flask Backend
---------------------------------------------
Provides an interactive Flask web interface for visualizing:
- X-ray interactions with matter (Photoelectric, Compton, Rayleigh)
- Gamma-ray interactions (Compton scattering, Pair production)
- Proton depth–dose distributions (Bragg Peak)
- Electron interactions and shielding (future modules)

Developed for educational and research use in medical physics.
"""

# ============================================================
# ===============  LIBRARIES AND GLOBAL IMPORTS  ==============
# ============================================================

from flask import Flask, render_template, request, jsonify, send_file
import os, time, datetime, io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Disable GUI backend for headless environments
import matplotlib.pyplot as plt

# PDF generation (ReportLab)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import inch

# ============================================================
# ==================  LOCAL FONT REGISTRATION  ================
# ============================================================

def _configure_pdf_fonts():
    project_font_dir = os.path.join("static", "fonts")
    candidates = [
        (
            "DejaVuSans",
            {
                "normal": os.path.join(project_font_dir, "DejaVuSans.ttf"),
                "bold": os.path.join(project_font_dir, "DejaVuSans-Bold.ttf"),
                "italic": os.path.join(project_font_dir, "DejaVuSans-Oblique.ttf"),
                "boldItalic": os.path.join(project_font_dir, "DejaVuSans-BoldOblique.ttf"),
            },
        ),
        (
            "Arial",
            {
                "normal": r"C:\Windows\Fonts\arial.ttf",
                "bold": r"C:\Windows\Fonts\arialbd.ttf",
                "italic": r"C:\Windows\Fonts\ariali.ttf",
                "boldItalic": r"C:\Windows\Fonts\arialbi.ttf",
            },
        ),
    ]

    for family, paths in candidates:
        normal_path = paths["normal"]
        if not os.path.exists(normal_path):
            continue

        variants = {
            "normal": family,
            "bold": f"{family}-Bold",
            "italic": f"{family}-Italic",
            "boldItalic": f"{family}-BoldItalic",
        }
        pdfmetrics.registerFont(TTFont(variants["normal"], normal_path))

        for key in ("bold", "italic", "boldItalic"):
            path = paths[key]
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(variants[key], path))
            else:
                variants[key] = variants["normal"]

        pdfmetrics.registerFontFamily(
            family,
            normal=variants["normal"],
            bold=variants["bold"],
            italic=variants["italic"],
            boldItalic=variants["boldItalic"],
        )
        return variants

    print("Warning: No project/system TrueType font found for PDF export. Falling back to Helvetica.")
    return {
        "normal": "Helvetica",
        "bold": "Helvetica-Bold",
        "italic": "Helvetica-Oblique",
        "boldItalic": "Helvetica-BoldOblique",
    }


PDF_FONTS = _configure_pdf_fonts()
PDF_FONT = PDF_FONTS["normal"]
PDF_FONT_BOLD = PDF_FONTS["bold"]
PDF_FONT_ITALIC = PDF_FONTS["italic"]

PDF_TEXT_REPLACEMENTS = {
    "ρ": "rho",
    "σ": "sigma",
    "μ": "mu",
    "₀": "0",
    "₁": "1",
    "₂": "2",
    "₃": "3",
    "₄": "4",
    "₅": "5",
    "₆": "6",
    "₇": "7",
    "₈": "8",
    "₉": "9",
    "²": "^2",
    "³": "^3",
    "·": "*",
    "—": "-",
    "–": "-",
    "©": "(C)",
}


def _create_pdf_styles():
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = PDF_FONT
    if "BodyText" in styles:
        styles["BodyText"].fontName = PDF_FONT
    if "Italic" in styles:
        styles["Italic"].fontName = PDF_FONT_ITALIC
    return styles


def _pdf_safe_text(value) -> str:
    text = str(value)
    for source, target in PDF_TEXT_REPLACEMENTS.items():
        text = text.replace(source, target)
    return text


def _pdf_safe_table(data):
    return [[_pdf_safe_text(cell) for cell in row] for row in data]

# ============================================================
# ==================  INTERNAL MODULE IMPORTS  ================
# ============================================================

from core.constants import MATERIALS
from modules.xray.physics import (
    energy_grid,
    interaction_components,
)
from modules.xray.visualizer import (
    plot_interactions,
    compare_materials,
)

# ============================================================
# ====================  FLASK INITIALIZATION  =================
# ============================================================

app = Flask(__name__)


def _material_label(name: str) -> str:
    return name.replace("_", " ").capitalize() if name else "Material"


def _slugify_label(label: str) -> str:
    return (label or "material").strip().lower().replace(" ", "_")


def _resolve_xray_material(
    choice: str,
    z_raw: str = "",
    rho_raw: str = "",
    custom_name: str = "",
    *,
    fallback_choice: str = "water",
    fallback_label: str = "Custom Material",
):
    choice = (choice or fallback_choice).strip()

    if choice == "custom":
        if not z_raw:
            raise ValueError("Please enter a valid atomic number for the custom material.")
        try:
            z_val = float(z_raw)
        except ValueError as exc:
            raise ValueError("Atomic number must be numeric.") from exc
        if z_val <= 0 or z_val > 118:
            raise ValueError("Atomic number must be between 1 and 118.")

        try:
            rho_val = float(rho_raw) if rho_raw else 1.0
        except ValueError as exc:
            raise ValueError("Density must be numeric.") from exc
        if rho_val <= 0:
            raise ValueError("Density must be positive.")

        label = (custom_name or fallback_label).strip() or fallback_label
        return {
            "choice": "custom",
            "label": label,
            "Z": z_val,
            "rho": rho_val,
            "E_K": 0.0126 * (z_val ** 2),
            "E_L": 0.0016 * (z_val ** 2),
            "is_custom": True,
        }

    data = MATERIALS.get(choice) or MATERIALS.get(fallback_choice, MATERIALS["water"])
    resolved_choice = choice if choice in MATERIALS else fallback_choice
    return {
        "choice": resolved_choice,
        "label": _material_label(resolved_choice),
        "Z": data.get("Z", 7.4),
        "rho": data.get("rho", 1.0) or 1.0,
        "E_K": data.get("E_K", 1.0) or 1.0,
        "E_L": data.get("E_L", 0.1) or 0.1,
        "is_custom": False,
    }


def _parse_xray_request(form, default_material: str = "bone"):
    material_choice = (form.get("material", default_material) or default_material).strip()
    material2_choice = (form.get("material2", "") or "").strip()
    z1_input = (form.get("z1", "") or "").strip()
    z2_input = (form.get("z2", "") or "").strip()
    name1 = (form.get("name1", "") or "").strip()
    name2 = (form.get("name2", "") or "").strip()
    rho1_input = (form.get("rho1", "") or "").strip()
    rho2_input = (form.get("rho2", "") or "").strip()

    try:
        emin = float(form.get("emin", 20))
        emax = float(form.get("emax", 120))
    except ValueError as exc:
        raise ValueError("Energy inputs must be valid numbers.") from exc

    if emin <= 0 or emax <= emin:
        raise ValueError("Invalid energy range.")

    material1 = _resolve_xray_material(
        material_choice,
        z_raw=z1_input,
        rho_raw=rho1_input,
        custom_name=name1,
        fallback_choice=default_material,
        fallback_label="Custom Material 1",
    )
    material2 = None
    if material2_choice:
        material2 = _resolve_xray_material(
            material2_choice,
            z_raw=z2_input,
            rho_raw=rho2_input,
            custom_name=name2,
            fallback_choice=default_material,
            fallback_label="Custom Material 2",
        )

    return {
        "material_choice": material_choice,
        "material2_choice": material2_choice,
        "material1": material1,
        "material2": material2,
        "emin": emin,
        "emax": emax,
        "show_photo": "show_photo" in form,
        "show_compton": "show_compton" in form,
        "show_rayleigh": "show_rayleigh" in form,
        "z1_input": z1_input,
        "z2_input": z2_input,
        "name1": name1,
        "name2": name2,
        "rho1_input": rho1_input,
        "rho2_input": rho2_input,
    }


def _build_xray_dataframe(
    E,
    material1,
    material2=None,
    *,
    show_photo=True,
    show_compton=True,
    show_rayleigh=True,
):
    rows = {"Energy (keV)": E}

    def add_material_columns(material, prefix=""):
        components = interaction_components(
            material["Z"],
            E,
            material["E_K"],
            material["E_L"],
            material["rho"],
        )
        if show_photo:
            rows[f"{prefix}Photoelectric"] = components["Photoelectric"]
        if show_compton:
            rows[f"{prefix}Compton"] = components["Compton"]
        if show_rayleigh:
            rows[f"{prefix}Rayleigh"] = components["Rayleigh"]

    if material2:
        add_material_columns(material1, f"{material1['label']} — ")
        add_material_columns(material2, f"{material2['label']} — ")
    else:
        add_material_columns(material1)

    return pd.DataFrame(rows)


def _xray_dominant_component(material, energy_keV: float) -> str:
    sample_energy = np.array([max(float(energy_keV), 1e-6)])
    components = interaction_components(
        material["Z"],
        sample_energy,
        material["E_K"],
        material["E_L"],
        material["rho"],
    )
    return max(components, key=lambda key: float(components[key][0]))


def _summarize_xray_selection(material1, emin: float, emax: float, material2=None) -> str:
    low_dom = _xray_dominant_component(material1, emin)
    high_dom = _xray_dominant_component(material1, emax)
    summary = [f"For {material1['label']}, {low_dom.lower()} is the dominant component near {emin:g} keV."]
    if high_dom == low_dom:
        summary.append(f"It remains dominant up to {emax:g} keV within the selected range.")
    else:
        summary.append(f"By {emax:g} keV, the balance shifts and {high_dom.lower()} becomes dominant.")
    if material1["rho"] > 1:
        summary.append("Because the plot uses absolute attenuation proxies, increasing density scales all component magnitudes upward.")
    if material2:
        summary.append(
            f"The comparison uses one shared vertical scale for {material1['label']} and {material2['label']}, preserving absolute differences."
        )
    return " ".join(summary)


def _make_xray_figure(
    E,
    material1,
    material2=None,
    *,
    show_photo=True,
    show_compton=True,
    show_rayleigh=True,
):
    if material2:
        title = f"{material1['label']} vs {material2['label']}"
        fig, ax = compare_materials(
            material1["Z"],
            material2["Z"],
            E,
            material1["label"],
            material2["label"],
            material1["E_K"],
            material1["E_L"],
            material1["rho"],
            material2["E_K"],
            material2["E_L"],
            material2["rho"],
            show_rayleigh=show_rayleigh,
        )
        return fig, ax, title

    title = f"{material1['label']} — X-ray Interactions"
    fig, ax = plot_interactions(
        material1["Z"],
        E,
        title=title,
        E_K=material1["E_K"],
        E_L=material1["E_L"],
        rho=material1["rho"],
        show_photo=show_photo,
        show_compton=show_compton,
        show_rayleigh=show_rayleigh,
    )
    return fig, ax, title

# ============================================================
# ======================  ROUTES: X-RAY  ======================
# ============================================================

@app.route("/")
def home():
    """Main landing page."""
    return render_template("index.html")


@app.route("/xray", methods=["GET", "POST"])
def xray():
    """
    X-ray Interaction Visualizer.
    Displays photoelectric, Compton, and Rayleigh effects
    for selected or custom materials across an energy range.
    """
    materials = list(MATERIALS.keys())
    plot_path = None
    material = "bone"
    material2 = ""
    material_label1 = _material_label(material)
    material_label2 = ""
    emin, emax = 20, 120
    show_photo, show_compton, show_rayleigh = True, True, True
    selected_Z = None
    selected_Z2 = None
    scale = "logarithmic y-axis"
    z1_input = z2_input = name1 = name2 = rho1_input = rho2_input = ""
    rho1 = rho2 = None

    if request.method == "POST":
        try:
            parsed = _parse_xray_request(request.form, default_material="bone")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        material = parsed["material_choice"]
        material2 = parsed["material2_choice"]
        material1 = parsed["material1"]
        material2_data = parsed["material2"]
        emin = parsed["emin"]
        emax = parsed["emax"]
        show_photo = parsed["show_photo"]
        show_compton = parsed["show_compton"]
        show_rayleigh = parsed["show_rayleigh"]
        z1_input = parsed["z1_input"]
        z2_input = parsed["z2_input"]
        name1 = parsed["name1"]
        name2 = parsed["name2"]
        rho1_input = parsed["rho1_input"]
        rho2_input = parsed["rho2_input"]

        material_label1 = material1["label"]
        material_label2 = material2_data["label"] if material2_data else ""
        selected_Z = material1["Z"]
        selected_Z2 = material2_data["Z"] if material2_data else None
        rho1 = material1["rho"]
        rho2 = material2_data["rho"] if material2_data else None

        E = energy_grid(emin, emax)
        fig, ax, title = _make_xray_figure(
            E,
            material1,
            material2_data,
            show_photo=show_photo,
            show_compton=show_compton,
            show_rayleigh=show_rayleigh,
        )

        os.makedirs("static/plots", exist_ok=True)
        plot_path = f"static/plots/xray_{int(time.time() * 1000)}.png"
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        if request.headers.get("X-Requested-With", "").lower() == "xmlhttprequest":
            return render_template(
                "_xray_result.html",
                plot_path=plot_path,
                material_label1=material_label1,
                material_label2=material_label2,
                selected_Z=selected_Z,
                selected_Z2=selected_Z2,
                z1=z1_input,
                z2=z2_input,
                name1=name1,
                name2=name2,
                emin=emin,
                emax=emax,
                show_rayleigh=show_rayleigh,
                scale=scale,
                rho1=rho1,
                rho2=rho2,
            )

    return render_template(
        "xray.html",
        materials=materials,
        plot_path=plot_path,
        selected_material=material,
        selected_material2=material2,
        material_label1=material_label1,
        material_label2=material_label2,
        selected_Z=selected_Z,
        selected_Z2=selected_Z2,
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
        rho1=rho1_input,
        rho2=rho2_input,
    )
# ============================================================
# ================  X-RAY REPORT (PDF GENERATOR)  =============
# ============================================================

@app.route("/xray/report", methods=["POST"])
def xray_report():
    """
    Generate a professional PDF report for selected X-ray materials.
    Includes parameters, plot, interaction data, and a brief analysis.
    """
    try:
        parsed = _parse_xray_request(request.form, default_material="bone")
        material1 = parsed["material1"]
        material2 = parsed["material2"]
        emin = parsed["emin"]
        emax = parsed["emax"]
        show_photo = parsed["show_photo"]
        show_compton = parsed["show_compton"]
        show_rayleigh = parsed["show_rayleigh"]

        E = energy_grid(emin, emax)
        df = _build_xray_dataframe(
            E,
            material1,
            material2,
            show_photo=show_photo,
            show_compton=show_compton,
            show_rayleigh=show_rayleigh,
        )
        summary_text = _summarize_xray_selection(material1, emin, emax, material2)

        fig, ax, title = _make_xray_figure(
            E,
            material1,
            material2,
            show_photo=show_photo,
            show_compton=show_compton,
            show_rayleigh=show_rayleigh,
        )
        plot_buffer = io.BytesIO()
        fig.savefig(plot_buffer, format="png", dpi=150, bbox_inches="tight")
        plot_buffer.seek(0)
        plt.close(fig)

        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        story = []
        # --- Logo section ---
        logo_path = os.path.join("static", "logo.png")  
        if os.path.exists(logo_path):
            story.append(Image(logo_path, width=70, height=70))
            story[-1].hAlign = 'CENTER'
            story.append(Spacer(1, 0.2 * inch))

        styles = _create_pdf_styles()
        styles.add(ParagraphStyle(name="Heading", fontName=PDF_FONT_BOLD, fontSize=16,
                                  leading=22, textColor=colors.darkblue, spaceAfter=12))
        styles.add(ParagraphStyle(name="NormalBold", fontName=PDF_FONT_BOLD, fontSize=11,
                                  leading=14, textColor=colors.black, spaceAfter=6))
        styles.add(ParagraphStyle(name="Warning", fontName=PDF_FONT_BOLD, fontSize=9,
                                  leading=13, textColor=colors.red, spaceAfter=8))

        story.append(Paragraph(_pdf_safe_text("X-ray Interaction Analysis Report"), styles["Heading"]))
        story.append(Paragraph(_pdf_safe_text(f"Generated on: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}"), styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        table_data = [["Parameter", "Value"],
                      ["Primary Material", material1["label"]],
                      ["Atomic Number (Z₁)", f"{material1['Z']:.2f}"],
                      ["Density (ρ₁, g/cm³)", f"{material1['rho']:.3f}"]]

        if material2:
            table_data += [["Comparison Material", material2["label"]]]
            table_data += [["Atomic Number (Z₂)", f"{material2['Z']:.2f}"],
                           ["Density (ρ₂, g/cm³)", f"{material2['rho']:.3f}"]]

        table_data += [["Energy Range (keV)", f"{emin} – {emax}"],
                       ["Included Interactions",
                        ", ".join([i for i, s in [("Photoelectric", show_photo),
                                                  ("Compton", show_compton),
                                                  ("Rayleigh", show_rayleigh)] if s])]]

        table = Table(_pdf_safe_table(table_data), colWidths=[2.5 * inch, 3.5 * inch])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), PDF_FONT),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph(_pdf_safe_text("Figure 1. Interaction Components"), styles["NormalBold"]))
        story.append(Image(plot_buffer, width=5.5 * inch, height=3.5 * inch))
        story.append(Spacer(1, 0.2 * inch))

        story.append(PageBreak())
        story.append(Paragraph(_pdf_safe_text("Scientific Analysis"), styles["Heading"]))
        story.append(Paragraph(_pdf_safe_text(summary_text), styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph(_pdf_safe_text("Sample Data (First 5 rows)"), styles["NormalBold"]))
        formatted_data = [[_pdf_safe_text(col) for col in df.columns.tolist()]]
        for row in df.head(5).itertuples(index=False):
            formatted_data.append([_pdf_safe_text(f"{v:.3g}" if isinstance(v, (int, float)) else str(v)) for v in row])
        t = Table(formatted_data, colWidths=[1.6 * inch] + [1.1 * inch] * (len(df.columns) - 1))
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph(_pdf_safe_text("WARNING"), styles["Heading"]))
        story.append(Paragraph(
            _pdf_safe_text(
                "This simulation is for educational and research purposes only. "
                "Not intended for clinical or diagnostic use."
            ),
            styles["Warning"]
        ))

        story.append(Paragraph(_pdf_safe_text("References"), styles["Heading"]))
        story.append(Paragraph(
            _pdf_safe_text(
                "1. Hubbell & Seltzer, NIST (1995). X-ray mass attenuation coefficients.<br/>"
                "2. Attix, F.H. (1986). Introduction to Radiological Physics.<br/>"
                "3. Johns & Cunningham (1983). The Physics of Radiology."
            ),
            styles["Normal"]
        ))

        # --- Unified Disclaimer & Footer ---
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph(_pdf_safe_text("DISCLAIMER"), styles["Heading"]))
        story.append(Paragraph(
            _pdf_safe_text(
                "This report is generated for educational and research purposes only. "
                "It must not be used for clinical or diagnostic decision-making."
            ),
            styles["Warning"]
        ))
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph(
            _pdf_safe_text("Generated by: Medical Radiation Visualizer © 2025 — Hassan Almoosa"),
            styles["Normal"]
        ))

        doc.build(story)
        pdf_buffer.seek(0)

        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"{_slugify_label(material1['label'])}_xray_report.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500


# ============================================================
# ====================  X-RAY EXCEL EXPORT  ==================
# ============================================================

@app.route("/xray/download", methods=["POST"])
def download_xray_data():
    """Export calculated X-ray interaction data to Excel."""
    try:
        parsed = _parse_xray_request(request.form, default_material="bone")
        material1 = parsed["material1"]
        material2 = parsed["material2"]
        E = energy_grid(parsed["emin"], parsed["emax"])
        df = _build_xray_dataframe(
            E,
            material1,
            material2,
            show_photo=parsed["show_photo"],
            show_compton=parsed["show_compton"],
            show_rayleigh=parsed["show_rayleigh"],
        )

        output = io.BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name=f"{_slugify_label(material1['label'])}_xray_data.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate Excel: {str(e)}"}), 500

# ============================================================
# ====================  ROUTES: GAMMA-RAY  ===================
# ============================================================

def _gamma_dominant_component(data: dict, energy_mev: float) -> str:
    sample_energy = max(float(energy_mev), 1e-6)
    idx = int(np.argmin(np.abs(data["E_mev"] - sample_energy)))
    components = {
        "Photoelectric": float(data["photo_mu"][idx]),
        "Compton": float(data["compton_mu"][idx]),
        "Pair": float(data["pair_mu"][idx]),
    }
    return max(components, key=components.get)


def _summarize_gamma_selection(
    data1: dict,
    emin: float,
    emax: float,
    *,
    label1: str,
    label2: str | None = None,
) -> str:
    low_dom = _gamma_dominant_component(data1, emin)
    high_dom = _gamma_dominant_component(data1, emax)
    total_mu = np.asarray(data1["total_mu"], dtype=float)
    total_end = float(total_mu[-1])
    total_mid = float(total_mu[len(total_mu) // 2])

    summary = [f"For {label1}, {low_dom.lower()} is the dominant contribution near {emin:g} MeV."]
    if high_dom == low_dom:
        summary.append(f"It remains the largest component near {emax:g} MeV.")
    else:
        summary.append(f"Near {emax:g} MeV, the balance shifts toward {high_dom.lower()}.")

    if emax < 1.022:
        summary.append("Pair production stays below threshold throughout the selected range.")
    elif emin < 1.022:
        summary.append("Pair production turns on above 1.022 MeV and grows toward the high-energy end.")
    else:
        summary.append("Pair production is available across the full selected range and grows with energy, especially for high-Z materials.")

    if emax >= 1.022 and total_end > 1.05 * total_mid:
        summary.append("At the highest energies, pair production offsets part of the Compton falloff, so total attenuation bends upward.")
    elif emax >= 1.022 and total_end > 0.9 * total_mid:
        summary.append("At the highest energies, pair production partly compensates for the Compton decline, so total attenuation flattens.")
    else:
        summary.append("Across the selected range, the total attenuation still trends downward with energy.")

    if label2:
        summary.append(f"The comparison uses one shared attenuation scale for {label1} and {label2}.")
    return " ".join(summary)


@app.route("/gamma", methods=["GET", "POST"])
def gamma():
    """
    Gamma-ray Interaction Visualizer.
    Supports linear/log energy scale, single or dual-material plots,
    and custom Z with optional density override.
    """
    from modules.gamma.visualizer import plot_gamma
    from modules.gamma.physics import energy_grid
    from flask import jsonify

    materials = list(MATERIALS.keys())
    plot_path = None
    material, material2 = "lead", ""
    material_label1, material_label2 = _material_label(material), ""
    emin, emax = 0.1, 10
    z_input, z_input2 = "", ""
    name1, name2 = "", ""
    rho1, rho2 = 1.0, 1.0
    Z1, Z2 = 13.8, None
    scale = "linear"

    if request.method == "POST":
        material = request.form.get("material", "lead").strip()
        material2 = request.form.get("material2", "").strip()
        z_input = (request.form.get("z1", "") or "").strip()
        z_input2 = (request.form.get("z2", "") or "").strip()
        name1 = (request.form.get("name1", "") or "").strip()
        name2 = (request.form.get("name2", "") or "").strip()
        scale = request.form.get("scale", "linear")

        try:
            rho1 = float(request.form.get("rho1", 1.0) or 1.0)
            rho2 = float(request.form.get("rho2", 1.0) or 1.0)
        except ValueError:
            return jsonify({"error": "Density values must be numeric."}), 400

        try:
            emin = float(request.form.get("emin", 0.1))
            emax = float(request.form.get("emax", 10))
        except ValueError:
            return jsonify({"error": "Energy inputs must be numeric."}), 400
        if emin <= 0 or emax <= emin:
            return jsonify({"error": "Invalid energy range."}), 400

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
                return z_val, (name_field.strip() or "Custom Material")
            else:
                mat = MATERIALS.get(material_name, {})
                return mat.get("Z", 7.4), (material_name.capitalize() if material_name else "Material")

        try:
            Z1, material_label1 = get_Z(material, z_input, name1)
            if material2:
                Z2, material_label2 = get_Z(material2, z_input2, name2)
            else:
                material_label2 = ""
        except ValueError as e:
            return jsonify({"error": f"{str(e)}"}), 400

        E = energy_grid(emin, emax, points=300, scale=scale)
        title = (
            f"{material_label1} — Gamma-ray Interactions"
            if not material2
            else f"{material_label1} vs {material_label2} — Gamma-ray Interactions"
        )

        fig, ax = plot_gamma(
            Z1, E, title,
            rho1=rho1,
            Z2=Z2, rho2=(rho2 if material2 else None),
            material1=material_label1, material2=(material_label2 if material2 else None),
            show_mass_coeff=False,
            scale=scale,
        )

        os.makedirs("static/plots", exist_ok=True)
        plot_path = f"static/plots/gamma_{int(time.time() * 1000)}.png"
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        if request.headers.get("X-Requested-With", "").lower() == "xmlhttprequest":
            return render_template(
                "_gammaray_result.html",
                plot_path=plot_path,
                material_label1=material_label1,
                material_label2=material_label2,
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

    return render_template(
        "gamma.html",
        materials=materials,
        plot_path=plot_path,
        selected_material=material,
        selected_material2=(material2 if "material2" in locals() else None),
        material_label1=material_label1,
        material_label2=material_label2,
        z1=z_input,
        z2=(z_input2 if "z_input2" in locals() else None),
        emin=emin,
        emax=emax,
        name1=name1,
        name2=(name2 if "name2" in locals() else None),
        rho1=(rho1 if "rho1" in locals() else None),
        rho2=(rho2 if "rho2" in locals() else None),
        scale=scale,
    )


@app.route("/gamma/download", methods=["POST"])
def download_gamma_data():
    """
    Export Gamma-ray interaction data (Energy, Compton, Pair, Total) to Excel.
    Supports one or two materials. Energy in MeV.
    """
    try:
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

        output = io.BytesIO()
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


@app.route("/gamma/report", methods=["POST"])
def gamma_report():
    """
    Generate a Gamma-ray PDF report (parameters table, plot, and short analysis).
    """
    try:
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

        E = energy_grid(emin, emax, points=300, scale=scale)
        title = f"{label1} — Gamma-ray Interactions" if not label2 else f"{label1} vs {label2} — Gamma-ray Interactions"

        fig, ax = plot_gamma(
            Z1, E, title, rho1=rho1,
            Z2=Z2, rho2=(rho2 if Z2 is not None else None),
            material1=label1, material2=(label2 if Z2 is not None else None),
            show_mass_coeff=False,
            scale=scale,
        )

        os.makedirs("static/plots", exist_ok=True)
        plot_path = f"static/plots/{label1.lower()}_gamma_report.png"
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        styles = _create_pdf_styles()
        # Ensure consistent styles across all modules
        if "Heading" not in styles:
            styles.add(ParagraphStyle(name="Heading", fontName=PDF_FONT_BOLD, fontSize=16,
                                    leading=22, textColor=colors.darkblue, spaceAfter=12))
        if "Warning" not in styles:
            styles.add(ParagraphStyle(name="Warning", fontName=PDF_FONT_BOLD, fontSize=9,
                                    leading=13, textColor=colors.red, spaceAfter=8))

        styles.add(ParagraphStyle(name="H", fontName=PDF_FONT_BOLD, fontSize=16, leading=22,
                                  textColor=colors.darkblue, spaceAfter=12))
        styles.add(ParagraphStyle(name="Warn", fontName=PDF_FONT_BOLD, fontSize=9, leading=13,
                                  textColor=colors.red, spaceAfter=8))

        story = []
        # --- Logo section ---
        logo_path = os.path.join("static", "logo.png")  
        if os.path.exists(logo_path):
            story.append(Image(logo_path, width=70, height=70))
            story[-1].hAlign = 'CENTER'
            story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(_pdf_safe_text("Gamma-ray Interaction Analysis Report"), styles["H"]))
        story.append(Paragraph(_pdf_safe_text(f"Generated: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}"), styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

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
        tbl = Table(_pdf_safe_table(rows), colWidths=[2.7*inch, 3.3*inch])
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,-1), PDF_FONT),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.25 * inch))

        if os.path.exists(plot_path):
            story.append(Image(plot_path, width=5.6*inch, height=3.4*inch))
            story.append(Spacer(1, 0.2 * inch))

        data1 = gamma_interactions(Z1, rho1, E)
        summary = _summarize_gamma_selection(
            data1,
            emin,
            emax,
            label1=label1,
            label2=label2,
        )
        story.append(Paragraph(_pdf_safe_text(summary), styles["Normal"]))
        story.append(Spacer(1, 0.25 * inch))

        # --- Unified Disclaimer & Footer ---
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph(_pdf_safe_text("DISCLAIMER"), styles["Heading"]))
        story.append(Paragraph(
            _pdf_safe_text(
                "This report is generated for educational and research purposes only. "
                "It must not be used for clinical or diagnostic decision-making."
            ),
            styles["Warning"]
        ))
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph(
            _pdf_safe_text("Generated by: Medical Radiation Visualizer © 2025 — Hassan Almoosa"),
            styles["Normal"]
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
        return jsonify({"error": f"Failed to generate PDF: {str(e)}"}), 500


# ============================================================
# =====================  ROUTES: PROTON  =====================
# ============================================================

from modules.protons.visualizer import plot_proton_interaction
from modules.protons.physics import (
    bragg_curve, stopping_power_curve, range_vs_energy, lateral_sigma_curve, resolve_material_spec
)

PROTON_MODE_LABELS = {
    "bragg": "Bragg Peak",
    "stopping": "Stopping Power",
    "range": "Range-Energy",
    "lateral": "Lateral Scattering",
}


def _resolve_proton_material_from_params(params: dict):
    choice = (params.get("material", "water") or "water").strip()
    if choice == "custom":
        name = (params.get("name", "") or "").strip() or "Custom Material"
        z_raw = (params.get("z", "") or "").strip()
        rho_raw = (params.get("rho", "") or "").strip()
        if not z_raw:
            raise ValueError("Please enter an atomic number for the custom proton material.")
        if not rho_raw:
            raise ValueError("Please enter a density for the custom proton material.")
        try:
            z_val = float(z_raw)
            rho_val = float(rho_raw)
        except ValueError as exc:
            raise ValueError("Custom proton material values must be numeric.") from exc
        if z_val <= 0 or z_val > 118:
            raise ValueError("Atomic number must be between 1 and 118.")
        if rho_val <= 0:
            raise ValueError("Density must be positive.")
        return choice, resolve_material_spec({"name": name, "label": name, "Z": z_val, "rho": rho_val})

    if choice not in MATERIALS:
        choice = "water"
    return choice, resolve_material_spec(choice)


def _parse_proton_request(form) -> dict:
    params = form.to_dict() or {}
    params["mode"] = (params.get("mode", "bragg") or "bragg").strip().lower()

    numeric_defaults = {
        "E0": 150.0,
        "dx": 0.01,
        "emin": 10.0,
        "emax": 250.0,
        "npts": 120,
        "zmax": 25.0,
    }

    for key, default in numeric_defaults.items():
        raw = params.get(key, default)
        if raw in (None, ""):
            params[key] = default
            continue
        try:
            params[key] = float(raw)
        except ValueError as exc:
            raise ValueError(f"{key} must be numeric.") from exc

    params["npts"] = int(round(params["npts"]))
    if params["E0"] <= 0:
        raise ValueError("Initial proton energy must be positive.")
    if params["dx"] <= 0:
        raise ValueError("Step size must be positive.")
    if params["emin"] <= 0 or params["emax"] <= params["emin"]:
        raise ValueError("Energy range must satisfy 0 < emin < emax.")
    if params["npts"] < 20 or params["npts"] > 1000:
        raise ValueError("npts must be between 20 and 1000.")
    if params["zmax"] <= 0:
        raise ValueError("Maximum depth must be positive.")

    material_choice, material_spec = _resolve_proton_material_from_params(params)
    params["material"] = material_choice
    params["material_spec"] = material_spec
    params["material_label"] = material_spec["label"]
    return params


def _build_proton_dataframe(params: dict) -> pd.DataFrame:
    mode = params["mode"]
    material = params["material_spec"]
    if mode == "bragg":
        x, y, _ = bragg_curve(params["E0"], material, dx_cm=params["dx"])
        return pd.DataFrame({"Depth (cm)": x, "Relative Dose": y})
    if mode == "stopping":
        energies = np.linspace(params["emin"], params["emax"], params["npts"])
        x, y = stopping_power_curve(energies, material)
        return pd.DataFrame({"Energy (MeV)": x, "Mass Stopping Power (MeV·cm²/g)": y})
    if mode == "range":
        energies = np.linspace(params["emin"], params["emax"], params["npts"])
        x, y = range_vs_energy(energies, material)
        return pd.DataFrame({"Initial Energy (MeV)": x, "CSDA Range (cm)": y})
    if mode == "lateral":
        depths = np.linspace(0, params["zmax"], params["npts"])
        x, y = lateral_sigma_curve(depths, params["E0"], material)
        return pd.DataFrame({"Depth (cm)": x, "Lateral Spread σ (cm)": y})
    raise ValueError("Unknown mode selected")


def _proton_interpretation(mode: str) -> str:
    if mode == "bragg":
        return "The Bragg curve is derived from the same stopping-power model used in the range calculation, so the peak position and terminal range are internally consistent."
    if mode == "stopping":
        return "The stopping-power curve and Bragg simulation now share one Bethe-inspired material model, so high stopping power at low energy feeds directly into the distal peak."
    if mode == "range":
        return "The CSDA range is obtained by integrating the same stopping-power model shown elsewhere, so it increases monotonically and nonlinearly with initial energy rather than relying on a separate empirical rescaling."
    if mode == "lateral":
        return "Lateral spread is estimated with Highland scattering using the same resolved material density and effective radiation length used throughout the proton module."
    return "Results are generated from one consistent proton-material model."

@app.route("/proton")
def proton_page():
    """Render the Proton module page."""
    return render_template("proton.html", materials=list(MATERIALS.keys()))


@app.route("/proton/plot", methods=["POST"])
def plot_proton():
    """
    Generate Proton plot (Bragg, stopping power, range-energy, or lateral scattering)
    and return a partial HTML snippet to display the figure.
    """
    try:
        params = _parse_proton_request(request.form)
        fig, ax = plot_proton_interaction(params["mode"], params)
        os.makedirs("static/plots", exist_ok=True)
        plot_path = f"static/plots/proton_{int(time.time() * 1000)}.png"
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        return render_template(
            "_proton_result.html",
            plot_path=plot_path,
            material_label=params["material_label"],
            E0=params["E0"],
            mode_label=PROTON_MODE_LABELS.get(params["mode"], "Interaction"),
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/proton/download", methods=["POST"])
def download_proton():
    """Export Proton data as an Excel file."""
    try:
        params = _parse_proton_request(request.form)
        data = _build_proton_dataframe(params)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    mode = params["mode"]
    material = params["material_spec"]

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        data.to_excel(writer, index=False, sheet_name="proton_data")
        meta = pd.DataFrame(
            [
                ("Material", params["material_label"]),
                ("Atomic Number (Z)", material["Z"]),
                ("Density (g/cm³)", material["rho"]),
                ("Mode", PROTON_MODE_LABELS.get(mode, mode)),
                ("Initial Energy (MeV)", params["E0"]),
                ("Step Size (cm)", params["dx"]),
                ("Energy Min (MeV)", params["emin"]),
                ("Energy Max (MeV)", params["emax"]),
                ("Points", params["npts"]),
                ("Max Depth (cm)", params["zmax"]),
            ],
            columns=["Parameter", "Value"],
        )
        meta.to_excel(writer, index=False, sheet_name="parameters")
    buf.seek(0)

    filename = f"{_slugify_label(params['material_label'])}_proton_{mode}_{datetime.datetime.now():%Y%m%d_%H%M%S}.xlsx"
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route("/proton/report", methods=["POST"])
def report_proton():
    """
    Generate a Proton Interaction PDF report with figure, parameters,
    sample data, and a short scientific interpretation.
    """
    try:
        params = _parse_proton_request(request.form)
        mode = params["mode"]
        material = params["material_spec"]

        fig, ax = plot_proton_interaction(mode, params)
        os.makedirs("static/plots", exist_ok=True)
        plot_path = f"static/plots/proton_report_{int(time.time())}.png"
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        df = _build_proton_dataframe(params)

        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        story = []
        # --- Logo section ---
        logo_path = os.path.join("static", "logo.png")  
        if os.path.exists(logo_path):
            story.append(Image(logo_path, width=70, height=70))
            story[-1].hAlign = 'CENTER'
            story.append(Spacer(1, 0.2 * inch))
        styles = _create_pdf_styles()
        styles.add(ParagraphStyle(name="Heading", fontName=PDF_FONT_BOLD, fontSize=16, leading=22,
                                  textColor=colors.darkblue, spaceAfter=12))
        styles.add(ParagraphStyle(name="NormalBold", fontName=PDF_FONT_BOLD, fontSize=11, leading=14,
                                  textColor=colors.black, spaceAfter=6))
        styles.add(ParagraphStyle(name="Warning", fontName=PDF_FONT_BOLD, fontSize=9, leading=13,
                                  textColor=colors.red, spaceAfter=8))
        styles.add(ParagraphStyle(name="Scientific", fontName=PDF_FONT_ITALIC, fontSize=10, leading=14,
                                  textColor=colors.black, spaceAfter=6, italic=True))

        E0_val = params["E0"]
        mode_label = PROTON_MODE_LABELS.get(mode, "Interaction")
        story.append(Paragraph(_pdf_safe_text(f"Proton {mode_label} Report — {E0_val:.0f} MeV in {params['material_label']}"), styles["Heading"]))
        story.append(Paragraph(_pdf_safe_text(f"Generated on: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}"), styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        table_data = [
            ["Parameter", "Value"],
            ["Material", params["material_label"]],
            ["Atomic Number (Z)", f"{material.get('Z', 7.4):.2f}"],
            ["Density (ρ, g/cm³)", f"{material.get('rho', 1.0):.3f}"],
            ["Mode", mode_label],
            ["Initial Energy (MeV)", f"{E0_val:.2f}"],
        ]
        tbl = Table(_pdf_safe_table(table_data), colWidths=[2.7 * inch, 3.3 * inch])
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), PDF_FONT),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.3 * inch))

        if plot_path and os.path.exists(plot_path):
            story.append(Paragraph(_pdf_safe_text("Figure 1. Proton Interaction Curve"), styles["NormalBold"]))
            story.append(Image(plot_path, width=5.5 * inch, height=3.5 * inch))
            story.append(Spacer(1, 0.25 * inch))
            story.append(Paragraph(
                _pdf_safe_text(f"<i>Simulated proton interaction response in {params['material_label']} (E0 = {E0_val} MeV).</i>"),
                styles["Scientific"]
            ))
            story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph(_pdf_safe_text("Sample Data (First 5 Rows)"), styles["NormalBold"]))
        formatted_data = [[_pdf_safe_text(col) for col in df.columns.tolist()]]
        for row in df.head(5).itertuples(index=False):
            formatted_data.append([_pdf_safe_text(f"{v:.3g}" if isinstance(v, (int, float)) else str(v)) for v in row])
        t = Table(formatted_data, colWidths=[1.6 * inch] + [1.2 * inch] * (len(df.columns) - 1))
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("Scientific Interpretation", styles["Heading"]))
        interp = _proton_interpretation(mode)
        if False and mode == "bragg":
            interp = "Bragg peak is observed near the stopping depth—typical for therapeutic proton beams."
        elif mode == "stopping":
            interp = "Stopping power decreases gradually with increasing energy, consistent with Bethe–Bloch predictions."
        elif mode == "range":
            interp = "Range grows approximately linearly with initial energy below 200 MeV; deviations occur at higher energies."
        elif mode == "lateral":
            interp = "Lateral scattering increases slowly with depth due to multiple Coulomb scattering."
        else:
            interp = "Results are consistent with theoretical proton–matter interactions."
        story.append(Paragraph(interp, styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        # --- Unified Disclaimer & Footer ---
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph("DISCLAIMER", styles["Heading"]))
        story.append(Paragraph(
            "This report is generated for educational and research purposes only. "
            "It must not be used for clinical or diagnostic decision-making.",
            styles["Warning"]
        ))
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph(
            _pdf_safe_text("Generated by: Medical Radiation Visualizer © 2025 — Hassan Almoosa"),
            styles["Normal"]
        ))
        doc.build(story)
        pdf_buffer.seek(0)

        filename = f"{_slugify_label(params['material_label'])}_proton_report_{int(time.time())}.pdf"
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


# ============================================================
# ==============  ROUTES: ELECTRON & SHIELDING  ==============
# ============================================================

@app.route("/electron")
def electron():
    """Render the placeholder Electrons page."""
    return render_template("electron.html")


@app.route("/shielding")
def shielding():
    """Render the placeholder Shielding page."""
    return render_template("shielding.html")


# ============================================================
# =======================  MAIN ENTRYPOINT  ==================
# ============================================================

if __name__ == "__main__":
    # Note: debug=True is for development only.
    app.run(debug=True, host="0.0.0.0", port=5000)
