/* Local AI Lab · © 2026 Serhii Khomenko · https://homensai.com/ */
/* Page shell of HomenS.AI Style for the console and the report: theme button, "to top" button and the author footer,
   in the interface language chosen in i18n.js. Needs style/js/brand.js, ui.js and brand-ui.js. */
(() => {
  const S = window.HomenS;
  if (!S || !S.ui) return;
  const lang = (window.i18n && window.i18n.lang()) || "ru";
  const T = {
    ru: {toLight: "Светлая тема", toDark: "Тёмная тема", top: "Наверх"},
    en: {toLight: "Light theme", toDark: "Dark theme", top: "Top"},
    de: {toLight: "Helles Design", toDark: "Dunkles Design", top: "Nach oben"},
  }[lang] || {toLight: "Light theme", toDark: "Dark theme", top: "Top"};
  const tools = document.getElementById("tools");
  if (tools) {
    const li = document.createElement("li");
    li.setAttribute("data-no-i18n", "");
    li.appendChild(S.ui.themeButton(T));
    tools.appendChild(li);
  }
  S.ui.initToTop(T.top);
  const footer = document.getElementById("brandFooter");
  if (footer && S.brandUi) S.brandUi.renderFooter(footer, lang);
})();
