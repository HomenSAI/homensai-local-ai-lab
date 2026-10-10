// HomenS.AI Style · © 2026 Serhii Khomenko · https://homensai.com/ · https://github.com/HomenSAI · https://www.linkedin.com/in/serhii-khomenko-homensai/
// Графики на SVG без внешних библиотек. Цвета — только классы (CSS-переменные темы), без inline-стилей: CSP style-src 'self'.
// Тонкие столбцы со скруглением 4 px у вершины, линии 2 px, тонкая сетка; цвет не единственный носитель смысла (подписи и значки).

(function () {
"use strict";
const NS = "http://www.w3.org/2000/svg";

function s(tag, attrs = {}, ...children) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== null && v !== undefined && v !== false) el.setAttribute(k, String(v));
  for (const c of children.flat()) if (c !== null && c !== undefined && c !== false) el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  return el;
}

const fmt = (n) => Number(n.toFixed(1));

function root(width, height, label) {
  return s("svg", { viewBox: `0 0 ${width} ${height}`, class: "chart", role: "img", "aria-label": label, preserveAspectRatio: "xMidYMid meet" });
}

function gridLines(svg, left, right, top, plotH, ticks, ymax, width) {
  for (const v of ticks) {
    const y = top + plotH * (1 - v / ymax);
    svg.append(s("line", { class: "ch-grid", x1: left, x2: width - right, y1: fmt(y), y2: fmt(y) }), s("text", { class: "ch-tick", x: left - 6, y: fmt(y + 4), "text-anchor": "end" }, v));
  }
}

function columnPath(x, baseline, y, w, r = 4) {
  return `M${fmt(x)} ${fmt(baseline)} V${fmt(y + r)} Q${fmt(x)} ${fmt(y)} ${fmt(x + r)} ${fmt(y)} H${fmt(x + w - r)} Q${fmt(x + w)} ${fmt(y)} ${fmt(x + w)} ${fmt(y + r)} V${fmt(baseline)} Z`;
}

// Все попытки столбиками, сгруппированы по проверкам; у каждой группы своя золотая черта порога сдачи.
// groups: [{ label, passPercent, attempts: [{ percent, passed, number, title }] }]
function groupedBars(groups, { width = 640, height = 250, label = "" } = {}) {
  const svg = root(width, height, label);
  const left = 36;
  const right = 10;
  const top = 20;
  const bottom = 48;
  const plotH = height - top - bottom;
  const gap = 4;
  const total = groups.reduce((a, g) => a + g.attempts.length, 0) || 1;
  // толщина столбца не больше 22 px; при многих попытках сужается, чтобы всё поместилось
  const bw = Math.max(8, Math.min(22, (width - left - right - groups.length * 18 - total * gap) / total));
  gridLines(svg, left, right, top, plotH, [0, 25, 50, 75, 100], 100, width);
  const widths = groups.map((g) => g.attempts.length * (bw + gap) - gap);
  const space = (width - left - right - widths.reduce((a, b) => a + b, 0)) / Math.max(1, groups.length);
  let x = left + space / 2;
  groups.forEach((g, gi) => {
    g.attempts.forEach((a, i) => {
      const bx = x + i * (bw + gap);
      const y = top + plotH * (1 - a.percent / 100);
      const bar = s("path", { class: a.passed ? "ch-pass" : "ch-bar", d: columnPath(bx, top + plotH, y, bw) });
      bar.append(s("title", {}, `${g.label}, ${`${L().attempt} ${a.number}`}: ${a.percent} %${a.passed ? ` — ${L().passed}` : ""}`));
      svg.append(bar, s("text", { class: "ch-value", x: fmt(bx + bw / 2), y: fmt(y - 5), "text-anchor": "middle" }, Math.round(a.percent)), s("text", { class: "ch-tick", x: fmt(bx + bw / 2), y: top + plotH + 14, "text-anchor": "middle" }, a.number));
    });
    const mid = x + widths[gi] / 2;
    const room = Math.max(6, Math.floor((widths[gi] + space) / 7));
    const name = g.label.length > room ? `${g.label.slice(0, room - 1)}…` : g.label;
    svg.append(s("text", { class: "ch-label", x: fmt(mid), y: top + plotH + 32, "text-anchor": "middle" }, name));
    if (g.passPercent !== null && g.passPercent !== undefined) {
      const py = top + plotH * (1 - g.passPercent / 100);
      svg.append(s("line", { class: "ch-line-pass", x1: fmt(x - 8), x2: fmt(x + widths[gi] + 8), y1: fmt(py), y2: fmt(py) }));
    }
    x += widths[gi] + space;
  });
  return svg;
}

