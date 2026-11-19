(function () {
    const STORAGE_KEY = "sgs-theme";

    function temaPreferido() {
        const guardado = localStorage.getItem(STORAGE_KEY);
        if (guardado === "dark" || guardado === "light") return guardado;
        return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }

    function aplicarTema(tema) {
        const modo = tema === "dark" ? "dark" : "light";
        document.documentElement.setAttribute("data-theme", modo);
        localStorage.setItem(STORAGE_KEY, modo);
        const btn = document.getElementById("theme-toggle");
        if (btn) {
            const icono = btn.querySelector("i");
            const texto = btn.querySelector(".theme-label");
            if (icono) {
                icono.className = modo === "dark" ? "fas fa-sun" : "fas fa-moon";
            }
            if (texto) {
                texto.textContent = modo === "dark" ? "Claro" : "Oscuro";
            }
            btn.setAttribute("aria-label", modo === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro");
            btn.title = modo === "dark" ? "Modo claro" : "Modo oscuro";
        }
        window.dispatchEvent(new CustomEvent("sgs-theme-change", { detail: { theme: modo } }));
    }

    function alternarTema() {
        const actual = document.documentElement.getAttribute("data-theme") || "light";
        aplicarTema(actual === "dark" ? "light" : "dark");
    }

    window.SGSTheme = { aplicarTema, alternarTema, temaPreferido };

    aplicarTema(temaPreferido());

    document.addEventListener("DOMContentLoaded", () => {
        aplicarTema(temaPreferido());
        const btn = document.getElementById("theme-toggle");
        if (btn) btn.addEventListener("click", alternarTema);
    });
})();
