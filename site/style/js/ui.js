// HomenS.AI Style · © 2026 Serhii Khomenko · https://homensai.com/ · https://github.com/HomenSAI · https://www.linkedin.com/in/serhii-khomenko-homensai/
// Малые помощники интерфейса без зависимостей: значки (контурные SVG), переключатель темы, кнопка «Наверх».
// Всё — через DOM API, без innerHTML с данными и без inline-стилей: работает при строгой CSP.
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var ICONS = {
    home: ["M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1z"],
    book: ["M5 4h10a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z", "M5 17a3 3 0 0 1 3-3h10"],
    calendar: ["M4 6h16v14H4z", "M8 3v4M16 3v4M4 11h16"],
    chart: ["M4 20V10M10 20V4M16 20v-7M22 20H2"],
    more: ["M6 12h.01M12 12h.01M18 12h.01"],
    help: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z", "M9.6 9.4a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1.1.9-1.1 1.7M12 17h.01"],
    user: ["M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z", "M4 20a8 8 0 0 1 16 0"],
    moon: ["M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"],
    sun: ["M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z", "M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"],
    up: ["M12 19V6M6 11l6-6 6 6"]
  };

  function icon(name) {
    var svg = document.createElementNS(NS, "svg");
    var attrs = { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": "1.8", "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true", focusable: "false" };
    Object.keys(attrs).forEach(function (k) { svg.setAttribute(k, attrs[k]); });
    (ICONS[name] || []).forEach(function (d) {
      var path = document.createElementNS(NS, "path");
      path.setAttribute("d", d);
      svg.appendChild(path);
    });
    return svg;
  }

  function currentTheme() {
    var set = document.documentElement.getAttribute("data-theme");
    if (set === "light" || set === "dark") return set;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function toggleTheme() {
    var next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("homensai.theme", next); } catch (e) { /* без хранилища тема действует до перезагрузки */ }
    return next;
  }

  // Кнопка-переключатель темы. labels: { toLight, toDark } — подписи для экранных дикторов.
  function themeButton(labels) {
    labels = labels || { toLight: "Light theme", toDark: "Dark theme" };
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "nav-btn theme-toggle";
    function paint() {
      var dark = currentTheme() === "dark";
      var text = dark ? labels.toLight : labels.toDark;
      btn.setAttribute("aria-label", text);
      btn.title = text;
      btn.replaceChildren(icon(dark ? "sun" : "moon"));
    }
    btn.addEventListener("click", function () { toggleTheme(); paint(); });
    paint();
    return btn;
  }

  // Кнопка «Наверх»: справа внизу, появляется после прокрутки на 300 px. Включается сама на каждой странице с js/ui.js
  // (подпись — по <html lang>: ru «Наверх», en «Back to top», de «Nach oben»); отключить — <body data-no-to-top>.
  var TO_TOP = { ru: "Наверх", en: "Back to top", de: "Nach oben" };
  function initToTop(label) {
    if (document.getElementById("to-top")) return;
    label = label || TO_TOP[(document.documentElement.lang || "ru").slice(0, 2)] || TO_TOP.en;
    var b = document.createElement("button");
    b.id = "to-top";
    b.type = "button";
    b.className = "to-top";
    b.hidden = true;
    b.setAttribute("aria-label", label);
    b.title = label;
    b.appendChild(icon("up"));
    b.addEventListener("click", function () {
      var calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      window.scrollTo({ top: 0, behavior: calm ? "auto" : "smooth" });
    });
    document.body.appendChild(b);
    var sync = function () { b.hidden = window.scrollY < 300; };
    window.addEventListener("scroll", sync, { passive: true });
    sync();   // страница открыта уже прокрученной (перезагрузка, ссылка на раздел) — кнопка видна сразу
  }

  function autoToTop() { if (document.body && !document.body.hasAttribute("data-no-to-top")) initToTop(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", autoToTop);
  else autoToTop();

  window.HomenS = window.HomenS || {};
  window.HomenS.ui = { icon: icon, currentTheme: currentTheme, toggleTheme: toggleTheme, themeButton: themeButton, initToTop: initToTop };
})();
