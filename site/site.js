/* Local AI Lab · © 2026 Serhii Khomenko · https://homensai.com/ */
/* Documentation site: theme button, "Top" button and author footer of HomenS.AI Style in the language of the page,
   the "Documents" sheet of the phone navigation and closing of open menus. Needs style/js/brand.js, ui.js, brand-ui.js. */
(function () {
  var S = window.HomenS;
  if (!S || !S.ui) return;
  var lang = (document.documentElement.lang || "en").slice(0, 2);
  var T = {
    ru: { toLight: "Светлая тема", toDark: "Тёмная тема", top: "Наверх" },
    en: { toLight: "Light theme", toDark: "Dark theme", top: "Top" },
    de: { toLight: "Helles Design", toDark: "Dunkles Design", top: "Nach oben" }
  }[lang] || { toLight: "Light theme", toDark: "Dark theme", top: "Top" };
  var tools = document.getElementById("tools");
  if (tools) {
    var li = document.createElement("li");
    li.appendChild(S.ui.themeButton(T));
    tools.appendChild(li);
  }
  S.ui.initToTop(T.top);
  var footer = document.getElementById("footer");
  if (footer && S.brandUi) S.brandUi.renderFooter(footer, lang);

  var toggle = document.querySelector(".more-toggle");
  var sheet = document.getElementById("more-sheet");
  function setSheet(open) {
    if (!toggle || !sheet) return;
    sheet.hidden = !open;
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  }
  if (toggle) toggle.addEventListener("click", function () { setSheet(sheet.hidden); });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    setSheet(false);
    Array.prototype.forEach.call(document.querySelectorAll("details.nav-group[open]"), function (d) { d.open = false; });
  });
  document.addEventListener("click", function (e) {
    Array.prototype.forEach.call(document.querySelectorAll("details.nav-group[open]"), function (d) {
      if (!d.contains(e.target)) d.open = false;
    });
    if (sheet && !sheet.hidden && !sheet.contains(e.target) && !toggle.contains(e.target)) setSheet(false);
  });
})();
