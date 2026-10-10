// HomenS.AI Style · © 2026 Serhii Khomenko · https://homensai.com/ · https://github.com/HomenSAI · https://www.linkedin.com/in/serhii-khomenko-homensai/
// Бренд на странице: подвал и список ссылок автора строятся из js/brand.js (данные генерируются из brand/brand.json).
// Подключать ПОСЛЕ brand.js. Язык подписей: "ru" | "en" | "de".
(function () {
  "use strict";
  var B = window.HomenS && window.HomenS.brand;
  if (!B) throw new Error("HomenS.brand не найден: подключите js/brand.js перед js/brand-ui.js");

  function byId(id) {
    return B.links.filter(function (l) { return l.id === id; })[0];
  }

  function anchor(link, text, lang) {
    var a = document.createElement("a");
    a.href = (lang === "de" && link.url_de) || link.url;
    a.rel = link.kind === "mail" ? "" : "me noopener";
    if (!a.rel) a.removeAttribute("rel");
    a.textContent = text;
    return a;
  }

  // Подвал: «© 2026 Автор · ссылки…». variant: "platform" (по умолчанию, для приложений) или "site" (как на homensai.com:
  // ORCID · LinkedIn · GitHub · Impressum · Privacy · e-mail).
  function renderFooter(host, lang, variant) {
    var order = B.footers[variant || "platform"];
    if (!order) throw new Error("Неизвестный вариант подвала: " + variant);
    var p = document.createElement("p");
    var site = (variant || "platform") === "site";
    p.appendChild(document.createTextNode(site ? B.site.footer_line : B.author.copyright));
    order.forEach(function (id) {
      var l = byId(id);
      if (!l) return;
      p.appendChild(document.createTextNode(" · "));
      p.appendChild(anchor(l, (lang === "de" && l.short_de) || l.short, lang));
    });
    host.replaceChildren(p);
    return host;
  }

  // Ссылки автора плашками (карточка «Об авторе»)
  function renderAuthorLinks(host, lang) {
    lang = lang || "ru";
    var ul = document.createElement("ul");
    ul.className = "author-links";
    B.author_card_order.forEach(function (id) {
      var l = byId(id);
      if (!l) return;
      var li = document.createElement("li");
      li.appendChild(anchor(l, l.label[lang] || l.label.en, lang));
      ul.appendChild(li);
    });
    host.replaceChildren(ul);
    return host;
  }

  window.HomenS.brandUi = { renderFooter: renderFooter, renderAuthorLinks: renderAuthorLinks, link: byId };
})();