// Линия: средний балл по неделям. points: [{ label, value }]
function lineChart(points, { width = 520, height = 230, label = "", ymax = 100 } = {}) {
  const svg = root(width, height, label);
  const left = 36;
  const right = 18;
  const top = 18;
  const bottom = 28;
  const plotW = width - left - right;
  const plotH = height - top - bottom;
  gridLines(svg, left, right, top, plotH, [0, 25, 50, 75, 100], ymax, width);
  if (!points.length) return svg;
  const xs = points.map((_, i) => left + (points.length === 1 ? plotW / 2 : (plotW * i) / (points.length - 1)));
  const ys = points.map((p) => top + plotH * (1 - p.value / ymax));
  const line = xs.map((x, i) => `${i ? "L" : "M"}${fmt(x)} ${fmt(ys[i])}`).join(" ");
  if (points.length > 1) svg.append(s("path", { class: "ch-area", d: `${line} L${fmt(xs[xs.length - 1])} ${top + plotH} L${fmt(xs[0])} ${top + plotH} Z` }));
  svg.append(s("path", { class: "ch-line", d: line }));
  const every = Math.max(1, Math.ceil(points.length / 7));
  points.forEach((p, i) => {
    if (i % every === 0 || i === points.length - 1) svg.append(s("text", { class: "ch-tick", x: fmt(xs[i]), y: height - 8, "text-anchor": "middle" }, p.label));
    const dot = s("circle", { class: "ch-dot", cx: fmt(xs[i]), cy: fmt(ys[i]), r: i === points.length - 1 ? 5 : 4 });
    dot.append(s("title", {}, `${p.label}: ${p.value} %`));
    svg.append(dot);
  });
  const last = points.length - 1;
  svg.append(s("text", { class: "ch-value", x: fmt(xs[last] - 8), y: fmt(ys[last] - 10), "text-anchor": "end" }, `${points[last].value} %`));
  return svg;
}

// Горизонтальные полосы прогресса: [{ label, percent }]
function progressBars(items, { width = 460, rowHeight = 32, labelWidth = 150, label = "" } = {}) {
  const height = rowHeight * items.length + 10;
  const svg = root(width, height, label);
  const barW = width - labelWidth - 56;
  items.forEach((it, i) => {
    const y = i * rowHeight + 6;
    const name = it.label.length > 22 ? `${it.label.slice(0, 21)}…` : it.label;
    svg.append(
      s("text", { class: "ch-label", x: 0, y: y + 14 }, name),
      s("rect", { class: "ch-track", x: labelWidth, y: y + 4, width: barW, height: 10, rx: 5 }),
      s("rect", { class: "ch-bar", x: labelWidth, y: y + 4, width: fmt(Math.max(6, (barW * it.percent) / 100)), height: 10, rx: 5 }),
      s("text", { class: "ch-value", x: labelWidth + barW + 8, y: y + 14 }, `${it.percent} %`),
    );
  });
  return svg;
}

// Кольцо: доля сделанного
function ring(percent, { size = 140, label = "", tone = "" } = {}) {
  const r = 48;
  const c = 2 * Math.PI * r;
  const p = Math.max(0, Math.min(100, percent));
  const svg = s("svg", { viewBox: "0 0 120 120", width: size, height: size, class: "chart ring", role: "img", "aria-label": `${label} ${p} %` });
  svg.append(
    s("circle", { class: "ch-track-ring", cx: 60, cy: 60, r, fill: "none", "stroke-width": 10 }),
    s("circle", { class: `ch-ring ${tone}`, cx: 60, cy: 60, r, fill: "none", "stroke-width": 10, "stroke-linecap": "round", "stroke-dasharray": `${fmt((c * p) / 100)} ${fmt(c)}`, transform: "rotate(-90 60 60)" }),
    s("text", { class: "ch-ring-text", x: 60, y: 67, "text-anchor": "middle" }, `${Math.round(p)}%`),
  );
  return svg;
}

