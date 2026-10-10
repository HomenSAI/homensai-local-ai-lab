// HomenS.AI Style · © 2026 Serhii Khomenko · https://homensai.com/ · https://github.com/HomenSAI · https://www.linkedin.com/in/serhii-khomenko-homensai/
// Общие правила движения (перенесены с homensai.com, site.js 2.21): проявление при прокрутке, общий выключатель анимаций,
// «уменьшить движение», запуск только в поле зрения, смена имени в шапке. Всё — улучшение: без JavaScript текст виден целиком.
// Подключать раньше js/motion-diagrams.js и js/cosmos.js. Описание — docs/MOTION.md.
(function () {
  "use strict";
  var H = window.HomenS = window.HomenS || {};
  var root = document.documentElement;
  var LANG = (root.lang || "ru").slice(0, 2);
  if (LANG !== "en" && LANG !== "de") LANG = "ru";

  var motion = {
    lang: LANG,
    reduced: !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches),
    paused: false,
    // Подпись на языке страницы: t({ ru: "…", en: "…", de: "…" }); нет перевода — английский, затем русский.
    t: function (m) { return m[LANG] != null ? m[LANG] : (m.en != null ? m.en : m.ru); }
  };

  // Общая пауза: класс на <html> останавливает CSS-анимации, событие homensai-motion — циклы скриптов (и робота).
  function setPaused(v) {
    motion.paused = !!v;
    root.classList.toggle("motion-paused", motion.paused);
    if (H.robot && H.robot.motion) H.robot.motion.paused = motion.paused;
    document.dispatchEvent(new CustomEvent("homensai-motion", { detail: { paused: motion.paused } }));
  }
  motion.setPaused = setPaused;

  // cb(true), пока элемент на экране и анимации не на паузе; иначе cb(false). Без IntersectionObserver — считается видимым.
  motion.onVisible = function (el, cb, threshold) {
    var vis = false, last = null;
    function apply() { var v = vis && !motion.paused; if (v !== last) { last = v; cb(v); } }
    document.addEventListener("homensai-motion", apply);
    if (!("IntersectionObserver" in window)) { vis = true; apply(); return; }
    new IntersectionObserver(function (es) {
      es.forEach(function (e) { vis = e.isIntersecting; apply(); });
    }, { threshold: threshold == null ? 0.15 : threshold }).observe(el);
  };

  // cb() после заметного изменения ширины (больше 24 px), с задержкой 150 мс — чтобы схема перестроилась один раз.
  motion.onResize = function (el, cb) {
    var w = el.clientWidth, t;
    window.addEventListener("resize", function () {
      clearTimeout(t);
      t = setTimeout(function () {
        if (Math.abs(el.clientWidth - w) > 24) { w = el.clientWidth; cb(); }
      }, 150);
    });
  };

  // Проявление при прокрутке: .reveal → .reveal.in. Класс .js на <html> включает скрытие (без скрипта всё видно сразу).
  motion.initReveal = function (scope) {
    var items = (scope || document).querySelectorAll(".reveal:not(.in)");
    if (motion.reduced || !("IntersectionObserver" in window)) {
      items.forEach(function (el) { el.classList.add("in"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { threshold: 0, rootMargin: "0px 0px -40px 0px" });
    items.forEach(function (el) { io.observe(el); });
  };

  // Выключатель анимаций (WCAG 2.2.2) — кнопка .motion-toggle, обычно в подвале. При «уменьшить движение» не нужен.
  motion.initToggle = function (btn) {
    btn = btn || document.querySelector(".motion-toggle");
    if (!btn) return;
    if (motion.reduced) { btn.hidden = true; return; }
    btn.hidden = false;
    var on = motion.t({ ru: "Остановить анимации", en: "Pause animations", de: "Animationen anhalten" });
    var off = motion.t({ ru: "Продолжить анимации", en: "Resume animations", de: "Animationen fortsetzen" });
    function paint() { btn.textContent = motion.paused ? off : on; btn.setAttribute("aria-pressed", motion.paused ? "true" : "false"); }
    btn.addEventListener("click", function () { setPaused(!motion.paused); paint(); });
    paint();
  };

  // Смена имени в шапке: «Serhii Khomenko» → «HomenS.AI» → «HomenS.A Inc.» → снова, шаг 2,6 с.
  // «Inc.» — придуманное автором название, компании нет (docs/BRAND.md, раздел 1). У ссылки постоянное aria-label.
  motion.initNameSwap = function (el) {
    var list = el ? [el] : document.querySelectorAll(".name-swap");
    list.forEach(function (n) {
      if (motion.reduced) return;
      var step = 0;
      setInterval(function () {
        if (motion.paused || n.hasAttribute("data-hold")) return;
        step = (step + 1) % 3;
        n.classList.toggle("alt", step > 0);
        n.classList.toggle("inc", step === 2);
      }, 2600);
    });
  };

  H.motion = motion;
  root.classList.add("js");

  function start() {
    motion.initReveal();
    motion.initToggle();
    motion.initNameSwap();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
