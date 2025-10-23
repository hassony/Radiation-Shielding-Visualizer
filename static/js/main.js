/* ============================================================
   ⚛️ Medical Radiation Visualizer — Interactive AJAX Handler
   Author: HASSAN ALMOOSA
   Description:
   Handles dynamic form submissions and interactive controls
   for X-ray, Gamma-ray, and other modules without page reload.
============================================================ */

document.addEventListener("DOMContentLoaded", () => {
  const forms = [
    { formId: "xrayForm", selectIds: ["material", "material2"], customIds: ["custom1", "custom2"], unit: "keV" },
    { formId: "gammaForm", selectIds: ["material", "material2"], customIds: ["custom1", "custom2"], unit: "MeV" },
  ];

  forms.forEach(cfg => {
    const form = document.getElementById(cfg.formId);
    const rightPanel = document.querySelector(".right-panel");
    if (!form) return;

    // 🎛️ التحكم في إظهار حقول custom
    cfg.selectIds.forEach((selectId, idx) => {
      const select = document.getElementById(selectId);
      const customDiv = document.getElementById(cfg.customIds[idx]);
      if (!select || !customDiv) return;

      const toggleCustom = () => {
        const isCustom = select.value === "custom";
        customDiv.style.display = isCustom ? "grid" : "none";
        customDiv.querySelectorAll("input").forEach(input => {
          input.disabled = !isCustom;
        });
      };

      toggleCustom();
      select.addEventListener("change", toggleCustom);
    });

    // 📈 إرسال النموذج عبر AJAX
    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const eminInput = form.querySelector("#emin");
      const emaxInput = form.querySelector("#emax");
      const emin = parseFloat(eminInput?.value || 0);
      const emax = parseFloat(emaxInput?.value || 0);

      // 🌟 التحقق من صحة الكثافة للمادة المخصصة (X-ray وGamma)
      const checkDensity = (id) => {
        const input = form.querySelector(`#${id}`);
        if (input && !input.disabled) {
          const val = parseFloat(input.value || 0);
          if (isNaN(val) || val <= 0) {
            alert(`⚠️ Density (${id}) must be a positive number.`);
            throw new Error("Invalid density");
          }
        }
      };

      try {
        checkDensity("rho1");
        checkDensity("rho2");
      } catch {
        return;
      }

      // ⚠️ تحقق من نطاق الطاقة
      if (emax <= emin) {
        alert(`⚠️ Maximum energy must be greater than minimum energy (${cfg.unit}).`);
        return;
      }

      // 🌀 شاشة التحميل
      rightPanel.innerHTML = `
        <div class="result" style="text-align:center; padding:40px;">
          <div class="spinner" style="
            width: 40px; height: 40px; border: 4px solid #ccc;
            border-top: 4px solid #5e72e4; border-radius: 50%;
            animation: spin 0.8s linear infinite; margin: 0 auto;
          "></div>
          <p style="margin-top:15px;">Generating ${cfg.unit} plot... Please wait.</p>
        </div>
      `;

      const formData = new FormData(form);

      try {
        const response = await fetch(window.location.pathname, {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "XMLHttpRequest" }
        });

        if (!response.ok) {
          const ct = response.headers.get("content-type") || "";
          if (ct.includes("application/json")) {
            const data = await response.json();
            alert(data.error || "❌ Request failed.");
          } else {
            alert("❌ Request failed.");
          }
          return;
        }

        // 📄 تحليل الرد HTML
        const html = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, "text/html");
        const newResult = doc.querySelector(".result");

        if (newResult) {
          // 🖼️ تحديث الصورة ومنع الكاش
          const img = newResult.querySelector("img");
          if (img) {
            const cleanSrc = img.getAttribute("src");
            img.src = cleanSrc.startsWith("/static")
              ? `${window.location.origin}${cleanSrc}?v=${Math.floor(Math.random() * 1000000)}`
              : `${window.location.origin}/${cleanSrc}?v=${Math.floor(Math.random() * 1000000)}`;
          }

          // 🧱 عرض النتيجة الجديدة
          rightPanel.innerHTML = "";
          rightPanel.appendChild(newResult);
        } else {
          rightPanel.innerHTML = `
            <div class="result" style="text-align:center;">
              <p>⚠️ No results returned. Please check your input.</p>
            </div>`;
        }
      } catch (err) {
        console.error("Error updating plot:", err);
        rightPanel.innerHTML = `
          <div class="result" style="text-align:center;">
            <p>❌ Failed to generate plot. Please try again.</p>
          </div>`;
      }
    });
  });
});

/* 🔁 CSS Animation for Spinner */
const style = document.createElement("style");
style.textContent = `
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}`;
document.head.appendChild(style);
console.log("✅ main.js loaded successfully");

// ============== Gamma: Excel / PDF download (append-only) ==============
(function () {
  const gammaForm = document.getElementById("gammaForm");
  const btnXlsx   = document.getElementById("btnGammaExcel");
  const btnPdf    = document.getElementById("btnGammaPDF");

  if (!gammaForm || !btnXlsx || !btnPdf) return;

  async function postAndDownload(url) {
    const fd = new FormData(gammaForm);
    const resp = await fetch(url, {
      method: "POST",
      body: fd,
      headers: { "X-Requested-With": "XMLHttpRequest" }
    });
    if (!resp.ok) {
      const ct = resp.headers.get("content-type") || "";
      if (ct.includes("application/json")) {
        const j = await resp.json();
        alert(j.error || "Request failed.");
      } else {
        alert("Request failed.");
      }
      return;
    }
    const blob = await resp.blob();
    let filename = "gamma_data";
    const cd = resp.headers.get("Content-Disposition") || resp.headers.get("content-disposition");
    if (cd) {
      const m = cd.match(/filename\*?=(?:UTF-8'')?("?)([^";]+)\1/i);
      if (m && m[2]) filename = decodeURIComponent(m[2]);
    }
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  btnXlsx.addEventListener("click", () => postAndDownload("/gamma/download"));
  btnPdf.addEventListener("click", () => postAndDownload("/gamma/report"));
})();

// ============================================================
// 💥 Proton Interaction Visualizer — Stable AJAX Handler
// ============================================================

(function () {
  if (window.protonLogicLoaded) return;
  window.protonLogicLoaded = true;

  const protonForm = document.getElementById("protonForm");
  if (!protonForm) return;
  const rightPanel = document.querySelector(".right-panel");

  // Submit
  protonForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(protonForm);
    const response = await fetch("/proton/plot", {
      method: "POST",
      body: formData,
      headers: { "X-Requested-With": "XMLHttpRequest" }
    });
    if (!response.ok) return alert("Failed to generate plot.");
    const html = await response.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const newResult = doc.querySelector(".result");
    rightPanel.innerHTML = "";
    rightPanel.appendChild(newResult);

  });

  // Excel
  const btnExcel = document.getElementById("btnProtonExcel");
  if (btnExcel) {
    btnExcel.addEventListener("click", async () => {
      const formData = new FormData(protonForm);
      const res = await fetch("/proton/download", { method: "POST", body: formData });
      if (!res.ok) return alert("Excel download failed.");
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "proton_data.xlsx";
      a.click();
    });
  }

  // PDF
  const btnPDF = document.getElementById("btnProtonPDF");
  if (btnPDF) {
    btnPDF.addEventListener("click", async () => {
      const formData = new FormData(protonForm);
      const res = await fetch("/proton/report", { method: "POST", body: formData });
      if (!res.ok) return alert("Report generation failed.");
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "proton_report.pdf";
      a.click();
    });
  }
})();
