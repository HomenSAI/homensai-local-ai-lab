// HomenS.AI Style · © 2026 Serhii Khomenko · https://homensai.com/ · https://github.com/HomenSAI · https://www.linkedin.com/in/serhii-khomenko-homensai/
// Анимированные схемы (перенесены с homensai.com, diagrams.js 2.21): цикл роста, петля проверки, «код → намерение», шаги,
// полный цикл заказа, разрыв «идея → реальность», «ИИ и бизнес», два мира, шифр Цезаря, канат, живой знак, знак с выносками.
// Каждая схема идёт только пока видна на экране, стоит на общей паузе и при «уменьшить движение» показывает итоговый кадр.
// Подключать после js/motion.js (и js/robot.js, если на странице есть канат или робот). Разметка — docs/MOTION.md, раздел 4.
// Запуск: всё с атрибутом data-dia="…" запускается само; вручную — HomenS.motionDiagrams.mount(элемент, вид, параметры).
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var H = window.HomenS = window.HomenS || {};
  var M = H.motion;
  if (!M) throw new Error("HomenS.motion не найден: подключите js/motion.js перед js/motion-diagrams.js");
  var reduce = M.reduced;
  function L(en, ru, de) { return M.t({ en: en, ru: ru, de: de }); }
  var LOC = M.lang === "de" ? "de-DE" : M.lang === "en" ? "en-US" : "ru-RU";

  function s(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    if (attrs) for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function el(tag, cls, text, parent) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  var onVisible = M.onVisible, onResize = M.onResize;
  var ease = function (x) { return x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2; };
  // Перезапуск CSS-анимации класса: снять, заставить пересчитать, поставить снова
  function restartClass(node, cls) { node.classList.remove(cls); void (node.getBBox ? node.getBBox() : node.offsetWidth); node.classList.add(cls); }
  function uid() { return Math.random().toString(36).slice(2, 8); }

  /* ---------- 1. Цикл роста: пять шагов по кругу, «Успех» наполняется, молнии от шага к центру ---------- */
  function growthCycle(root, o) {
    var P = o.steps || [
      { t: L("Intent", "Замысел", "Ziel"), d: L("Everything starts with an idea and clear goals.", "Всё начинается с идеи и ясных целей.", "Alles beginnt mit einer Idee und klaren Zielen.") },
      { t: L("Equip", "Оснащение", "Ausrüsten"), d: L("Use the best tools within reach — and check what they deliver.", "Используй лучшие доступные инструменты и проверяй результат.", "Die besten verfügbaren Werkzeuge nutzen — und prüfen, was sie liefern.") },
      { t: L("Optimize", "Оптимизация", "Optimieren"), d: L("Streamline routine and outdated procedures. Keep the checks that matter.", "Упрости рутину и устаревшие процедуры. Оставь важные проверки.", "Routine und veraltete Abläufe vereinfachen. Die Kontrollen behalten, die zählen.") },
      { t: L("Accelerate", "Ускорение", "Beschleunigen"), d: L("The world speeds up. Fast, thorough learning is a real advantage.", "Мир ускоряется. Быстрое и основательное обучение — реальное преимущество.", "Die Welt wird schneller. Schnelles, gründliches Lernen ist ein echter Vorteil.") },
      { t: L("Implement", "Внедрение", "Umsetzen"), d: L("Test, verify, put into operation. The next cycle starts from what was learned.", "Тестируй, проверяй, запускай. Следующий цикл начинается с полученного опыта.", "Testen, prüfen, in Betrieb nehmen. Der nächste Zyklus beginnt mit dem Gelernten.") }
    ];
    var N = P.length;
    var canvas = root.querySelector(".dia-canvas");
    var capBox = root.querySelector(".dia-caption");
    var capNum = root.querySelector(".cap-num");
    var capTitle = root.querySelector(".cap-title");
    var capText = root.querySelector(".cap-text");
    var outCycle = root.querySelector("[data-cycle]");
    var outSpeed = root.querySelector("[data-speed]");
    function two(n) { return (n < 10 ? "0" : "") + n; }

    var C = 300, R = 205, circ = 2 * Math.PI * R;
    var svg = s("svg", { viewBox: "0 0 600 600", class: "cycle-svg", role: "img",
      "aria-label": o.label || L("Growth cycle (schematic): intent, equip, optimize, accelerate, implement", "Цикл роста (схема): замысел, оснащение, оптимизация, ускорение, внедрение", "Wachstumszyklus (schematische Darstellung): Ziel, Ausrüsten, Optimieren, Beschleunigen, Umsetzen") }, canvas);
    var pos = P.map(function (_, i) {
      var a = (-90 + 360 / N * i) * Math.PI / 180;
      return { x: C + R * Math.cos(a), y: C + R * Math.sin(a) };
    });
    pos.forEach(function (p) { s("line", { x1: C, y1: C, x2: p.x, y2: p.y, class: "c-spoke" }, svg); });
    s("circle", { cx: C, cy: C, r: R, class: "c-ring" }, svg);
    var prog = s("circle", { cx: C, cy: C, r: R, class: "c-prog", transform: "rotate(-90 " + C + " " + C + ")",
      "stroke-dasharray": circ, "stroke-dashoffset": circ }, svg);

    // В центре «Успех» наполняется, как сосуд, по мере прохождения круга
    var clipId = "cfill-" + uid();
    s("circle", { cx: C, cy: C, r: 90 }, s("clipPath", { id: clipId }, s("defs", {}, svg)));
    var center = s("g", { class: "c-center" }, svg);
    s("circle", { cx: C, cy: C, r: 92 }, center);
    var fillG = s("g", { "clip-path": "url(#" + clipId + ")" }, center);
    var waveBack = s("path", { class: "c-fill c-fill-back" }, fillG);
    var wave = s("path", { class: "c-fill" }, fillG);
    s("text", { x: C, y: C - 2, class: "c-center-t" }, center).textContent = o.center || L("Success", "Успех", "Erfolg");
    var pct = s("text", { x: C, y: C + 26, class: "c-center-s" }, center);
    pct.textContent = "0%";

    var bolts = s("g", { class: "c-bolts" }, svg);
    var comet = s("g", {}, svg);
    s("circle", { r: 16, class: "c-glow" }, comet);
    s("circle", { r: 7, class: "c-comet" }, comet);

    var t = 0, speed = 1, cycle = 1, active = -1, running = false, last = null, BASE = o.period || 11000;
    var level = 0, phase = 0;
    function jump(i) { t = i / N + 0.0001; draw(); }

    var nodes = P.map(function (p, i) {
      var g = s("g", { class: "c-node" }, svg);
      s("circle", { cx: pos[i].x, cy: pos[i].y, r: 52 }, g);
      s("text", { x: pos[i].x, y: pos[i].y - 12, class: "n" }, g).textContent = two(i + 1);
      s("text", { x: pos[i].x, y: pos[i].y + 10 }, g).textContent = p.t;
      g.addEventListener("click", function () { jump(i); });
      return g;
    });
    // Настоящие кнопки шагов: то же действие, что щелчок по кружку, но с клавиатуры и для экранного диктора
    var bar = el("div", "c-steps", null, capBox);
    bar.setAttribute("role", "group");
    bar.setAttribute("aria-label", L("Jump to a step of the cycle", "К шагу цикла", "Zu einem Schritt des Zyklus springen"));
    var stepBtns = P.map(function (p, i) {
      var b = el("button", null, null, bar);
      b.type = "button";
      el("span", "n", two(i + 1), b).setAttribute("aria-hidden", "true");
      b.appendChild(document.createTextNode(p.t));
      b.addEventListener("click", function () { jump(i); });
      return b;
    });

    function wavePath(lv, ph, amp) {
      var y0 = C + 90 - 180 * lv, d = "M" + (C - 100) + " " + (C + 100);
      for (var x = C - 100; x <= C + 100; x += 8) d += " L" + x + " " + (y0 + amp * Math.sin(x / 17 + ph)).toFixed(1);
      return d + " L" + (C + 100) + " " + (C + 100) + " Z";
    }
    function drawFill() {
      var amp = level > 0.01 && level < 0.99 ? 5 : 1.5;
      waveBack.setAttribute("d", wavePath(level, phase + 1.8, amp));
      wave.setAttribute("d", wavePath(level, phase, amp));
      pct.textContent = Math.round(level * 100) + "%";
    }
    // Молния от шага к центру: ломаная с разбросом, ответвление и второе мерцание
    function zigzag(x1, y1, x2, y2, segs, spread) {
      var dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy), nx = -dy / len, ny = dx / len, pts = [];
      for (var k = 0; k <= segs; k++) {
        var f = k / segs, j = (k === 0 || k === segs) ? 0 : (Math.random() * 2 - 1) * spread * Math.sin(Math.PI * f);
        pts.push([x1 + dx * f + nx * j, y1 + dy * f + ny * j]);
      }
      return pts;
    }
    function strike(pts, cls, width, dur, delay) {
      var p = s("path", { d: "M" + pts.map(function (q) { return q[0].toFixed(1) + " " + q[1].toFixed(1); }).join(" L"), class: cls, "stroke-width": width }, bolts);
      var len = p.getTotalLength();
      p.style.strokeDasharray = len;
      p.style.strokeDashoffset = len;
      if (p.animate) {
        p.animate([
          { strokeDashoffset: len, opacity: 1 },
          { strokeDashoffset: 0, opacity: 1, offset: 0.3 },
          { strokeDashoffset: 0, opacity: 0.25, offset: 0.45 },
          { strokeDashoffset: 0, opacity: 1, offset: 0.58 },
          { strokeDashoffset: 0, opacity: 0 }
        ], { duration: dur, delay: delay || 0, easing: "ease-out", fill: "forwards" });
      }
      setTimeout(function () { p.remove(); }, dur + (delay || 0) + 50);
    }
    function bolt(i) {
      if (reduce) return;
      var p = pos[i], dx = C - p.x, dy = C - p.y, d = Math.hypot(dx, dy), ux = dx / d, uy = dy / d;
      var sx = p.x + ux * 54, sy = p.y + uy * 54, ex = C - ux * 93, ey = C - uy * 93;
      var main = zigzag(sx, sy, ex, ey, 9, 15);
      strike(main, "c-bolt-glow", 11, 900);
      strike(main, "c-bolt", 3, 900);
      var from = main[3 + Math.floor(Math.random() * 3)], side = Math.random() < 0.5 ? -1 : 1;
      var fx = from[0] + (ux * 0.6 - uy * side * 0.8) * 40, fy = from[1] + (uy * 0.6 + ux * side * 0.8) * 40;
      var fork = zigzag(from[0], from[1], fx, fy, 3, 6);
      strike(fork, "c-bolt-glow", 6, 650, 90);
      strike(fork, "c-bolt", 1.8, 650, 90);
      var second = zigzag(sx, sy, ex, ey, 9, 12);
      strike(second, "c-bolt-glow", 7, 700, 170);
      strike(second, "c-bolt", 1.8, 700, 170);
      restartClass(center, "hit");
    }
    function setActive(i) {
      active = i;
      bolt(i);
      nodes.forEach(function (g, j) { g.classList.toggle("on", j === i); g.classList.toggle("done", j < i); });
      stepBtns.forEach(function (b, j) { if (j === i) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current"); });
      capNum.textContent = two(i + 1) + " / " + two(N);
      capTitle.textContent = P[i].t;
      capText.textContent = P[i].d;
      restartClass(capBox, "swap");
    }
    function draw() {
      var a = (-90 + 360 * t) * Math.PI / 180;
      comet.setAttribute("transform", "translate(" + (C + R * Math.cos(a)) + " " + (C + R * Math.sin(a)) + ")");
      prog.setAttribute("stroke-dashoffset", circ * (1 - t));
      var i = Math.min(N - 1, Math.floor(t * N));
      if (i !== active) setActive(i);
      level += (t - level) * (t < level ? 0.06 : 0.12);
      phase += 0.08;
      drawFill();
    }
    // Каждый новый круг быстрее в 1,35 раза; после четвёртого — снова с ×1,0
    function pulse() {
      restartClass(center, "pulse");
      if (outCycle) outCycle.textContent = cycle;
      if (outSpeed) outSpeed.textContent = "×" + speed.toFixed(1);
    }
    function frame(now) {
      if (!running) { last = null; return; }
      if (last == null) last = now;
      t += Math.min(64, now - last) / BASE * speed;
      last = now;
      if (t >= 1) {
        t -= 1;
        cycle++;
        if (cycle > 4) { cycle = 1; speed = 1; } else speed *= 1.35;
        pulse();
      }
      draw();
      requestAnimationFrame(frame);
    }

    draw();
    if (reduce) { prog.setAttribute("stroke-dashoffset", 0); level = 1; drawFill(); return; }

    // Пауза/пуск — значок, как на магнитофоне; выбор пользователя сильнее видимости
    var paused = false, visible = false;
    var btn = el("button", "dia-pause");
    btn.type = "button";
    function label() {
      var ic = s("svg", { viewBox: "0 0 16 16", "aria-hidden": "true" });
      if (paused) s("path", { d: "M4 2.5v11l9.5-5.5z" }, ic);
      else { s("rect", { x: 3, y: 2.5, width: 3.5, height: 11, rx: 1 }, ic); s("rect", { x: 9.5, y: 2.5, width: 3.5, height: 11, rx: 1 }, ic); }
      btn.replaceChildren(ic);
      btn.setAttribute("aria-label", paused ? L("Play", "Пуск", "Start") : L("Pause", "Пауза", "Pause"));
      btn.title = btn.getAttribute("aria-label");
      btn.setAttribute("aria-pressed", paused ? "true" : "false");
      root.classList.toggle("paused", paused);
    }
    function sync() {
      var should = visible && !paused;
      if (should && !running) { running = true; requestAnimationFrame(frame); }
      else if (!should) running = false;
    }
    btn.addEventListener("click", function () { paused = !paused; label(); sync(); });
    var meter = root.querySelector(".dia-meter");
    if (meter) meter.appendChild(btn);
    label();
    onVisible(root, function (v) { visible = v; sync(); });
  }

  /* ---------- 2. Петля проверки: понять → … → замер; не сошлось — исправить и перепроверить; затем документ ---------- */
  function verifyLoop(root, o) {
    var canvas = root.querySelector(".dia-canvas");
    var log = root.querySelector(".dia-log");
    var badge = root.querySelector(".dia-badge");
    var MAIN = o.nodes || [L("Understand", "Понять", "Verstehen"), L("Plan", "План", "Plan"), L("Build", "Сборка", "Bau"), L("Test", "Тест", "Test"), L("Measure", "Замер", "Messung"), L("Document", "Документ", "Dokument")];
    var FIX = o.fix || L("Fix", "Исправить", "Korrigieren");
    var STEPS = o.steps || [
      { to: 0, k: L("understand", "понять", "verstehen"), m: L("map the system and its limits", "изучить систему и её ограничения", "das System und seine Grenzen kartieren") },
      { from: 0, to: 1, k: L("plan", "план", "planen"), m: L("split into verifiable checkpoints", "разбить на проверяемые этапы", "in prüfbare Meilensteine teilen") },
      { from: 1, to: 2, k: L("build", "сборка", "bauen"), m: L("assemble from the best available tools", "собрать из лучших инструментов", "aus den besten verfügbaren Werkzeugen zusammensetzen") },
      { from: 2, to: 3, k: L("test", "тест", "testen"), m: L("run the checks", "запустить проверки", "Prüfungen ausführen") },
      { from: 3, to: 4, k: L("measure", "замер", "messen"), m: L("result below target", "результат ниже цели", "Ergebnis unter dem Ziel"), st: "warn" },
      { from: 4, to: "fix", k: L("fix", "исправить", "korrigieren"), m: L("find the root cause, adjust", "найти первопричину, исправить", "Ursache finden, nachjustieren") },
      { from: "fix", to: 3, k: L("re-test", "перетест", "erneut testen"), m: L("run the checks again", "запустить проверки снова", "Prüfungen erneut ausführen") },
      { from: 3, to: 4, k: L("measure", "замер", "messen"), m: L("target met", "цель достигнута", "Ziel erreicht"), st: "ok" },
      { from: 4, to: 5, k: L("document", "документ", "dokumentieren"), m: L("results + recovery notes", "результаты + инструкции восстановления", "Ergebnisse + Wiederherstellungshinweise"), st: "ok", end: true }
    ];
    var token, nodeEls, paths, k, phase, tp, seg, segLen, holdDur, running = false, last = null;

    // Широко (от 720 px) — в строку с петлёй снизу; узко — в столбец с петлёй справа
    function build() {
      canvas.replaceChildren();
      var W = Math.max(280, canvas.clientWidth), wide = W >= 720, pos = {}, Hh, nw, fw, nh = 44;
      if (wide) {
        var pad = 70, step = (W - 2 * pad) / 5;
        nw = Math.min(130, step - 16); fw = 84; Hh = 280;
        MAIN.forEach(function (_, i) { pos[i] = { x: pad + i * step, y: 90 }; });
        pos.fix = { x: (pos[3].x + pos[4].x) / 2, y: 220 };
      } else {
        var cx = Math.round(W * 0.36);
        nw = Math.min(170, W * 0.52);
        MAIN.forEach(function (_, i) { pos[i] = { x: cx, y: 34 + i * 68 }; });
        var right = cx + nw / 2;
        fw = Math.min(84, W - right - 20);
        pos.fix = { x: right + (W - right) / 2, y: (pos[3].y + pos[4].y) / 2 };
        Hh = pos[5].y + 36;
      }
      var svg = s("svg", { viewBox: "0 0 " + W + " " + Hh, class: "loop-svg", role: "img",
        "aria-label": o.label || L("Verification loop: understand, plan, build, test, measure; on failure fix and re-test; then document", "Петля проверки: понять, спланировать, собрать, протестировать, измерить; при неудаче исправить и перепроверить; затем задокументировать", "Prüfschleife: verstehen, planen, bauen, testen, messen; bei Fehler korrigieren und erneut testen; dann dokumentieren") }, canvas);
      paths = {};
      for (var i = 0; i < 5; i++) paths[i + "-" + (i + 1)] = s("path", { d: "M" + pos[i].x + " " + pos[i].y + " L" + pos[i + 1].x + " " + pos[i + 1].y, class: "l-edge" }, svg);
      var Mm = pos[4], F = pos.fix, T = pos[3];
      var dMF = wide ? "M" + Mm.x + " " + Mm.y + " Q" + Mm.x + " " + F.y + " " + F.x + " " + F.y : "M" + Mm.x + " " + Mm.y + " Q" + F.x + " " + Mm.y + " " + F.x + " " + F.y;
      var dFT = wide ? "M" + F.x + " " + F.y + " Q" + T.x + " " + F.y + " " + T.x + " " + T.y : "M" + F.x + " " + F.y + " Q" + F.x + " " + T.y + " " + T.x + " " + T.y;
      paths["4-fix"] = s("path", { d: dMF, class: "l-loop" }, svg);
      paths["fix-3"] = s("path", { d: dFT, class: "l-loop" }, svg);
      nodeEls = {};
      MAIN.concat([FIX]).forEach(function (text, n) {
        var isFix = n === MAIN.length, key = isFix ? "fix" : n, p = pos[key], w = isFix ? fw : nw;
        var g = s("g", { class: "l-node" + (isFix ? " l-fix" : "") }, svg);
        s("rect", { x: p.x - w / 2, y: p.y - nh / 2, width: w, height: nh, rx: 10 }, g);
        s("text", { x: p.x, y: p.y }, g).textContent = text;
        nodeEls[key] = g;
      });
      token = s("g", { class: "l-token" }, svg);
      s("circle", { r: 14, class: "l-glow" }, token);
      s("circle", { r: 6, class: "l-dot" }, token);
      token.pos = pos;
    }
    function addLog(step) {
      var row = el("div", null, null, log);
      el("span", "k", (step.k + "           ").slice(0, 11), row);
      row.appendChild(document.createTextNode(step.m));
      if (step.st === "warn") { row.appendChild(document.createTextNode(" ")); el("span", "w", "✗", row); }
      if (step.st === "ok") { row.appendChild(document.createTextNode(" ")); el("span", "ok", "✓", row); }
      while (log.children.length > 9) log.removeChild(log.firstChild);
    }
    function arrive(step) {
      var n = nodeEls[step.to];
      n.classList.remove("warn", "ok");
      n.classList.add("on");
      if (step.st) n.classList.add(step.st);
      addLog(step);
      if (step.end && badge) badge.classList.add("show");
      token.classList.remove("moving");
      holdDur = step.end ? 2800 : step.st === "warn" ? 1000 : 420;
    }
    function place(p) { token.setAttribute("transform", "translate(" + p.x + " " + p.y + ")"); }
    function reset() {
      Object.keys(nodeEls).forEach(function (key) { nodeEls[key].classList.remove("on", "warn", "ok"); });
      log.replaceChildren();
      if (badge) badge.classList.remove("show");
      k = 0; phase = "hold"; tp = 0;
      place(token.pos[0]);
      arrive(STEPS[0]);
      holdDur = 700;
    }
    // Точка едет по ребру за 520 мс + 1,6 мс на пиксель, плавно; на шаге стоит 0,42 с, на «✗» — 1 с, в конце — 2,8 с
    function frame(now) {
      if (!running) { last = null; return; }
      if (last == null) last = now;
      tp += Math.min(64, now - last);
      last = now;
      if (phase === "hold" && tp >= holdDur) {
        k++;
        if (k >= STEPS.length) reset();
        else {
          seg = paths[STEPS[k].from + "-" + STEPS[k].to];
          segLen = seg.getTotalLength();
          phase = "move"; tp = 0;
          token.classList.add("moving");
        }
      }
      if (phase === "move") {
        var dur = 520 + segLen * 1.6, f = Math.min(1, tp / dur);
        place(seg.getPointAtLength(segLen * ease(f)));
        if (f >= 1) { arrive(STEPS[k]); phase = "hold"; tp = 0; }
      }
      requestAnimationFrame(frame);
    }
    function finalState() {
      STEPS.forEach(function (st) { var n = nodeEls[st.to]; n.classList.add("on"); if (st.st) { n.classList.remove("warn"); n.classList.add(st.st); } addLog(st); });
      if (badge) badge.classList.add("show");
      place(token.pos[5]);
    }
    build();
    if (reduce) { finalState(); return; }
    reset();
    onResize(canvas, function () { build(); reset(); });
    onVisible(root, function (v) {
      if (v && !running) { running = true; requestAnimationFrame(frame); }
      else if (!v) running = false;
    });
  }

  /* ---------- 3. «Код → намерение»: строки кода растут, гаснут, печатается задача, загораются шаги ---------- */
  function shift(root, o) {
    var linesBox = root.querySelector(".code-lines");
    var count = root.querySelector("[data-lines]");
    var codeCol = root.querySelector(".shift-code");
    var intentText = root.querySelector(".intent-text");
    var outs = root.querySelectorAll(".intent-out li");
    var result = root.querySelector(".intent-result");
    var SENTENCE = o.sentence || root.getAttribute("data-sentence") || L("Build a private AI server for my team. Test it, measure it, document it.", "Собери приватный ИИ-сервер для моей команды. Протестируй, измерь, задокументируй.", "Aufgabe: einen privaten KI-Server für mein Team aufbauen, testen, messen und dokumentieren.");
    var TOTAL = Number(o.lines || root.getAttribute("data-total-lines")) || 1200;
    // Постоянная «форма» псевдокода: отступ + ширины слов в %
    var SHAPE = [[0, 18, 30], [1, 22, 12, 26], [2, 14, 34], [2, 28, 16], [1, 10], [1, 20, 24, 12], [2, 36], [2, 16, 22], [3, 26, 10], [2, 12], [1, 30, 14], [0, 8]];
    SHAPE.forEach(function (row) {
      var l = el("div", "code-line", null, linesBox);
      l.style.paddingLeft = row[0] * 7 + "%";
      row.slice(1).forEach(function (w, j) { var t = el("i", j === 0 ? "kw" : null, null, l); t.style.width = w + "%"; });
    });
    var lines = linesBox.children, timers = [], running = false;
    function later(fn, ms) { timers.push(setTimeout(fn, ms)); }
    function clear() { timers.forEach(clearTimeout); timers = []; }
    function reset() {
      root.classList.remove("phase-2", "phase-3");
      codeCol.classList.remove("fade");
      [].forEach.call(lines, function (l) { l.classList.remove("show"); });
      outs.forEach(function (x) { x.classList.remove("show"); });
      result.classList.remove("show");
      intentText.textContent = "";
      count.textContent = "0";
    }
    // Фаза 1 — строка за строкой через 180 мс; фаза 2 — код гаснет, задача печатается по 28 мс на знак; фаза 3 — шаги через 450 мс
    function run() {
      reset();
      [].forEach.call(lines, function (l, i) {
        later(function () { l.classList.add("show"); count.textContent = Math.round((i + 1) / lines.length * TOTAL).toLocaleString(LOC); }, 180 * i);
      });
      var t = 180 * lines.length + 500;
      later(function () { codeCol.classList.add("fade"); root.classList.add("phase-2"); }, t);
      for (var c = 1; c <= SENTENCE.length; c++) (function (c) { later(function () { intentText.textContent = SENTENCE.slice(0, c); }, t + 300 + c * 28); })(c);
      t += 300 + SENTENCE.length * 28 + 300;
      outs.forEach(function (x, i) { later(function () { x.classList.add("show"); }, t + i * 450); });
      t += outs.length * 450 + 200;
      later(function () { result.classList.add("show"); root.classList.add("phase-3"); }, t);
      later(function () { if (running) run(); }, t + 3200);
    }
    function finalState() {
      [].forEach.call(lines, function (l) { l.classList.add("show"); });
      codeCol.classList.add("fade");
      count.textContent = TOTAL.toLocaleString(LOC);
      intentText.textContent = SENTENCE;
      outs.forEach(function (x) { x.classList.add("show"); });
      result.classList.add("show");
      root.classList.add("phase-2", "phase-3");
    }
    if (reduce) { finalState(); return; }
    onVisible(root, function (v) {
      if (v && !running) { running = true; run(); }
      else if (!v && running) { running = false; clear(); }
    });
  }

  /* ---------- 4. Шаги: карточки загораются по очереди, снизу бежит полоса 2,4 с ---------- */
  function stepper(root) {
    var cards = root.querySelectorAll(".card, .exp"), i = 0, timer = null;
    if (reduce || !cards.length) return;
    root.classList.add("stepper");
    function tick() {
      cards.forEach(function (c, j) { c.classList.toggle("on", j === i); c.classList.toggle("past", j < i); });
      i = (i + 1) % (cards.length + 1);
      timer = setTimeout(tick, i === 0 ? 1400 : 2400);
    }
    onVisible(root, function (v) {
      if (v && !timer) tick();
      else if (!v && timer) { clearTimeout(timer); timer = null; }
    });
  }

  /* ---------- 5. Полный цикл заказа: колонки этапов, пункты загораются через 0,9 с, полоса растёт, в конце значок ---------- */
  function projectCycle(root) {
    var cols = root.querySelectorAll(".pc-col");
    var items = root.querySelectorAll(".pc-col li");
    var bar = root.querySelector(".pc-bar i");
    var outStage = root.querySelector("[data-stage]");
    var badge = root.querySelector(".dia-badge");
    var total = root.querySelector("[data-total]");
    if (total) total.textContent = items.length;
    var i = -1, timer = null;
    function show(n) {
      items.forEach(function (li, j) { li.classList.toggle("on", j === n); li.classList.toggle("done", j < n); });
      cols.forEach(function (c) {
        var lis = c.querySelectorAll("li"), first = [].indexOf.call(items, lis[0]), lastI = first + lis.length - 1;
        c.classList.toggle("active", n >= first && n <= lastI);
        c.classList.toggle("complete", n > lastI);
      });
      bar.style.width = ((n + 1) / items.length * 100) + "%";
      if (outStage) outStage.textContent = Math.max(1, n + 1);
      if (badge) badge.classList.toggle("show", n >= items.length - 1);
    }
    function tick() {
      i++;
      if (i >= items.length) {
        // итог держится 2,6 с, затем начинается следующий заказ
        timer = setTimeout(function () {
          i = -1; items.forEach(function (li) { li.classList.remove("on", "done"); });
          cols.forEach(function (c) { c.classList.remove("active", "complete"); }); bar.style.width = "0"; if (badge) badge.classList.remove("show");
          timer = setTimeout(tick, 600);
        }, 2600);
        return;
      }
      show(i);
      timer = setTimeout(tick, 900);
    }
    if (reduce) { show(items.length - 1); return; }
    onVisible(root, function (v) {
      if (v && !timer) tick();
      else if (!v && timer) { clearTimeout(timer); timer = null; }
    });
  }

  /* ---------- 6–7. Переключатель «тогда / сейчас»: разрыв «идея → реальность» и «ИИ и бизнес» ---------- */
  // Сам переключается (4,2 / 5,2 с или 3,5 / 7 с); после щелчка пользователя автосмена останавливается.
  function toggleLoop(root, set, thenMs, nowMs) {
    var buttons = root.querySelectorAll(".gap-toggle button"), mode = "then", timer = null, auto = !reduce;
    function go(m) { mode = m; buttons.forEach(function (b) { b.classList.toggle("on", b.dataset.mode === m); b.setAttribute("aria-pressed", b.dataset.mode === m ? "true" : "false"); }); set(m); }
    function loop() { timer = setTimeout(function () { go(mode === "then" ? "now" : "then"); loop(); }, mode === "then" ? thenMs : nowMs); }
    buttons.forEach(function (b) { b.addEventListener("click", function () { auto = false; clearTimeout(timer); timer = null; go(b.dataset.mode); }); });
    if (reduce) { go("now"); return; }
    go("then");
    onVisible(root, function (v) {
      if (v && auto && !timer) loop();
      else if (!v && timer) { clearTimeout(timer); timer = null; }
    });
  }
  function gap(root) {
    var caption = root.querySelector(".gap-caption");
    toggleLoop(root, function (m) {
      root.classList.toggle("now", m === "now");
      if (caption && caption.dataset[m]) { restartClass(caption, "swap"); caption.textContent = caption.dataset[m]; }
    }, 4200, 5200);
  }
  function aiBusiness(root) {
    var era = root.querySelector("[data-era]");
    root.querySelectorAll(".ab-col li").forEach(function (li, i) {
      li.style.setProperty("--i", i);
      var role = li.classList.contains("gate") ? "gate" : li.dataset.ai ? "ai" : "people";
      li.classList.add("r-" + role);
      var note = el("small", "ab-note mono", null, li);
      note.textContent = li.dataset.ai ? L("AI · ", "ИИ · ", "KI · ") + li.dataset.ai : role === "gate" ? L("Human decides", "Человек решает", "Mensch entscheidet") : L("Hands & skill", "Руки и мастерство", "Hände & Können");
      if (role === "gate" && li.dataset.ai) note.textContent += L(" · decision: human", " · решение: человек", " · Entscheidung: Mensch");
    });
    toggleLoop(root, function (m) {
      root.classList.toggle("now", m === "now");
      if (era) era.textContent = m === "now" ? (era.dataset.now || L("today · people + AI", "сегодня · люди + ИИ", "heute · Menschen + KI")) : (era.dataset.then || L("2008 · people", "2008 · люди", "2008 · Menschen"));
    }, 3500, 7000);
  }

  /* ---------- 8. Два мира: строки времени загораются через 0,65 с, ось наливается от золотого к бирюзовому ---------- */
  function worlds(root) {
    var rows = root.querySelectorAll(".w-row");
    var spine = root.querySelector(".w-spine");
    var box = root.querySelector(".w-rows");
    var replay = root.querySelector(".dia-replay");
    var timers = [], started = false;
    function fillTo(row) { var r = row.getBoundingClientRect(), b = box.getBoundingClientRect(); spine.style.height = (r.top - b.top + r.height / 2) + "px"; }
    function play() {
      timers.forEach(clearTimeout); timers = [];
      rows.forEach(function (r) { r.classList.remove("lit"); });
      spine.style.height = "0";
      rows.forEach(function (r, i) { timers.push(setTimeout(function () { r.classList.add("lit"); fillTo(r); }, 400 + i * 650)); });
    }
    function finalState() { rows.forEach(function (r) { r.classList.add("lit"); }); fillTo(rows[rows.length - 1]); }
    if (replay) replay.addEventListener("click", function () { if (reduce) finalState(); else play(); });
    window.addEventListener("resize", function () { var lit = root.querySelectorAll(".w-row.lit"); if (lit.length) fillTo(lit[lit.length - 1]); });
    if (reduce) { finalState(); return; }
    onVisible(root, function (v) { if (v && !started) { started = true; play(); } });
  }

  /* ---------- 9. Шифр Цезаря: буквы «перебираются» и встают на место по одной, в конце текст зеленеет ---------- */
  function caesar(root, o) {
    var out = root.querySelector(".c-text");
    var PLAIN = (o.plain || root.getAttribute("data-plain") || "IMAGINATION").toUpperCase(), SHIFT = Number(o.shift || root.getAttribute("data-shift")) || 3, A = 65;
    var enc = PLAIN.replace(/[A-Z]/g, function (c) { return String.fromCharCode((c.charCodeAt(0) - A + SHIFT) % 26 + A); });
    var timers = [], running = false;
    function render(n, scramble) {
      var frag = document.createDocumentFragment();
      PLAIN.split("").forEach(function (c, i) {
        if (i < n) el("b", null, c, frag);
        else if (i === n && scramble) el("i", null, String.fromCharCode(A + Math.floor(Math.random() * 26)), frag);
        else frag.appendChild(document.createTextNode(enc[i]));
      });
      out.replaceChildren(frag);
    }
    function cycle() {
      timers.forEach(clearTimeout); timers = [];
      render(0);
      root.classList.remove("solved");
      var t = 1200;
      for (var n = 0; n < PLAIN.length; n++) {
        (function (n) {
          for (var k = 0; k < 3; k++) timers.push(setTimeout(function () { render(n, true); }, t + k * 60));
          timers.push(setTimeout(function () { render(n + 1); }, t + 200));
        })(n);
        t += 220;
      }
      timers.push(setTimeout(function () { root.classList.add("solved"); }, t));
      timers.push(setTimeout(function () { if (running) cycle(); }, t + 3000));
    }
    if (reduce) { render(PLAIN.length); root.classList.add("solved"); return; }
    onVisible(root, function (v) {
      if (v && !running) { running = true; cycle(); }
      else if (!v && running) { running = false; timers.forEach(clearTimeout); timers = []; }
    });
  }

  /* ---------- 10. Живой знак: шестерёнка крутится, становится платой, по дорожкам бегут сигналы, знак делится ---------- */
  // Полный круг 7,6 с и остановка ровно в виде обычного логотипа. Цвета знака — из brand.json (logo_colors).
  function animatedMark(host, onEnd, onFrame) {
    var LC = (H.brand && H.brand.brand && H.brand.brand.logo_colors) || {};
    var GOLD = LC.gear || "#c9a24a", TEAL = LC.circuit || "#2bb3c4", T = 7600;
    var old = host.querySelector("svg.mark, svg.brand-mark") || host.querySelector("svg");
    var svg = s("svg", { viewBox: "0 0 100 100", class: old.getAttribute("class") || "mark", "aria-hidden": "true", focusable: "false" });
    ["x", "y", "width", "height"].forEach(function (a) { if (old.hasAttribute(a)) svg.setAttribute(a, old.getAttribute(a)); });
    old.parentNode.replaceChild(svg, old);
    var defs = s("defs", {}, svg), id = uid();
    var gClip = s("rect", { x: 0, y: 0, width: 100, height: 100 }, s("clipPath", { id: "mg" + id }, defs));
    var cClip = s("rect", { x: 0, y: 0, width: 100, height: 100 }, s("clipPath", { id: "mc" + id }, defs));
    var gear = s("path", { fill: GOLD }, s("g", { "clip-path": "url(#mg" + id + ")" }, svg));
    var circ = s("g", {}, s("g", { "clip-path": "url(#mc" + id + ")" }, svg));
    s("circle", { cx: 50, cy: 50, r: 30, fill: "none", stroke: TEAL, "stroke-width": 5 }, circ);
    var TR = ["M50 36 H64 L70 30", "M50 50 H72", "M50 64 H62 L68 70", "M50 36 H36 L30 30", "M50 50 H28", "M50 64 H38 L32 70"];
    var traces = TR.map(function (d) { return s("path", { d: d, fill: "none", stroke: TEAL, "stroke-width": 4, "stroke-linecap": "round", "stroke-linejoin": "round" }, circ); });
    [[71, 29], [74, 50], [69, 71], [29, 29], [26, 50], [31, 71]].forEach(function (e) { s("circle", { cx: e[0], cy: e[1], r: 4, fill: TEAL }, circ); });
    var wave = s("circle", { cx: 50, cy: 50, r: 9, fill: "none", stroke: TEAL, "stroke-width": 2, opacity: 0 }, circ);
    var dots = traces.map(function () { return s("circle", { r: 2.6, fill: "#ffffff", stroke: TEAL, "stroke-width": 1.2, opacity: 0 }, circ); });
    var lens = traces.map(function (p) { return p.getTotalLength(); });
    s("circle", { cx: 50, cy: 50, r: 9, fill: "currentColor" }, svg);
    s("circle", { cx: 50, cy: 50, r: 3.5, fill: GOLD }, svg);
    function gearPath(h) {
      var d = "";
      for (var i = 0; i <= 360; i += 3) {
        var r = 30 + ((i % 30) < 14 ? 7 * h : 0), a = (90 + i) * Math.PI / 180;
        d += (i ? "L" : "M") + (50 + r * Math.cos(a)).toFixed(2) + " " + (50 - r * Math.sin(a)).toFixed(2);
      }
      return d + "Z";
    }
    function seg(u, a, b) { return Math.max(0, Math.min(1, (u - a) / (b - a))); }
    // u 0…1: 0–0,22 шестерёнка крутится; 0,22–0,42 зубцы уходят — плата; 0,42–0,74 сигналы; 0,68–0,86 знак делится пополам
    function draw(u) {
      var rot = "rotate(" + (720 * (1 - Math.pow(1 - u, 3))).toFixed(2) + " 50 50)";
      gear.setAttribute("transform", rot);
      circ.setAttribute("transform", rot);
      var g = u < 0.68 ? 1 - seg(u, 0.22, 0.42) : seg(u, 0.68, 0.86);
      gear.setAttribute("d", gearPath(Math.max(g, 0.001)));
      gear.setAttribute("opacity", g);
      gClip.setAttribute("width", u < 0.68 ? 100 : 50);
      circ.setAttribute("opacity", seg(u, 0.22, 0.42));
      var cx = 50 * seg(u, 0.68, 0.86);
      cClip.setAttribute("x", cx);
      cClip.setAttribute("width", 100 - cx);
      var sp = seg(u, 0.42, 0.74), live = sp > 0 && sp < 1, w = (sp * 2) % 1;
      wave.setAttribute("r", 9 + 26 * w);
      wave.setAttribute("opacity", live ? (1 - w) * 0.8 : 0);
      traces.forEach(function (p, i) {
        var k = (sp * 2 - i * 0.06 + 1) % 1, pt = p.getPointAtLength(lens[i] * k);
        dots[i].setAttribute("cx", pt.x);
        dots[i].setAttribute("cy", pt.y);
        dots[i].setAttribute("opacity", live ? Math.sin(Math.PI * k) : 0);
      });
      if (onFrame) onFrame(u);
    }
    var raf = null, t0 = null, done = null;
    // Большой знак сообщает странице «собрался» (круг закончен) и «начал заново»: по этим событиям появляется надпись (js/logo-word.js)
    function announce(finished) {
      if (done === finished) return;
      done = finished;
      host.dispatchEvent(new CustomEvent(finished ? "homensai-logo-formed" : "homensai-logo-reset", { bubbles: true }));
    }
    function frame(now) {
      if (M.paused) { raf = null; draw(1); announce(true); return; }        // общая пауза: сразу обычный знак
      if (t0 == null) t0 = now;
      var u = Math.min(1, (now - t0) / T);
      draw(u);
      raf = u < 1 ? requestAnimationFrame(frame) : null;
      if (u >= 1) { announce(true); if (onEnd) onEnd(); }
    }
    draw(1);
    return {
      play: function () { if (reduce || M.paused) { draw(1); announce(true); return; } if (raf) cancelAnimationFrame(raf); t0 = null; draw(0); announce(false); raf = requestAnimationFrame(frame); },
      still: function () { if (raf) cancelAnimationFrame(raf); raf = null; draw(1); announce(true); },
      busy: function () { return !!raf; }
    };
  }

  // data-dia="mark": один раз при появлении (data-autoplay) и снова при наведении; data-loop — по кругу с паузой 1,6 с,
  // кнопки [data-mark-play] / [data-mark-pause] в пределах [data-mark-scope] управляют им
  function markHost(host) {
    var loop = host.hasAttribute("data-loop"), wait = null, paused = false, m, started = false;
    m = animatedMark(host, function () { if (loop && !paused) wait = setTimeout(function () { m.play(); }, 1600); });
    if (loop || host.hasAttribute("data-autoplay")) onVisible(host, function (v) { if (v && !started) { started = true; m.play(); } });
    if (!loop) host.addEventListener("mouseenter", function () { if (!m.busy()) m.play(); });
    var scope = host.closest("[data-mark-scope]") || document;
    var playBtn = scope.querySelector("[data-mark-play]"), pauseBtn = scope.querySelector("[data-mark-pause]");
    if (playBtn) playBtn.addEventListener("click", function () { paused = false; clearTimeout(wait); m.play(); });
    if (pauseBtn) pauseBtn.addEventListener("click", function () { paused = true; clearTimeout(wait); m.still(); });
    return m;
  }

  /* ---------- 11. Знак с выносками, как на чертеже: «Механика» и «ИТ» меняются местами, затем сливаются в одну ---------- */
  function heroMark(stage) {
    var co = { hw: stage.querySelector(".co-hw"), it: stage.querySelector(".co-it") };
    var SLOT = { top: 0, bottom: 200 }, state = "";
    function place(hwSlot, itSlot, hot) {
      var key = hwSlot + itSlot + hot;
      if (key === state) return;
      state = key;
      co.hw.style.transform = "translateY(" + SLOT[hwSlot] + "px)";
      co.it.style.transform = "translateY(" + SLOT[itSlot] + "px)";
      co.hw.classList.toggle("hot", hot === "hw" || hot === "both");
      co.it.classList.toggle("hot", hot === "it" || hot === "both");
    }
    function frame(u) {
      var join = u >= 0.86;
      stage.classList.toggle("joined", join);
      if (join) return;
      if (u < 0.22) place("top", "bottom", "hw");
      else if (u < 0.68) { var sw = Math.floor((u - 0.22) / 0.075) % 2 === 1; place(sw ? "bottom" : "top", sw ? "top" : "bottom", u < 0.42 ? "hw" : "it"); }
      else place("top", "bottom", "both");
    }
    var m = animatedMark(stage, null, frame);
    frame(1);
    if (reduce) return m;
    var started = false;
    onVisible(stage, function (v) { if (v && !started) { started = true; m.play(); } });
    stage.addEventListener("click", function () { if (!m.busy()) m.play(); });
    return m;
  }

  /* ---------- 12. Канат: две нити — железо (золото) и софт (бирюза) — идут раздельно и скручиваются в один трос ---------- */
  // В конце трос раскрывается в кольцо, в нём знак становится роботом (js/robot.js), под ним меняется имя.
  function rope(root, o) {
    var canvas = root.querySelector(".dia-canvas");
    var replay = root.querySelector(".dia-replay");
    var logo = root.querySelector(".rope-logo");
    var EV = o.events || [
      { u: 0.04, s: "sw", row: 0, y: "1993", t: L("Systems engineering · first AI in Lisp", "Системная инженерия · первый ИИ на Lisp", "Systemtechnik · erste KI in Lisp") },
      { u: 0.15, s: "sw", row: 1, y: "1997–98", t: L("Distributed computing · cryptographic key search", "Распределённые вычисления · поиск ключа", "Verteiltes Rechnen · kryptografische Schlüsselsuche") },
      { u: 0.25, s: "sw", row: 0, y: "2000", t: L("Web code", "Веб-код", "Web-Code") },
      { u: 0.31, s: "hw", row: 0, y: "2002", t: L("Machinery · lines for cellular concrete", "Механизмы · линии ячеистого бетона", "Maschinenbau · Anlagen für Zellbeton") },
      { u: 0.45, s: "hw", row: 0, y: "2008", t: L("Controllers: dosing, weighing, control logic", "Контроллеры: дозирование, взвешивание, логика", "Steuerungen: Dosieren, Wiegen, Steuerungslogik") },
      { u: 0.58, s: "both", row: 0, y: "2010", t: L("3D CAD — code shapes steel", "3D САПР — код формирует металл", "3D-CAD — Code formt Stahl") },
      { u: 0.71, s: "both", row: 1, y: "2018", t: L("GPU rigs — computer hardware runs crypto", "GPU-фермы — железо считает крипту", "GPU-Rigs — Rechner-Hardware für Krypto") },
      { u: 0.83, s: "both", row: 0, y: L("Today", "Сегодня", "Heute"), t: L("Local AI on my own hardware", "Локальный ИИ на моём железе", "Lokale KI auf eigener Hardware") }
    ];
    // U0/UEND — базовая разметка; на широком экране сжимаются в K раз, чтобы осталось место для кольца
    var U0B = 0.47, UEB = 0.9, U0 = U0B, UEND = UEB, K = 1, DUR = o.duration || 6500;
    var t = 0, running = false, last = null, started = false, G, clipRect, labels;
    var roboHost = logo && logo.querySelector(".robo");
    var robo = roboHost && H.robot ? H.robot.tvRobot(roboHost) : { play: function (cb) { if (cb) cb(); }, reset: function () {} };
    var shown = false;
    var after = o.after ? document.querySelector(o.after) : null;   // блок, который появляется после подмигивания робота
    var nameSwap = logo && logo.querySelector(".name-swap");
    if (nameSwap) nameSwap.setAttribute("data-hold", "");          // имя начинает меняться только когда робот на месте
    function wink() { if (after) after.classList.add("on"); }

    function geom(W) {
      var g;
      if (W >= 760) {
        var pad = 30, axis = 205, len = W - 2 * pad, R = Math.round(Math.min(84, Math.max(58, len * 0.075)));
        UEND = (len - 2 * R - 4) / len; K = UEND / UEB; U0 = U0B * K;
        g = { wide: true, W: W, H: 430, A0: 80, r: 11, w: 6, R: R, x0: pad, len: len, P: function (u, off) { return { x: pad + u * len, y: axis + off }; } };
        g.E = g.P(UEND, 0);
        g.C = { x: g.E.x + R, y: g.E.y };
        g.end = g.C.x + R + g.w;
        return g;
      }
      UEND = UEB; K = 1; U0 = U0B;
      var top = 24, lenv = 920, ax = 46, Rt = Math.round(Math.max(56, Math.min(78, W / 2 - 24)));
      g = { wide: false, W: W, A0: 24, r: 8, w: 5, R: Rt, x0: top, len: lenv, P: function (u, off) { return { x: ax + off, y: top + u * lenv }; } };
      g.E = g.P(UEND, 0);
      g.C = { x: Math.max(W / 2, Rt + 16), y: g.E.y + 50 + Rt };
      g.H = Math.round(g.C.y + Rt + 120);
      g.end = g.C.y + Rt + g.w;
      return g;
    }
    // Нити расходятся до U0, затем сходятся и закручиваются всё туже (5,5 оборота)
    function shape(u) {
      if (u <= U0) return { a: G.A0, ph: 0 };
      var q = (u - U0) / (UEND - U0), k = Math.min(1, q / 0.35);
      k = k * k * (3 - 2 * k);
      return { a: G.A0 + (G.r - G.A0) * k, ph: Math.PI * 2 * 5.5 * Math.pow(q, 1.25) };
    }
    function build() {
      canvas.replaceChildren();
      G = geom(Math.max(300, canvas.clientWidth));
      var svg = s("svg", { viewBox: "0 0 " + G.W + " " + G.H, class: "rope-svg", role: "img",
        "aria-label": o.label || L("Two strands, hardware and software, run apart from the 1990s and twist into one rope", "Две нити, железо и код, идут раздельно с 1990-х и скручиваются в один трос", "Zwei Stränge, Maschinenbau und Software, laufen seit den 1990ern getrennt und verdrehen sich zu einem Seil") }, canvas);
      var clipId = "rclip-" + uid();
      clipRect = s("rect", { x: 0, y: 0, width: 0, height: 0 }, s("clipPath", { id: clipId }, s("defs", {}, svg)));
      var g = s("g", { "clip-path": "url(#" + clipId + ")" }, svg);
      // Короткие отрезки, отсортированные от дальнего к ближнему, дают честное «над/под» на каждом пересечении
      var N = 320, pieces = [], prev = null;
      for (var i = 0; i <= N; i++) {
        var u = UEND * i / N, sh = shape(u), c = Math.cos(sh.ph);
        var cur = { hw: G.P(u, -sh.a * c), sw: G.P(u, sh.a * c), z: Math.sin(sh.ph) };
        if (prev) { var zm = (prev.z + cur.z) / 2; pieces.push({ k: "hw", a: prev.hw, b: cur.hw, z: zm }); pieces.push({ k: "sw", a: prev.sw, b: cur.sw, z: -zm }); }
        prev = cur;
      }
      pieces.sort(function (p, q) { return p.z - q.z; });
      pieces.forEach(function (p) {
        var d = "M" + p.a.x.toFixed(1) + " " + p.a.y.toFixed(1) + " L" + p.b.x.toFixed(1) + " " + p.b.y.toFixed(1);
        if (p.z > 0.05) s("path", { d: d, class: "r-gap", "stroke-width": G.w + 4 }, g);
        s("path", { d: d, class: "r-" + p.k, "stroke-width": G.w }, g);
      });
      var C = G.C, R = G.R, E = G.E, f = function (n) { return n.toFixed(1); };
      if (G.wide) {
        s("path", { d: "M" + f(C.x - R) + " " + f(C.y) + " A" + R + " " + R + " 0 0 1 " + f(C.x + R) + " " + f(C.y), class: "r-hw", "stroke-width": G.w }, g);
        s("path", { d: "M" + f(C.x - R) + " " + f(C.y) + " A" + R + " " + R + " 0 0 0 " + f(C.x + R) + " " + f(C.y), class: "r-sw", "stroke-width": G.w }, g);
      } else {
        var top = C.y - R, lead = function (dx) { return "M" + f(E.x + dx) + " " + f(E.y) + " C" + f(E.x + dx) + " " + f(E.y + 34) + " " + f(C.x + dx) + " " + f(top - 34) + " " + f(C.x + dx) + " " + f(top); };
        s("path", { d: lead(3), class: "r-sw", "stroke-width": G.w }, g);
        s("path", { d: lead(-3), class: "r-hw", "stroke-width": G.w }, g);
        s("path", { d: "M" + f(C.x) + " " + f(top) + " A" + R + " " + R + " 0 0 1 " + f(C.x) + " " + f(C.y + R), class: "r-sw", "stroke-width": G.w }, g);
        s("path", { d: "M" + f(C.x) + " " + f(top) + " A" + R + " " + R + " 0 0 0 " + f(C.x) + " " + f(C.y + R), class: "r-hw", "stroke-width": G.w }, g);
      }
      // Подписи над и под тросом; если соседняя подпись на той же стороне ближе 140 px, эта уходит на ряд дальше (56 px)
      var placed = { up: [], down: [] }, GAPX = 140, ROW = 56;
      labels = EV.map(function (ev) {
        var lab = el("div"), off, dir, row = ev.row || 0, x = G.P(ev.u * K, 0).x;
        if (!G.wide) { off = G.A0 + 18; dir = "side"; }
        else {
          var a = Math.max(shape(ev.u * K).a, shape(Math.max(0, ev.u * K - 0.07)).a) + G.w + 16;
          dir = ev.s === "hw" ? "up" : ev.s === "sw" ? "down" : (ev.row ? "down" : "up");
          var base = ev.s === "both" ? a : G.A0 + 14;
          row = ev.s === "both" ? 0 : (ev.s === "sw" ? row : 0);
          while (placed[dir].some(function (q) { return q.row === row && Math.abs(q.x - x) < GAPX; })) row++;
          placed[dir].push({ x: x, row: row });
          off = (base + row * ROW) * (dir === "up" ? -1 : 1);
        }
        var p = G.P(ev.u * K, off);
        lab.className = "r-label r-" + ev.s + " " + dir;
        lab.style.left = (p.x / G.W * 100) + "%";
        lab.style.top = (p.y / G.H * 100) + "%";
        el("b", "mono", ev.y, lab);
        el("span", null, ev.t, lab);
        canvas.appendChild(lab);
        return { el: lab, u: ev.u * K };
      });
      if (logo) {                                               // знак (а затем робот) живёт внутри кольца
        logo.classList.add("ring");
        logo.classList.toggle("wide", G.wide);
        logo.classList.toggle("tall", !G.wide);
        logo.style.left = (C.x / G.W * 100) + "%";
        logo.style.top = (C.y / G.H * 100) + "%";
        logo.style.setProperty("--rr", R + "px");
        logo.style.setProperty("--rs", Math.round(R * 2.4) + "px");
        canvas.appendChild(logo);
      }
      render();
    }
    function render() {
      // проявление идёт дальше конца троса, чтобы кольцо замкнулось последним
      var edge = G.x0 + t * (G.end - G.x0), ur = (edge - G.x0) / G.len;
      if (G.wide) { clipRect.setAttribute("width", edge); clipRect.setAttribute("height", G.H); }
      else { clipRect.setAttribute("width", G.W); clipRect.setAttribute("height", edge); }
      labels.forEach(function (l) { l.el.classList.toggle("on", l.u <= ur + 0.005); });
      if (logo) logo.classList.toggle("show", t >= 1);
      if (t >= 1 && !shown) { shown = true; robo.play(wink); if (nameSwap) nameSwap.removeAttribute("data-hold"); }
      if (t < 1 && shown) { shown = false; robo.reset(); if (nameSwap) { nameSwap.setAttribute("data-hold", ""); nameSwap.classList.remove("alt", "inc"); } }
    }
    // Реальное прошедшее время: в фоновой вкладке рисунок не растягивается
    function frame(now) {
      if (!running) return;
      if (last == null) last = now;
      t = Math.min(1, (now - last) / DUR);
      render();
      if (t < 1) requestAnimationFrame(frame); else running = false;
    }
    function play() { t = 0; last = null; render(); if (!running) { running = true; requestAnimationFrame(frame); } }
    if (logo) logo.addEventListener("click", function () { if (t >= 1) robo.play(); });
    build();
    onResize(canvas, build);
    if (replay) replay.addEventListener("click", function () { if (reduce) { t = 1; render(); } else play(); });
    if (reduce) { t = 1; render(); return; }
    onVisible(root, function (v) { if (v && !started) { started = true; play(); } });
  }

  /* ---------- 13. Отдельный робот: один раз при появлении, щелчок и кнопка [data-robot-play] повторяют ---------- */
  function robot(host) {
    if (!H.robot) throw new Error("HomenS.robot не найден: подключите js/robot.js для data-dia=\"robot\"");
    var r = H.robot.tvRobot(host), done = false;
    onVisible(host, function (v) { if (v && !done) { done = true; r.play(); } });
    host.addEventListener("click", function () { r.play(); });
    var fig = host.closest("figure");
    var btn = fig && fig.querySelector("[data-robot-play]");
    if (btn) { btn.hidden = false; btn.addEventListener("click", function () { done = true; r.play(); }); }
    return r;
  }

  var KINDS = {
    "hero-mark": heroMark, mark: markHost, rope: rope, robot: robot, aibiz: aiBusiness, worlds: worlds, caesar: caesar,
    gap: gap, project: projectCycle, shift: shift, steps: stepper, cycle: growthCycle, loop: verifyLoop
  };
  function mount(node, kind, options) {
    kind = kind || node.getAttribute("data-dia");
    if (!KINDS[kind]) throw new Error("Неизвестный вид схемы: " + kind);
    if (node.__dia) return node.__dia;
    node.__dia = KINDS[kind](node, options || {}) || true;
    return node.__dia;
  }
  H.motionDiagrams = { mount: mount, kinds: Object.keys(KINDS), animatedMark: animatedMark };
  // Порядок как на сайте: сначала знаки (их SVG заменяется), затем остальное
  function start() {
    ["hero-mark", "mark", "rope", "robot", "aibiz", "worlds", "caesar", "gap", "project", "shift", "steps", "cycle", "loop"].forEach(function (k) {
      document.querySelectorAll('[data-dia="' + k + '"]:not([data-manual])').forEach(function (n) { mount(n, k); });
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
