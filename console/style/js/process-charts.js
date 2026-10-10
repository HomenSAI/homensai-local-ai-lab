// HomenS.AI Style · © 2026 Serhii Khomenko · https://homensai.com/ · https://github.com/HomenSAI
// Проценты, распределения, скорость и текстовые графики из convert-page-variants.html. Без сетевых вызовов и HTML из данных.
(function () {
  "use strict";
  const NS = "http://www.w3.org/2000/svg";
  const tones = new Set(["accent", "teal", "ok", "warn", "bad", "gold", "muted"]);
  let sequence = 0;
  const finite = n => typeof n === "number" && Number.isFinite(n) && n >= 0;
  const percent = n => finite(n) ? Math.min(100, n) : null;
  const tone = t => tones.has(t) ? t : "accent";
  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = String(text);
    return e;
  }
  function svg(tag, attrs, text) {
    const e = document.createElementNS(NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => e.setAttribute(k, String(v)));
    if (text !== undefined) e.textContent = String(text);
    return e;
  }
  function root(w, h, label) {
    const e = svg("svg", { viewBox: `0 0 ${w} ${h}`, class: "pv-chart", role: "img", "aria-label": label });
    e.append(svg("title", {}, label));
    return e;
  }
  function gradient(host) {
    const id = "pv-gradient-" + (++sequence);
    const defs = svg("defs"), g = svg("linearGradient", { id });
    g.append(svg("stop", { offset: 0, class: "pv-gradient-start" }), svg("stop", { offset: 1, class: "pv-gradient-end" }));
    defs.append(g); host.append(defs);
    return `url(#${id})`;
  }
  function ring(value, { label = "Progress" } = {}) {
    const p = percent(value), e = root(150, 150, `${label}: ${p === null ? "—" : p + "%"}`);
    e.classList.add("pv-ring");
    const circumference = 2 * Math.PI * 62;
    e.append(svg("circle", { cx: 75, cy: 75, r: 62, fill: "none", class: "pv-ring-track", "stroke-width": 14 }));
    if (p !== null) e.append(svg("circle", { cx: 75, cy: 75, r: 62, stroke: gradient(e), class: "pv-ring-stroke", "stroke-dasharray": `${circumference * p / 100} ${circumference}`, transform: "rotate(-90 75 75)" }));
    e.append(svg("text", { x: 75, y: 83, "text-anchor": "middle", class: "pv-value pv-ring-value" }, p === null ? "—" : Math.round(p) + "%"));
    return e;
  }
  function progress(value, { label = "Progress", tone: colour = "gradient" } = {}) {
    const p = percent(value), e = root(300, 14, `${label}: ${p === null ? "—" : p + "%"}`);
    e.append(svg("rect", { x: 0, y: 1, width: 300, height: 12, rx: 6, class: "pv-track" }));
    if (p !== null && p > 0) {
      const attrs = { x: 0, y: 1, width: 300 * p / 100, height: 12, rx: 6 };
      if (colour === "gradient") attrs.fill = gradient(e); else attrs.class = "pv-fill-" + tone(colour);
      e.append(svg("rect", attrs));
    }
    return e;
  }
  function countBars(items, { label = "Counts", locale = "ru-RU" } = {}) {
    const list = el("ul", "pv-bars"), valid = items.filter(i => finite(i.value));
    list.setAttribute("aria-label", label);
    if (!valid.length) return el("p", "pv-note", "—");
    const max = Math.max(1, ...valid.map(i => i.value));
    valid.forEach(i => {
      const row = el("li"), g = root(180, 12, `${i.label}: ${i.value}`);
      g.append(svg("rect", { width: 180, height: 12, rx: 6, class: "pv-track" }));
      if (i.value > 0) g.append(svg("rect", { width: 180 * i.value / max, height: 12, rx: 6, class: "pv-fill-" + tone(i.tone) }));
      row.append(el("span", "pv-bar-label", i.label), g, el("b", "pv-bar-value", i.value.toLocaleString(locale)));
      list.append(row);
    });
    return list;
  }
  function distribution(items, { label = "Distribution", locale = "ru-RU" } = {}) {
    const valid = items.filter(i => finite(i.value)), total = valid.reduce((n, i) => n + i.value, 0);
    const host = el("div"), e = root(520, 26, `${label}; ${valid.map(i => `${i.label}: ${i.value}`).join(", ")}`), legend = el("ul", "pv-legend");
    let x = 0;
    e.append(svg("rect", { width: 520, height: 24, rx: 8, class: "pv-track" }));
    valid.forEach(i => {
      const width = total ? 520 * i.value / total : 0;
      if (width > 0) { const part = svg("rect", { x, y: 0, width, height: 24, class: "pv-fill-" + tone(i.tone) }); part.append(svg("title", {}, `${i.label}: ${i.value}`)); e.append(part); }
      x += width;
      const row = el("li"), sw = el("span", "pv-swatch pv-swatch-" + tone(i.tone)); sw.setAttribute("aria-hidden", "true");
      row.append(sw, document.createTextNode(`${i.label}: ${i.value.toLocaleString(locale)} (${total ? (100 * i.value / total).toFixed(1) + "%" : "—"})`)); legend.append(row);
    });
    host.append(e, legend); return host;
  }
  function histogram(values, { label = "Words", binWidth = 160, bins = 10 } = {}) {
    if (!Number.isInteger(bins) || bins < 1 || bins > 50 || !finite(binWidth) || !binWidth) throw new TypeError("Invalid histogram bins");
    const counts = Array(bins).fill(0);
    values.filter(finite).forEach(v => counts[Math.min(bins - 1, Math.floor(v / binWidth))]++);
    const e = root(520, 130, label), max = Math.max(1, ...counts);
    const step = 480 / bins, barWidth = Math.min(22, step - 2);
    counts.forEach((n, i) => {
      const range = i === bins - 1 ? `${i * binWidth}+` : `${i * binWidth}–${(i + 1) * binWidth - 1}`;
      const x = 20 + i * step + (step - barWidth) / 2, h = n / max * 80;
      const bar = svg("rect", { x, y: 98 - h, width: barWidth, height: h, rx: Math.min(3, h / 2), class: "pv-fill-teal" });
      bar.append(svg("title", {}, `${range}: ${n}`));
      e.append(bar, svg("text", { x: x + barWidth / 2, y: 92 - h, "text-anchor": "middle", class: "pv-value" }, n), svg("text", { x: x + barWidth / 2, y: 120, "text-anchor": "middle" }, i === bins - 1 ? `${i * binWidth}+` : i * binWidth));
    }); return e;
  }
  function rateLine(samples, { label = "Rate", unit = "files/s", averageLabel = "Average" } = {}) {
    const values = samples.filter(s => finite(s.elapsedSeconds) && finite(s.value)).slice(-40);
    const e = root(520, 160, label), max = Math.max(10, ...values.map(s => s.value));
    const minTime = values.length ? values[0].elapsedSeconds : 0, maxTime = values.length ? values[values.length - 1].elapsedSeconds : 0;
    [0, max / 2, max].forEach(v => { const y = 125 - v / max * 100; e.append(svg("line", { x1: 48, x2: 505, y1: y, y2: y, class: "pv-grid-line" }), svg("text", { x: 42, y: y + 4, "text-anchor": "end" }, Math.round(v))); });
    e.append(svg("text", { x: 48, y: 14 }, unit));
    if (!values.length) return e;
    const xy = values.map(s => [maxTime === minTime ? 275 : 48 + (s.elapsedSeconds - minTime) / (maxTime - minTime) * 457, 125 - s.value / max * 100]);
    const avg = values.reduce((n, s) => n + s.value, 0) / values.length, y = 125 - avg / max * 100;
    const average = svg("line", { x1: 48, x2: 505, y1: y, y2: y, class: "pv-average" }); average.append(svg("title", {}, `${averageLabel}: ${avg.toFixed(1)} ${unit}`)); e.append(average);
    const line = xy.map(p => p.join(",")).join(" ");
    if (xy.length > 1) e.append(svg("polygon", { points: `${xy[0][0]},125 ${line} ${xy[xy.length - 1][0]},125`, class: "pv-speed-area" }));
    e.append(svg("polyline", { points: line, class: "pv-speed" }));
    xy.forEach((p, i) => { const dot = svg("circle", { cx: p[0], cy: p[1], r: 3, class: "pv-fill-teal" }); dot.append(svg("title", {}, `${values[i].elapsedSeconds}s: ${values[i].value} ${unit}`)); e.append(dot); });
    e.append(svg("text", { x: 48, y: 151 }, `${minTime}s`), svg("text", { x: 505, y: 151, "text-anchor": "end" }, `${maxTime}s`));
    return e;
  }
  function textBar(value, size = 20) {
    const p = percent(value), n = Math.max(1, Math.min(80, Math.round(size) || 20));
    return p === null ? "—" : "█".repeat(Math.round(p / 100 * n)).padEnd(n, "░");
  }
  function sparkline(values) {
    const data = values.filter(finite).slice(-32), blocks = "▁▂▃▄▅▆▇█", max = Math.max(1, ...data);
    return data.length ? data.map(v => blocks[Math.min(7, Math.floor(v / max * 7))]).join("") : "—";
  }
  function textHistogram(items, size = 24) {
    const data = items.filter(i => finite(i.value)).slice().sort((a, b) => b.value - a.value), max = Math.max(1, ...data.map(i => i.value));
    const width = Math.max(1, Math.min(80, Math.round(size) || 24));
    return data.map(i => `${String(i.label).padEnd(28)} ${"█".repeat(Math.round(i.value / max * width)).padEnd(width)} ${i.value}`).join("\n") || "—";
  }
  window.HomenS = window.HomenS || {};
  window.HomenS.processCharts = { ring, progress, countBars, distribution, histogram, rateLine, textBar, sparkline, textHistogram };
})();