// Календарь активности: [{ date: "ГГГГ-ММ-ДД", minutes }] за последние weeks недель (по неделям слева направо)
function heatmap(days, { weeks = 16, label = "" } = {}) {
  const cell = 13;
  const gap = 3;
  const left = 28;
  const width = left + weeks * (cell + gap);
  const height = 7 * (cell + gap) + 20;
  const svg = s("svg", { viewBox: `0 0 ${width} ${height}`, width, class: "chart heat", role: "img", "aria-label": label });
  const byDate = new Map(days.map((d) => [d.date, d.minutes]));
  const today = new Date();
  const mondayOffset = (today.getDay() + 6) % 7;
  const start = new Date(today);
  start.setDate(today.getDate() - mondayOffset - (weeks - 1) * 7);
  const names = [L().weekdays[0], "", L().weekdays[2], "", L().weekdays[4], "", ""];
  names.forEach((n, i) => n && svg.append(s("text", { class: "ch-tick", x: 0, y: i * (cell + gap) + 11 }, n)));
  for (let w = 0; w < weeks; w++) {
    for (let d = 0; d < 7; d++) {
      const day = new Date(start);
      day.setDate(start.getDate() + w * 7 + d);
      if (day > today) continue;
      const iso = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
      const min = byDate.get(iso) || 0;
      const level = min === 0 ? 0 : min < 15 ? 1 : min < 45 ? 2 : 3;
      const rect = s("rect", { class: `ch-heat l${level}`, x: left + w * (cell + gap), y: d * (cell + gap), width: cell, height: cell, rx: 3 });
      rect.append(s("title", {}, `${day.toLocaleDateString(L().locale)}: ${min} ${L().minutes}`));
      svg.append(rect);
    }
    const first = new Date(start);
    first.setDate(start.getDate() + w * 7);
    if (first.getDate() <= 7) svg.append(s("text", { class: "ch-tick", x: left + w * (cell + gap), y: height - 4 }, first.toLocaleDateString(L().locale, { month: "short" })));
  }
  return svg;
}

// Полоса уровней освоения: counts — { new, attempted, familiar, proficient, mastered }
function levelsBar(counts, { width = 520, label = "" } = {}) {
  const order = ["new", "attempted", "familiar", "proficient", "mastered"];
  const total = order.reduce((a, k) => a + (counts[k] || 0), 0) || 1;
  const svg = root(width, 34, label);
  let x = 0;
  for (const k of order) {
    const w = ((width - 8) * (counts[k] || 0)) / total;
    if (w > 0) {
      const part = s("rect", { class: `ch-level ${k}`, x: fmt(x), y: 4, width: fmt(Math.max(w - 2, 1)), height: 24, rx: 4 });
      part.append(s("title", {}, `${L().levels[k]}: ${counts[k]}`));
      svg.append(part);
    }
    x += w;
  }
  return svg;
}

// Подписи графиков. Язык: HomenS.charts.setLocale("ru" | "en" | "de"); любые подписи можно переопределить через setLabels({...}).
const DICT = {
  ru: { locale: "ru-RU", attempt: "попытка", passed: "сдано", minutes: "мин", weekdays: ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"], levels: { new: "Не начато", attempted: "Начато", familiar: "Знакомо", proficient: "Уверенно", mastered: "Освоено" } },
  en: { locale: "en-GB", attempt: "attempt", passed: "passed", minutes: "min", weekdays: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], levels: { new: "Not started", attempted: "Started", familiar: "Familiar", proficient: "Proficient", mastered: "Mastered" } },
  de: { locale: "de-DE", attempt: "Versuch", passed: "bestanden", minutes: "Min.", weekdays: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"], levels: { new: "Nicht begonnen", attempted: "Begonnen", familiar: "Vertraut", proficient: "Sicher", mastered: "Gemeistert" } },
};
let current = { ...DICT.ru };
function L() {
  return current;
}
function setLocale(code) {
  current = { ...(DICT[code] || DICT.ru) };
}
function setLabels(patch) {
  current = { ...current, ...patch, levels: { ...current.levels, ...(patch.levels || {}) } };
}

window.HomenS = window.HomenS || {};
window.HomenS.charts = { groupedBars, lineChart, progressBars, ring, heatmap, levelsBar, setLocale, setLabels };
})();
