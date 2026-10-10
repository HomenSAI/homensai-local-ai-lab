// HomenS.AI Style · © 2026 Serhii Khomenko · https://homensai.com/ · https://github.com/HomenSAI · https://www.linkedin.com/in/serhii-khomenko-homensai/
// «Вселенная»: анимация на холсте «От сегодня к звёздам» (перенесена с homensai.com, vision.js 2.02).
// Три масштаба на логарифмической шкале времени: Солнечная система → соседние звёзды → Галактика. Иллюстрация, не прогноз.
// Цвета — токены --cosmos-* из css/tokens.css, шрифт — --font-mono. Разметка и правила — docs/MOTION.md, раздел 3.
// Подключать после js/motion.js. Каждый блок .cosmos на странице запускается сам; вручную — HomenS.cosmos.mount(блок).
(function () {
  "use strict";
  var H = window.HomenS = window.HomenS || {};
  var M = H.motion || { reduced: false, paused: false, lang: "ru" };
  var LANG = M.lang || "ru";

  var TEXT = {
    ru: { today: "Сегодня · 2026", years: " лет", myears: " млн лет", loc: "ru-RU", earth: "Земля · старт", sun: "Солнце", ly: "св. лет", gal: "≈ 100 000 световых лет",
      solar: "Солнечная система", stars: "Соседние звёзды", galaxy: "Галактика", planets: "Достигнуто планет: ", of: " из ", start: " · Всё начинается с Земли", starsReached: "Достигнуто звёзд: ", shown: " показано", galReached: "Пройдено по Галактике (иллюстрация): ", play: "Пуск", pause: "Пауза", replay: "Ещё раз",
      pn: ["Меркурий", "Венера", "Земля", "Марс", "Юпитер", "Сатурн", "Уран", "Нептун"] },
    en: { today: "Today · 2026", years: " years", myears: " million years", loc: "en-US", earth: "Earth · start", sun: "Sun", ly: "ly", gal: "≈ 100 000 light-years",
      solar: "Solar system", stars: "Neighbouring stars", galaxy: "The Galaxy", planets: "Planets reached: ", of: " of ", start: " · Earth is where it starts", starsReached: "Stars reached: ", shown: " shown", galReached: "Galaxy crossed (illustration): ", play: "Play", pause: "Pause", replay: "Replay",
      pn: ["Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"] },
    de: { today: "Heute · 2026", years: " Jahre", myears: " Millionen Jahre", loc: "de-DE", earth: "Erde · Start", sun: "Sonne", ly: "Lj", gal: "≈ 100.000 Lichtjahre",
      solar: "Sonnensystem", stars: "Nachbarsterne", galaxy: "Die Galaxie", planets: "Planeten erreicht: ", of: " von ", start: " · Hier beginnt es: die Erde", starsReached: "Sterne erreicht: ", shown: " gezeigt", galReached: "Galaxie durchquert (Veranschaulichung): ", play: "Abspielen", pause: "Pause", replay: "Wiederholen",
      pn: ["Merkur", "Venus", "Erde", "Mars", "Jupiter", "Saturn", "Uranus", "Neptun"] }
  };

  function rng(seed) { return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; var t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }
  function sm(x) { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); }
  // «#rrggbb» + прозрачность → rgba(); полупрозрачные оттенки строятся из токенов, новых цветов не появляется
  function A(hex, a) { var n = parseInt(hex.slice(1), 16); return "rgba(" + (n >> 16 & 255) + "," + (n >> 8 & 255) + "," + (n & 255) + "," + a + ")"; }

  function mount(box) {
    if (box.__cosmos) return box.__cosmos;
    var cv = box.querySelector("canvas");
    if (!cv || !cv.getContext) return null;
    var ctx = cv.getContext("2d");
    var T = TEXT[box.getAttribute("data-lang") || LANG] || TEXT.ru;
    var W = 960, H = 540, CX = W / 2, CY = H / 2;
    var DURATION = Number(box.getAttribute("data-duration")) || 44;   // секунд на весь показ
    var SPAN = 8;                                                     // прошло = 10^(p*SPAN) − 1 → 0 … 100 млн лет
    var B1 = 3 / 8, B2 = 6 / 8;                                       // границы сцен по p
    var reduce = M.reduced;

    var css = getComputedStyle(box);
    function tok(n) { return css.getPropertyValue("--cosmos-" + n).trim() || "#888888"; }
    var C = { bg: tok("bg"), grid: tok("grid"), ink: tok("ink"), mute: tok("mute"), cy: tok("teal"), gold: tok("gold"), earth: tok("earth") };
    var FONT = css.getPropertyValue("--font-mono").trim() || "monospace";

    var rand = rng(2026);   // одно и то же зерно — звёзды всегда на тех же местах
    var planets = [
      { r: 36, c: tok("mercury"), s: 3, th: 0.35 },
      { r: 58, c: tok("venus"), s: 4, th: 0.25 },
      { r: 82, c: C.earth, s: 4.5, th: 0 },
      { r: 106, c: tok("mars"), s: 3.5, th: 0.08 },
      { r: 142, c: tok("jupiter"), s: 7, th: 0.45 },
      { r: 178, c: tok("saturn"), s: 6, th: 0.6 },
      { r: 212, c: tok("uranus"), s: 5, th: 0.75 },
      { r: 248, c: tok("neptune"), s: 5, th: 0.88 }
    ];
    planets.forEach(function (p) { p.a0 = rand() * 6.283; p.w = 0.55 * Math.pow(82 / p.r, 1.5); });

    var i, bg = []; for (i = 0; i < 160; i++) bg.push({ x: rand() * W, y: rand() * H, a: 0.15 + rand() * 0.5, r: rand() < 0.1 ? 1.3 : 0.7 });

    var stars = [];
    for (i = 0; i < 150; i++) {
      var d = 250 * Math.sqrt(rand()), th = rand() * 6.283;
      stars.push({ x: d * Math.cos(th), y: d * Math.sin(th), q: (d / 250) * (0.9 + 0.2 * rand()), r: 1.4 + rand() * 1.6 });
    }
    stars.sort(function (a, b) { return a.q - b.q; });
    stars.forEach(function (s, k) {                       // родитель — ближайшая звезда, достигнутая раньше (или Солнце)
      var best = { x: 0, y: 0 }, bd = Math.hypot(s.x, s.y);
      for (var j = 0; j < k; j++) { var dd = Math.hypot(s.x - stars[j].x, s.y - stars[j].y); if (dd < bd) { bd = dd; best = stars[j]; } }
      s.p = best;
    });

    var gal = [], SUN = { r: 170, th: 0.9 };
    for (i = 0; i < 760; i++) {
      var t = Math.pow(rand(), 0.75), arm = i % 2, rr = 22 + t * 228, tt = arm * Math.PI + t * 3.4 + (rand() - 0.5) * 0.55;
      gal.push({ x: rr * Math.cos(tt), y: rr * Math.sin(tt), r: 0.7 + rand() * 1.1 });
    }
    for (i = 0; i < 140; i++) { var a = rand() * 6.283, g = 40 * Math.abs(rand() + rand() - 1) + 4; gal.push({ x: g * Math.cos(a), y: g * Math.sin(a), r: 0.8 + rand() * 1.2 }); }
    SUN.x = SUN.r * Math.cos(SUN.th); SUN.y = SUN.r * Math.sin(SUN.th);

    /* ---------- помощники рисования ---------- */
    function arrow(x1, y1, x2, y2, size, col, lw) {
      var an = Math.atan2(y2 - y1, x2 - x1);
      ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineWidth = lw || 1;
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x2, y2); ctx.lineTo(x2 - size * Math.cos(an - 0.4), y2 - size * Math.sin(an - 0.4)); ctx.lineTo(x2 - size * Math.cos(an + 0.4), y2 - size * Math.sin(an + 0.4)); ctx.closePath(); ctx.fill();
    }
    function label(txt, x, y, col, size, align) { ctx.font = (size || 11) + "px " + FONT; ctx.fillStyle = col || C.mute; ctx.textAlign = align || "left"; ctx.fillText(txt, x, y); }
    function glow(x, y, r, col) { var gr = ctx.createRadialGradient(x, y, 0, x, y, r * 3); gr.addColorStop(0, col); gr.addColorStop(1, "rgba(0,0,0,0)"); ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(x, y, r * 3, 0, 6.283); ctx.fill(); }

    /* ---------- сцены: рисуют вокруг (0,0) = центр ---------- */
    function sceneSolar(u, clk) {
      var pos = planets.map(function (p) { var an = p.a0 + clk * p.w; return { x: p.r * Math.cos(an), y: p.r * Math.sin(an) }; });
      ctx.lineWidth = 1;
      planets.forEach(function (p) { ctx.strokeStyle = A(C.grid, 0.16); ctx.beginPath(); ctx.arc(0, 0, p.r, 0, 6.283); ctx.stroke(); });
      glow(0, 0, 9, A(C.gold, 0.55)); ctx.fillStyle = C.gold; ctx.beginPath(); ctx.arc(0, 0, 9, 0, 6.283); ctx.fill();
      var E = pos[2];
      planets.forEach(function (p, k) {
        var P = pos[k], on = u >= p.th;
        if (k !== 2 && on) {                                    // луч от Земли «как на чертеже»
          var gr = sm((u - p.th) / 0.07), tx = E.x + (P.x - E.x) * gr, ty = E.y + (P.y - E.y) * gr;
          ctx.setLineDash([5, 4]); arrow(E.x, E.y, tx, ty, 7, A(C.cy, 0.75), 1); ctx.setLineDash([]);
        }
        ctx.fillStyle = p.c; ctx.beginPath(); ctx.arc(P.x, P.y, p.s, 0, 6.283); ctx.fill();
        if (on) {
          var pul = 1 + 0.25 * Math.sin(clk * 3 + k);
          ctx.strokeStyle = C.cy; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(P.x, P.y, p.s + 5 * pul, 0, 6.283); ctx.stroke();
          if (k !== 2) label(T.pn[k], P.x + p.s + 8, P.y - 6, C.ink, 10);
        }
      });
      label(T.earth, E.x + 10, E.y + 20, C.ink, 11);
      if (u > 0.9) {                                            // первые зонды покидают систему
        var k2 = sm((u - 0.9) / 0.1);
        for (var j = 0; j < 5; j++) { var an = clk * 0.05 + j * 1.2566, r0 = 255, r1 = 255 + 40 * k2; ctx.setLineDash([]); arrow(r0 * Math.cos(an), r0 * Math.sin(an), r1 * Math.cos(an), r1 * Math.sin(an), 7, A(C.gold, 0.85), 1.3); }
      }
    }

    function sceneStars(u, clk) {
      ctx.save(); ctx.rotate(clk * 0.03);
      [83, 166, 250].forEach(function (r) { ctx.strokeStyle = A(C.grid, 0.14); ctx.setLineDash([2, 5]); ctx.beginPath(); ctx.arc(0, 0, r, 0, 6.283); ctx.stroke(); ctx.setLineDash([]); });
      var f = u * 1.12, n = 0;
      stars.forEach(function (s) {
        if (f >= s.q) {
          n++;
          var gr = sm((f - s.q) / 0.08);
          arrow(s.p.x, s.p.y, s.p.x + (s.x - s.p.x) * gr, s.p.y + (s.y - s.p.y) * gr, 5, A(C.cy, 0.45), 0.8);
          ctx.fillStyle = C.cy; ctx.beginPath(); ctx.arc(s.x, s.y, s.r + 0.6, 0, 6.283); ctx.fill();
          if (gr < 1) { ctx.strokeStyle = A(C.cy, 0.7 * (1 - gr)); ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(s.x, s.y, s.r + 3 + 12 * gr, 0, 6.283); ctx.stroke(); }
        } else { ctx.fillStyle = A(C.ink, 0.55); ctx.beginPath(); ctx.arc(s.x, s.y, s.r * 0.75, 0, 6.283); ctx.fill(); }
      });
      glow(0, 0, 6, A(C.gold, 0.55)); ctx.fillStyle = C.gold; ctx.beginPath(); ctx.arc(0, 0, 5, 0, 6.283); ctx.fill();
      ctx.restore();
      label(T.sun, 10, 18, C.ink, 11);
      ["25 ", "50 ", "75 "].forEach(function (t, k) { label(t + T.ly, 83 * (k + 1) * 0.7071 + 4, -83 * (k + 1) * 0.7071 - 4, C.mute, 10); });
      sceneStars.n = n;
    }

    function sceneGalaxy(u, clk) {
      var TILT = 0.55, rot = clk * 0.02, cr = Math.cos(rot), sr = Math.sin(rot);
      function pr(x, y) { return { x: x * cr - y * sr, y: (x * sr + y * cr) * TILT }; }
      var sx = SUN.x, sy = SUN.y, F = u * 440, n = 0;
      var halo = ctx.createRadialGradient(0, 0, 0, 0, 0, 120); halo.addColorStop(0, A(C.gold, 0.28)); halo.addColorStop(1, "rgba(0,0,0,0)"); ctx.fillStyle = halo; ctx.beginPath(); ctx.ellipse(0, 0, 120, 120 * TILT, 0, 0, 6.283); ctx.fill();
      gal.forEach(function (s) {
        var on = Math.hypot(s.x - sx, s.y - sy) < F, p = pr(s.x, s.y);
        if (on) { n++; ctx.fillStyle = A(C.cy, 0.95); ctx.beginPath(); ctx.arc(p.x, p.y, s.r + 0.5, 0, 6.283); ctx.fill(); }
        else { ctx.fillStyle = A(C.ink, 0.38); ctx.beginPath(); ctx.arc(p.x, p.y, s.r * 0.8, 0, 6.283); ctx.fill(); }
      });
      var S = pr(sx, sy);
      if (F > 6) {                                              // расширяющаяся граница на плоскости Галактики
        ctx.save(); ctx.beginPath(); ctx.strokeStyle = A(C.gold, 0.6); ctx.lineWidth = 1; ctx.setLineDash([4, 4]);
        for (var k = 0; k <= 64; k++) { var th2 = k / 64 * 6.283, q = pr(sx + F * Math.cos(th2), sy + F * Math.sin(th2)); if (k) ctx.lineTo(q.x, q.y); else ctx.moveTo(q.x, q.y); }
        ctx.stroke(); ctx.setLineDash([]); ctx.restore();
      }
      glow(S.x, S.y, 4, A(C.gold, 0.7)); ctx.fillStyle = C.gold; ctx.beginPath(); ctx.arc(S.x, S.y, 3.5, 0, 6.283); ctx.fill();
      label(T.sun, S.x + 8, S.y - 8, C.ink, 11);
      arrow(-250, 262 * TILT + 20, 250, 262 * TILT + 20, 6, A(C.grid, 0.35), 1); arrow(250, 262 * TILT + 20, -250, 262 * TILT + 20, 6, A(C.grid, 0.35), 1);
      label(T.gal, 0, 262 * TILT + 36, C.mute, 10, "center");
      sceneGalaxy.pct = Math.round(100 * n / gal.length);
    }

    var SCENES = [{ fn: sceneSolar, name: T.solar }, { fn: sceneStars, name: T.stars }, { fn: sceneGalaxy, name: T.galaxy }];

    /* ---------- состояние и управление ---------- */
    var p = 0, playing = false, last = 0, clk = 0, visible = true, done = false;
    var q = function (k) { return box.querySelector("[data-cosmos-" + k + "]"); };
    var elCount = q("count"), elSub = q("sub"), elStat = q("stat"), btn = q("play"), rewind = q("restart"), range = q("range");
    var pills = box.querySelectorAll("[data-cosmos-stage] > *");
    pills.forEach(function (el, k) { if (!el.textContent) el.textContent = SCENES[k] ? SCENES[k].name : ""; });

    function fmt(e) {
      if (e < 1) return T.today;
      if (e < 1000) return "+" + Math.round(e).toLocaleString(T.loc) + T.years;
      if (e < 1e6) return "+" + (Math.round(e / 10) * 10).toLocaleString(T.loc) + T.years;
      var m = e / 1e6 >= 10 ? String(Math.round(e / 1e6)) : (e / 1e6).toFixed(1);
      return "+" + (T.loc === "en-US" ? m : m.replace(".", ",")) + T.myears;
    }

    // Переход между сценами: последние 10 % сцены она гаснет и уменьшается до 55 %, следующая проявляется из увеличенной (160 % → 100 %)
    function frame() {
      var dpr = cv.width / W;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
      ctx.lineWidth = 1; ctx.strokeStyle = A(C.grid, 0.05);
      for (var x = 0; x <= W; x += 60) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
      for (var y = 0; y <= H; y += 60) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
      bg.forEach(function (s) { ctx.fillStyle = A(C.ink, s.a); ctx.fillRect(s.x, s.y, s.r, s.r); });

      var st = p < B1 ? 0 : p < B2 ? 1 : 2, a0 = [0, B1, B2][st], a1 = [B1, B2, 1][st], u = clamp((p - a0) / (a1 - a0), 0, 1);
      var k = st < 2 ? sm((u - 0.9) / 0.1) : 0;
      function draw(n, uu, alpha, scale) { ctx.save(); ctx.globalAlpha = alpha; ctx.translate(CX, CY); ctx.scale(scale, scale); SCENES[n].fn(uu, clk); ctx.restore(); }
      draw(st, u, 1 - k, 1 - 0.45 * k);
      if (k > 0) draw(st + 1, 0, k, 1.6 - 0.6 * k);

      // уголки рамки, как на чертёжном листе
      ctx.globalAlpha = 1; ctx.strokeStyle = A(C.grid, 0.35); ctx.lineWidth = 1;
      [[12, 12, 1, 1], [W - 12, 12, -1, 1], [12, H - 12, 1, -1], [W - 12, H - 12, -1, -1]].forEach(function (c) { ctx.beginPath(); ctx.moveTo(c[0], c[1] + 16 * c[3]); ctx.lineTo(c[0], c[1]); ctx.lineTo(c[0] + 16 * c[2], c[1]); ctx.stroke(); });

      var e = Math.pow(10, p * SPAN) - 1, sc = k > 0.5 ? st + 1 : st;
      if (elCount) elCount.textContent = fmt(e);
      if (elSub) elSub.textContent = SCENES[sc].name;
      if (elStat) {
        var s2;
        if (sc === 0) { var c0 = planets.filter(function (pl) { return pl.th > 0 && u >= pl.th && st === 0; }).length; s2 = T.planets + c0 + T.of + "7" + T.start; }
        else if (sc === 1) s2 = T.starsReached + (sceneStars.n || 0) + T.of + stars.length + T.shown;
        else s2 = T.galReached + (sceneGalaxy.pct || 0) + " %";
        elStat.textContent = s2;
      }
      pills.forEach(function (el, n) { el.classList.toggle("on", n === sc); });
      if (range && document.activeElement !== range) range.value = Math.round(p * 1000);
    }

    function tick(now) {
      var dt = Math.min(0.1, (now - last) / 1000 || 0); last = now;
      if (!box.isConnected) return;                          // блок убран со страницы — цикл останавливается
      if (visible) {
        if (!reduce && !M.paused) clk += dt;
        if (playing) { p += dt / DURATION; if (p >= 1) { p = 1; playing = false; done = true; syncBtn(); } }
        frame();
      }
      requestAnimationFrame(tick);
    }
    function syncBtn() { if (btn) btn.textContent = playing ? T.pause : (done ? T.replay : T.play); }
    function play() { if (p >= 1) { p = 0; done = false; } playing = true; syncBtn(); }
    function pause() { playing = false; syncBtn(); }
    document.addEventListener("homensai-motion", function () { if (M.paused) pause(); });

    if (btn) btn.addEventListener("click", function () { if (playing) pause(); else play(); });
    if (rewind) rewind.addEventListener("click", function () { p = 0; done = false; play(); });
    if (range) range.addEventListener("input", function () { p = range.value / 1000; done = p >= 1; pause(); frame(); });

    function fit() { var r = cv.getBoundingClientRect(), dp = Math.min(window.devicePixelRatio || 1, 2); cv.width = Math.round(r.width * dp); cv.height = Math.round(r.width * H / W * dp); frame(); }
    window.addEventListener("resize", fit);
    fit(); syncBtn();

    // Сам запускается через 0,7 с после появления на экране (больше трети блока видно); при «уменьшить движение» — только по кнопке
    if ("IntersectionObserver" in window) {
      var started = false;
      new IntersectionObserver(function (es) {
        es.forEach(function (en) {
          visible = en.isIntersecting;
          if (visible && !started && !reduce && !M.paused) { started = true; setTimeout(play, 700); }
        });
      }, { threshold: 0.35 }).observe(cv);
    } else if (!reduce) play();
    requestAnimationFrame(tick);

    box.__cosmos = { play: play, pause: pause, seek: function (v) { p = clamp(v, 0, 1); frame(); } };
    return box.__cosmos;
  }

  H.cosmos = { mount: mount, text: TEXT };
  function start() { document.querySelectorAll(".cosmos").forEach(mount); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
