// HomenS.AI Style · © 2026 Serhii Khomenko · https://homensai.com/ · https://github.com/HomenSAI · https://www.linkedin.com/in/serhii-khomenko-homensai/
// Бренд на странице: подвал, список ссылок автора и блок «Контакт» строятся из js/brand.js (данные генерируются из brand/brand.json).
// Подключать ПОСЛЕ brand.js. Язык подписей: "ru" | "en" | "de".
(function () {
  "use strict";
  var B = window.HomenS && window.HomenS.brand;
  if (!B) throw new Error("HomenS.brand не найден: подключите js/brand.js перед js/brand-ui.js");

  function byId(id) {
    return B.links.filter(function (l) { return l.id === id; })[0];
  }

  // Почта от сборщиков адресов: в файлах нет «user@domain»; mailto собирается из contact.email_parts
  // только при наведении, фокусе, касании или клике, а видимый текст — «info [at] homensai [dot] com» (S-012).
  function protectMail(a) {
    var arm = function () { a.href = "mailto:" + emailOf(); };
    a.href = "#mail";
    ["mouseenter", "focus", "touchstart", "click"].forEach(function (ev) { a.addEventListener(ev, arm, { passive: true }); });
    return a;
  }

  function anchor(link, text, lang) {
    var a = document.createElement("a");
    a.textContent = text;
    if (link.kind === "mail") return protectMail(a);
    a.href = (lang === "de" && link.url_de) || link.url;
    a.rel = "me noopener";
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

  // ---------- Контакт (как homensai.com/contact.html): карточки, место, адрес с кнопкой «Скопировать», срок ответа ----------
  // Адрес почты не лежит в HTML текстом: он собирается скриптом из двух частей (brand.json → contact.email_parts).
  function tr(m, lang) { return m[lang] != null ? m[lang] : (m.en != null ? m.en : m.ru); }
  function el(tag, cls, text, parent) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  function emailOf(node) {
    var u = node && node.getAttribute("data-u"), d = node && node.getAttribute("data-d");
    if (u && d) return u + "@" + d;
    return B.contact.email_parts.user + "@" + B.contact.email_parts.domain;
  }

  // Кнопка копирования: буфер обмена, иначе старый способ, иначе адрес выделяется и выводится подсказка.
  function bindCopy(btn, addrNode, statusNode, lang) {
    var C = B.contact.copy;
    btn.hidden = false;
    function say(msg, err) {
      if (!statusNode) return;
      statusNode.textContent = "";
      statusNode.classList.toggle("err", !!err);
      setTimeout(function () { statusNode.textContent = msg; }, 30);   // повторное сообщение тоже будет прочитано
    }
    function selectVisible() {
      if (!addrNode || !window.getSelection) return;
      var r = document.createRange();
      r.selectNodeContents(addrNode);
      var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
    }
    function legacyCopy(text) {
      var ta = document.createElement("textarea");
      ta.value = text; ta.setAttribute("readonly", ""); ta.className = "copy-buffer";
      document.body.appendChild(ta); ta.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      document.body.removeChild(ta);
      return ok;
    }
    btn.addEventListener("click", function () {
      var text = emailOf(addrNode);
      var ok = function () { say(tr(C.ok, lang), false); };
      var fail = function () { selectVisible(); say(tr(C.fail, lang), true); };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(ok, function () { if (legacyCopy(text)) ok(); else fail(); });
      } else if (legacyCopy(text)) ok(); else fail();
    });
  }

  // Готовая разметка страницы (как на сайте): .em → ссылка mailto, .em-card → карточка, [data-copy] → кнопка копирования.
  function enhanceEmail(scope, lang) {
    scope = scope || document;
    lang = lang || (document.documentElement.lang || "ru").slice(0, 2);
    scope.querySelectorAll(".em").forEach(function (n) {
      var a = el("a", "em-link", emailOf(n));
      a.href = "mailto:" + emailOf(n);
      n.replaceWith(a);
    });
    scope.querySelectorAll(".em-card").forEach(function (n) {
      n.href = "mailto:" + emailOf(n);
      var b = n.querySelector("b"); if (b) b.textContent = emailOf(n);
    });
    scope.querySelectorAll("[data-copy]").forEach(function (btn) {
      var addr = document.getElementById(btn.getAttribute("data-select"));
      if (addr && addr.getAttribute("data-u")) addr.textContent = emailOf(addr);
      bindCopy(btn, addr, document.getElementById(btn.getAttribute("data-status")), lang);
    });
  }

  // Блок «Контакт» целиком. opts: { heading: "h1" | "h2" (по умолчанию), lead: false — без вводного абзаца,
  // cards: ["email", "linkedin", …] — свой набор карточек по id ссылок, reply: false — без строки о сроке ответа,
  // robot: false — без робота справа от заголовка (по умолчанию он есть, если подключён js/robot.js) }.
  var contactSeq = 0;
  function renderContact(host, lang, opts) {
    lang = lang || "ru"; opts = opts || {};
    var C = B.contact, n = ++contactSeq;
    var box = el("div", "contact");
    // Робот HomenS.AI справа от заголовка (как на сайте): нужен js/robot.js; без него или с robot: false — только текст
    var withRobot = opts.robot !== false && !!(window.HomenS && window.HomenS.robot);
    var top = withRobot ? el("div", "contact-hero", null, box) : box;
    var intro = withRobot ? el("div", "contact-intro", null, top) : box;
    el("p", "eyebrow", tr(C.eyebrow, lang), intro);
    el(opts.heading || "h2", "contact-title", tr(C.title, lang), intro);
    if (opts.lead !== false) el("p", "contact-lead", tr(C.lead, lang), intro);
    var roboHost, roboBtn;
    if (withRobot) {
      var fig = el("figure", "contact-robot author-robot", null, top);
      roboHost = el("div", "robo", null, fig);
      roboHost.setAttribute("role", "img");
      roboHost.setAttribute("aria-label", tr(C.robot.alt, lang));
      var word = el("p", "robo-word", null, fig);
      word.setAttribute("data-robo-word", "");
      word.appendChild(document.createTextNode((B.brand.name || "HomenS.AI").split(".")[0]));
      el("span", "ai", "." + (B.brand.name || "HomenS.AI").split(".").slice(1).join("."), word);
      roboBtn = el("button", "robot-play", tr(C.robot.replay, lang), fig);
      roboBtn.type = "button";
    }
    var cards = el("div", "ccards", null, box);
    var list = opts.cards ? C.cards.filter(function (c) { return opts.cards.indexOf(c.link) >= 0; }) : C.cards;
    list.forEach(function (c) {
      var l = byId(c.link);
      if (!l) return;
      var a = el("a", "ccard", null, cards);
      a.href = c.email ? "mailto:" + emailOf() : ((lang === "de" && l.url_de) || l.url);
      if (l.kind === "profile" || l.kind === "id") a.rel = "me noopener";
      else if (!c.email) a.rel = "noopener";
      el("span", "mono", tr(c.kicker, lang), a);
      el("b", null, c.email ? emailOf() : tr(c.value, lang), a);
    });
    if (C.facts && C.facts.length) {
      var dl = el("dl", "contact-facts", null, box);
      C.facts.forEach(function (f) { var row = el("div", null, null, dl); el("dt", null, tr(f.label, lang), row); el("dd", null, tr(f.value, lang), row); });
    }
    var line = el("div", "mail-line", null, box);
    el("span", "mono", tr(C.mail_label, lang), line);
    var addr = el("span", "mail-text", emailOf(), line);
    addr.id = "contact-mail-" + n;
    var btn = el("button", "copy-btn", tr(C.copy.button, lang), line);
    btn.type = "button";
    var status = el("span", "copy-status", null, line);
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    bindCopy(btn, addr, status, lang);
    if (opts.reply !== false) el("p", "contact-note", tr(C.reply, lang), box);
    host.replaceChildren(box);
    if (withRobot) {
      if (window.HomenS.logoWord) window.HomenS.logoWord.init(box);
      var robot = window.HomenS.robot.tvRobot(roboHost), played = false;
      var start = function () { played = true; robot.play(); };
      var M = window.HomenS.motion;
      if (M && M.onVisible) M.onVisible(roboHost, function (v) { if (v && !played) start(); });
      else if ("IntersectionObserver" in window) {
        var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting && !played) { start(); io.disconnect(); } }); }, { threshold: 0.15 });
        io.observe(roboHost);
      } else start();
      roboHost.addEventListener("click", function () { start(); });
      roboBtn.addEventListener("click", function () { start(); });
    }
    return host;
  }

  window.HomenS.brandUi = { renderFooter: renderFooter, renderAuthorLinks: renderAuthorLinks, renderContact: renderContact, enhanceEmail: enhanceEmail, protectMail: protectMail, link: byId };
})();
