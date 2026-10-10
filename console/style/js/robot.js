// HomenS.AI Style · © 2026 Serhii Khomenko · https://homensai.com/ · https://github.com/HomenSAI · https://www.linkedin.com/in/serhii-khomenko-homensai/
// Робот автора: шестерёнка и схема логотипа трясутся, превращаются в голову робота 1930-х и подмигивают.
// Перенесён с сайта homensai.com (собственный код автора). SVG строится из статической разметки через DOMParser, не innerHTML.

(function () {
"use strict";
const motion = { paused: false };
const reduce = typeof window !== "undefined" && window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function tvRobot(host) {
  var id = Math.random().toString(36).slice(2, 8);
  var HEAD = 'M54 66 H146 Q153 66 152 73 L143 144 Q142 150 136 150 H64 Q58 150 57 144 L48 73 Q47 66 54 66 Z';
  var markup = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" class="robo-svg" aria-hidden="true"><defs>' +
    '<linearGradient id="ch' + id + '" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#5f6b70"/><stop offset=".18" stop-color="#a9b3b5"/><stop offset=".3" stop-color="#f4f6f2"/><stop offset=".42" stop-color="#a9b3b5"/><stop offset=".7" stop-color="#a9b3b5"/><stop offset=".82" stop-color="#f4f6f2"/><stop offset="1" stop-color="#5f6b70"/></linearGradient>' +
    '<clipPath id="eL' + id + '"><rect class="lidL" x="-12" y="-12" width="24" height="24"/></clipPath><clipPath id="eR' + id + '"><rect class="lidR" x="-12" y="-12" width="24" height="24"/></clipPath></defs>' +
    '<g class="all">' +
    '<g class="antL"><path d="M84 64 L72 38" stroke="currentColor" stroke-width="3" stroke-linecap="round"/><circle cx="72" cy="34" r="5" fill="#c9a24a" stroke="#1d1a17" stroke-width="2"/></g>' +
    '<g class="antR"><path d="M116 64 L128 38" stroke="currentColor" stroke-width="3" stroke-linecap="round"/><circle cx="128" cy="34" r="5" fill="#2bb3c4" stroke="#1d1a17" stroke-width="2"/></g>' +
    '<g class="gear"><path d="M50.0 13.0 L48.1 13.1 L46.1 13.2 L44.2 13.5 L42.3 13.8 L42.2 21.0 L40.7 21.5 L39.2 22.0 L37.8 22.6 L36.4 23.3 L31.5 18.0 L29.8 19.0 L28.3 20.1 L26.7 21.2 L25.2 22.5 L28.8 28.8 L27.7 29.9 L26.7 31.1 L25.7 32.4 L24.8 33.7 L18.0 31.5 L17.0 33.2 L16.2 35.0 L15.5 36.7 L14.8 38.6 L21.0 42.2 L20.7 43.8 L20.4 45.3 L20.2 46.9 L20.0 48.4 L13.0 50.0 L13.1 51.9 L13.2 53.9 L13.5 55.8 L13.8 57.7 L21.0 57.8 L21.5 59.3 L22.0 60.8 L22.6 62.2 L23.3 63.6 L18.0 68.5 L19.0 70.2 L20.1 71.7 L21.2 73.3 L22.5 74.8 L28.8 71.2 L29.9 72.3 L31.1 73.3 L32.4 74.3 L33.7 75.2 L31.5 82.0 L33.2 83.0 L35.0 83.8 L36.7 84.5 L38.6 85.2 L42.2 79.0 L43.8 79.3 L45.3 79.6 L46.9 79.8 L48.4 80.0 L50.0 87.0 Z" fill="#c9a24a"/></g>' +
    '<g class="circ"><path d="M50 20 A30 30 0 0 1 50 80" fill="none" stroke="#2bb3c4" stroke-width="5"/><g fill="none" stroke="#2bb3c4" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"><path d="M50 36 H64 L70 30"/><path d="M50 50 H72"/><path d="M50 64 H62 L68 70"/></g><g fill="#2bb3c4"><circle cx="71" cy="29" r="4"/><circle cx="74" cy="50" r="4"/><circle cx="69" cy="71" r="4"/></g></g>' +
    '<g class="head" opacity="0"><path d="' + HEAD + '" fill="#1d1a17" transform="translate(5 5)"/><path d="' + HEAD + '" fill="url(#ch' + id + ')" stroke="#1d1a17" stroke-width="3"/>' +
    '<g fill="#566663"><circle cx="58" cy="73" r="2.2"/><circle cx="142" cy="73" r="2.2"/><circle cx="64" cy="143" r="2.2"/><circle cx="136" cy="143" r="2.2"/></g>' +
    '<path d="M64 78 H136 L131 112 H69 Z" fill="none" stroke="#566663" stroke-width="1.2" opacity=".55"/>' +
    '<g class="mouth"><circle cx="100" cy="131" r="9" fill="#1c2a26"/><path d="M100 131 L106 131 M100 131 L104.2 135.2 M100 131 L100 137 M100 131 L95.8 135.2 M100 131 L94 131 M100 131 L95.8 126.8 M100 131 L100 125 M100 131 L104.2 126.8" stroke="#9fb0ad" stroke-width="1.4"/><path d="M80 128 H88 M80 134 H88 M112 128 H120 M112 134 H120" stroke="#1c2a26" stroke-width="2" stroke-linecap="round"/></g></g>' +
    eye('L', '#c9a24a', -4.8, -5.7) + eye('R', '#2bb3c4', 3.8, -6.5) + '</g></svg>';
  host.replaceChildren(document.importNode(new DOMParser().parseFromString(markup, 'image/svg+xml').documentElement, true));
  function eye(k, col, nx, ny) {
    return '<g class="eye' + k + '"><g clip-path="url(#e' + k + id + ')"><g class="hub"><circle r="9" fill="#14212e"/><circle r="3.5" fill="' + col + '"/></g>' +
      '<g class="gauge" opacity="0"><circle r="9" fill="#f7fbf8" stroke="#1c2a26" stroke-width="2"/><path d="M-6 -2 A6.3 6.3 0 0 1 6 -2" fill="none" stroke="#1c2a26" stroke-width=".8" stroke-dasharray="1 1.6"/>' +
      '<path d="M0 0 L' + nx + ' ' + ny + '" stroke="#d0573d" stroke-width="1.6" stroke-linecap="round"/><circle r="1.6" fill="#1c2a26"/></g></g></g>';
  }
  var q = function (c) { return host.querySelector('.' + c); };
  var E = { all: q('all'), gear: q('gear'), circ: q('circ'), head: q('head'), mouth: q('mouth'), eyeL: q('eyeL'), eyeR: q('eyeR'),
    antL: q('antL'), antR: q('antR'), lidL: q('lidL'), lidR: q('lidR') };
  var gauges = host.querySelectorAll('.gauge'), hubs = host.querySelectorAll('.hub');
  var clamp = function (x) { return x < 0 ? 0 : x > 1 ? 1 : x; };
  var lerp = function (a, b, t) { return a + (b - a) * t; };
  var seg = function (t, a, b) { return clamp((t - a) / (b - a)); };
  var inOut = function (x) { return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  var back = function (x) { var c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
  function place(el, x, y, sc, rot) {
    el.setAttribute('transform', 'translate(' + x.toFixed(2) + ' ' + y.toFixed(2) + ') rotate(' + rot.toFixed(1) + ') scale(' + sc.toFixed(3) + ') translate(-50 -50)');
  }
  function lid(el, v) { el.setAttribute('y', (-12 * v).toFixed(2)); el.setAttribute('height', (24 * v).toFixed(2)); }
  // t in ms: 0–1000 logo, 1000–3000 shake left → right, 3000–3900 pop into the head, 5000 wink, 6400 blink
  function draw(t) {
    var m = t < 3000 ? 0 : t < 3900 ? back(seg(t, 3000, 3900)) : 1, mc = clamp(m);
    var shG = t < 3300 ? Math.pow(seg(t, 1000, 2900), 2) : 0, shC = t < 3300 ? Math.pow(seg(t, 1500, 2900), 2) : 0;
    var settle = t >= 3000 && t < 4300 ? (1 - seg(t, 3000, 4300)) * 1.6 : 0, w = t * 0.19;
    var jG = 3.2 * shG * Math.sin(w) + settle * Math.sin(w * .8);
    var jC = 3.2 * shC * Math.sin(w + 1.3) + settle * Math.sin(w * .8 + 1);
    var jy = 1.1 * Math.max(shG, shC) * Math.sin(w * 1.7), jE = (jG + jC) / 2;
    place(E.gear, lerp(100, 44, m) + jG, lerp(100, 106, m) + jy, lerp(1.6, .36, m), jG * 2);
    place(E.circ, lerp(100, 156, m) + jC, lerp(100, 106, m) - jy, lerp(1.6, .42, m), jC * 2);
    var es = lerp(1.6, 1.45, mc), gf = seg(mc, .45, .9);
    E.eyeL.setAttribute('transform', 'translate(' + (lerp(100, 80, m) + jE).toFixed(2) + ' ' + lerp(100, 98, m).toFixed(2) + ') scale(' + es.toFixed(3) + ')');
    E.eyeR.setAttribute('transform', 'translate(' + (lerp(100, 120, m) + jE).toFixed(2) + ' ' + lerp(100, 98, m).toFixed(2) + ') scale(' + es.toFixed(3) + ')');
    E.eyeR.setAttribute('opacity', mc > .02 ? 1 : 0);
    for (var i = 0; i < gauges.length; i++) { gauges[i].setAttribute('opacity', gf.toFixed(3)); hubs[i].setAttribute('opacity', (1 - gf).toFixed(3)); }
    E.head.setAttribute('opacity', clamp(m * 3).toFixed(3));
    E.head.setAttribute('transform', 'translate(' + (100 + jE).toFixed(2) + ' 107) scale(' + lerp(.04, 1, clamp(m * 1.25)).toFixed(3) + ' ' + lerp(.35, 1, mc).toFixed(3) + ') translate(-100 -107)');
    E.mouth.setAttribute('opacity', seg(t, 3500, 4100).toFixed(3));
    var ga = inOut(seg(t, 3600, 4300));
    [E.antL, E.antR].forEach(function (el, k) {
      var bx = k ? 116 : 84;
      el.setAttribute('transform', 'translate(' + bx + ' 64) scale(' + ga.toFixed(3) + ') translate(' + (-bx) + ' -64)');
      el.setAttribute('opacity', ga > .01 ? 1 : 0);
    });
    var k1 = seg(t, 5000, 5500), wink = k1 > .3 && k1 < .7 ? .08 : 1 - Math.sin(Math.PI * k1) * .92;
    var b1 = seg(t, 6400, 6650), blink = 1 - Math.sin(Math.PI * b1) * .92;
    lid(E.lidL, blink);
    lid(E.lidR, b1 > 0 && b1 < 1 ? blink : wink);
    E.all.setAttribute('transform', 'rotate(' + (Math.sin(Math.PI * seg(t, 4850, 5800)) * 4).toFixed(2) + ' 100 107)');
  }
  var raf = 0, t0 = null, onWink = null, lastT = 0, running = false, formed = false;
  // Знак сообщает странице: «собрался в голову» (через 3,9 с) и «начал заново». Под ним по этим событиям появляется надпись (js/logo-word.js).
  function announce(name) { host.dispatchEvent(new CustomEvent(name, { bubbles: true })); }
  function setFormed(v) { if (formed !== v) { formed = v; announce(v ? "homensai-logo-formed" : "homensai-logo-reset"); } }
  function tick(now) {
    if (!host.isConnected) { raf = 0; running = false; return; }  // страница закрыта: цикл не крутится вхолостую
    if (t0 == null) t0 = now;
    var t = now - t0;
    if (t >= 3900) setFormed(true);
    if (t > 5600 && onWink) { onWink(); onWink = null; }
    if (t > 7000) t = 4300 + (t - 7000) % 2700; // stays a robot: wink + blink, again and again
    lastT = now - t0;
    draw(t);
    if (motion.paused) { raf = 0; return; }       // global pause: hold the current frame
    raf = requestAnimationFrame(tick);
  }
  document.addEventListener('homensai-motion', function () {
    if (!motion.paused && running && !raf) { t0 = performance.now() - lastT; raf = requestAnimationFrame(tick); }
  });
  draw(0);
  return {
    play: function (cb) { onWink = cb || null; cancelAnimationFrame(raf); running = true; setFormed(false); if (reduce) { draw(4400); setFormed(true); if (onWink) onWink(); return; } t0 = null; raf = requestAnimationFrame(tick); },
    reset: function () { cancelAnimationFrame(raf); raf = 0; running = false; draw(0); setFormed(false); }
  };
}

window.HomenS = window.HomenS || {};
window.HomenS.robot = { tvRobot, motion };
})();
