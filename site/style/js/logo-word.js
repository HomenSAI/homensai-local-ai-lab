// HomenS.AI Style · © 2026 Serhii Khomenko · https://homensai.com/ · https://github.com/HomenSAI · https://www.linkedin.com/in/serhii-khomenko-homensai/
// Надпись «HomenS.AI» под большим знаком. Пока знак крутится — надписи нет; когда он собрался (голова робота или готовый логотип) —
// буквы по одной поднимаются снизу, «.AI» вспыхивает бирюзовым, под словом выдвигается линия. «Начать заново» прячет надпись.
// Знак сообщает о себе событиями homensai-logo-formed / homensai-logo-reset (их шлют js/robot.js и js/motion-diagrams.js).
// Разметка: <p class="robo-word" data-robo-word>HomenS<span class="ai">.AI</span></p> рядом со знаком, внутри <figure> или
// элемента с data-logo-scope. Подключать ДО скриптов, которые запускают знак. Описание — docs/MOTION.md, раздел 4.12.
(function () {
  "use strict";

  // Ближайший общий контейнер знака и надписи: [data-logo-scope], [data-mark-scope] или <figure>
  function wordOf(logo) {
    var scope = logo.closest("[data-logo-scope], [data-mark-scope], figure");
    return scope ? scope.querySelector("[data-robo-word]") : null;
  }

  document.addEventListener("homensai-logo-formed", function (e) {
    var w = wordOf(e.target);
    if (w) w.classList.add("on");
  });
  document.addEventListener("homensai-logo-reset", function (e) {
    var w = wordOf(e.target);
    if (w) w.classList.remove("on");
  });

  // Буквы — отдельные элементы с номером (--i), чтобы появляться по очереди; текст для диктора остаётся словом целиком
  function split(node) {
    if (node.getAttribute("data-split")) return;
    node.setAttribute("data-split", "1");
    var n = 0;
    (function walk(parent) {
      Array.prototype.slice.call(parent.childNodes).forEach(function (c) {
        if (c.nodeType === 3) {
          var frag = document.createDocumentFragment();
          c.textContent.split("").forEach(function (ch) {
            var s = document.createElement("span");
            s.className = "l";
            s.textContent = ch;
            s.style.setProperty("--i", n++);
            frag.appendChild(s);
          });
          parent.replaceChild(frag, c);
        } else if (c.nodeType === 1) walk(c);
      });
    })(node);
  }

  function init(scope) {
    (scope && scope.querySelectorAll ? scope : document).querySelectorAll("[data-robo-word]").forEach(function (w) {
      split(w);
      // Ждёт знак, только если знак действительно будет анимироваться; иначе (нет скриптов знака) надпись видна сразу
      var H = window.HomenS || {};
      if (!w.classList.contains("on") && (H.robot || H.motionDiagrams)) w.classList.add("wait");
    });
  }
  window.HomenS = window.HomenS || {};
  window.HomenS.logoWord = { init: init };   // для надписей, добавленных на страницу позже (например, блок «Контакт»)
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { init(); });
  else init();
})();
