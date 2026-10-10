// HomenS.AI Style · © 2026 Serhii Khomenko · https://homensai.com/ · https://github.com/HomenSAI · https://www.linkedin.com/in/serhii-khomenko-homensai/
// Общий запуск каждой страницы сайта по SITE_RULES.md: кнопка темы в шапке, подвал, ссылки автора, блок «Контакт», робот.
// Подключать последним из файлов ядра (после brand.js, ui.js, brand-ui.js и, если есть, robot.js, motion.js, logo-word.js).
// Язык подписей — по <html lang>. Кнопка «Наверх» включается сама в js/ui.js. Без inline-кода: работает при строгой CSP.
(function () {
  "use strict";
  var H = window.HomenS;
  if (!H || !H.ui || !H.brandUi) throw new Error("site-init.js: подключите js/brand.js, js/ui.js и js/brand-ui.js раньше");
  var lang = (document.documentElement.lang || "ru").slice(0, 2);
  var THEME = {
    ru: { toLight: "Светлая тема", toDark: "Тёмная тема" },
    en: { toLight: "Light theme", toDark: "Dark theme" },
    de: { toLight: "Helles Design", toDark: "Dunkles Design" }
  };

  // Кнопка темы — последним пунктом в правой части шапки (один раз, даже если скрипт подключён дважды).
  var tools = document.getElementById("tools");
  if (tools && !tools.querySelector(".theme-toggle")) {
    var li = document.createElement("li");
    li.appendChild(H.ui.themeButton(THEME[lang] || THEME.en));
    tools.appendChild(li);
  }

  // Подвал строится из данных бренда; набирать его руками нельзя.
  var footer = document.getElementById("footer");
  if (footer) H.brandUi.renderFooter(footer, lang);

  // Страница «Об авторе»: плашки ссылок и робот со знаком.
  var links = document.getElementById("author-links");
  if (links) H.brandUi.renderAuthorLinks(links, lang);
  var robo = document.getElementById("robo");
  if (robo && H.robot && !robo.closest("#contact")) {
    var robot = H.robot.tvRobot(robo);
    var replay = document.getElementById("robo-replay");
    if (replay) replay.addEventListener("click", function () { robot.play(); });
    robo.addEventListener("click", function () { robot.play(); });
    robot.play();
  }

  // Телефон (≤ 860 px): строка меню скрыта, поэтому из её пунктов строится нижняя панель — «Главная», текущий раздел
  // (или второй пункт), кнопка «Меню» с листом всех пунктов и «Контакт». Разметку страниц менять не нужно.
  var main = document.querySelector(".nav-main");
  if (main && !document.querySelector(".bottomnav")) {
    var MENU = { ru: "Меню", en: "Menu", de: "Menü" };
    var items = Array.prototype.slice.call(main.querySelectorAll("a"));
    var contactLink = main.querySelector("a.nav-contact");
    var inner = items.filter(function (a) { return a !== contactLink; });
    var current = main.querySelector('a[aria-current="page"]');
    var second = current && current !== inner[0] && current !== contactLink ? current : inner[1];
    var bar = document.createElement("nav");
    bar.className = "bottomnav";
    bar.setAttribute("aria-label", (document.getElementById("nav") || main).getAttribute("aria-label") || MENU[lang] || "Menu");
    var copy = function (a) {
      var c = document.createElement("a");
      c.href = a.getAttribute("href");
      c.textContent = a.textContent;
      if (a.getAttribute("rel")) c.rel = a.getAttribute("rel");
      if (a.getAttribute("aria-current")) c.setAttribute("aria-current", a.getAttribute("aria-current"));
      return c;
    };
    [inner[0], second].forEach(function (a) { if (a) bar.appendChild(copy(a)); });
    var sheet = document.createElement("div");
    sheet.className = "more-sheet";
    sheet.id = "more-sheet";
    sheet.hidden = true;
    items.forEach(function (a) { sheet.appendChild(copy(a)); });
    var more = document.createElement("button");
    more.type = "button";
    more.textContent = MENU[lang] || MENU.en;
    more.setAttribute("aria-expanded", "false");
    more.setAttribute("aria-controls", "more-sheet");
    var setOpen = function (open) { sheet.hidden = !open; more.setAttribute("aria-expanded", open ? "true" : "false"); };
    more.addEventListener("click", function () { setOpen(sheet.hidden); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") setOpen(false); });
    document.addEventListener("click", function (e) { if (!sheet.hidden && !sheet.contains(e.target) && e.target !== more) setOpen(false); });
    bar.appendChild(more);
    if (contactLink) bar.appendChild(copy(contactLink));
    var foot = document.getElementById("footer");
    document.body.insertBefore(sheet, foot || null);
    document.body.insertBefore(bar, foot || null);
  }

  // Страница или секция «Контакт»: блок из brand.json, робот справа строится самим блоком.
  var contact = document.getElementById("contact");
  if (contact) H.brandUi.renderContact(contact, lang, { heading: contact.getAttribute("data-heading") || "h2" });
})();
