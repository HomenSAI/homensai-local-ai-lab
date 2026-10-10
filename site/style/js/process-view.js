// HomenS.AI Style · © 2026 Serhii Khomenko · https://homensai.com/ · https://github.com/HomenSAI
// Переиспользуемая страница процесса A/B/C. Только отображение снимка данных; действий над заданиями здесь нет.
(function () {
  "use strict";
  const jobs = new Set(["idle", "running", "succeeded", "failed", "cancelled"]);
  const steps = new Set(["pending", "running", "succeeded", "failed", "skipped"]);
  const levels = new Set(["info", "warn", "error", "ok", "progress"]);
  const labels = {
    modes: ["Вид страницы", "Page layout", "Seitenansicht"],
    A: ["A · Командный центр", "A · Command centre", "A · Leitstand"],
    B: ["B · Конвейер", "B · Pipeline", "B · Verarbeitung"],
    C: ["C · Терминал", "C · Terminal", "C · Terminal"],
    idle: ["Ожидание данных", "Waiting for data", "Warten auf Daten"],
    running: ["Выполняется", "Running", "In Bearbeitung"],
    succeeded: ["Завершено", "Completed", "Abgeschlossen"],
    failed: ["Ошибка", "Failed", "Fehlgeschlagen"],
    cancelled: ["Отменено", "Cancelled", "Abgebrochen"],
    pending: ["Ожидает", "Pending", "Ausstehend"],
    skipped: ["Пропущено", "Skipped", "Übersprungen"],
    progress: ["Общий ход", "Overall progress", "Gesamtfortschritt"],
    stages: ["Этапы", "Stages", "Phasen"],
    files: ["Файлов просмотрено", "Files scanned", "Dateien geprüft"],
    lessons: ["Уроков собрано", "Lessons created", "Lektionen erstellt"],
    questions: ["Вопросов перенесено", "Questions imported", "Fragen importiert"],
    issues: ["Замечаний и ошибок", "Warnings and errors", "Hinweise und Fehler"],
    errors: ["Ошибок", "Errors", "Fehler"],
    rate: ["Скорость обработки", "Processing rate", "Verarbeitungsgeschwindigkeit"],
    unit: ["файл/с", "files/s", "Dateien/s"],
    average: ["Среднее по показанным замерам", "Mean of displayed samples", "Mittelwert der angezeigten Messungen"],
    current: ["Текущая скорость", "Current rate", "Aktuelle Geschwindigkeit"],
    codes: ["Проблемы по кодам", "Issues by code", "Probleme nach Code"],
    source: ["Языки источника", "Source languages", "Quellsprachen"],
    words: ["Размер уроков (слов)", "Lesson length (words)", "Lektionslänge (Wörter)"],
    outcomes: ["Куда ушли файлы", "File outcomes", "Dateiergebnisse"],
    coverage: ["Покрытие", "Coverage", "Abdeckung"],
    topics: ["Темы", "Topics", "Themen"],
    log: ["Журнал процесса", "Process log", "Prozessprotokoll"],
    terminal: ["Терминальное представление", "Terminal view", "Terminalansicht"],
    counters: ["Счётчики", "Counters", "Zähler"],
    eta: ["Осталось примерно", "Estimated remaining", "Geschätzte Restzeit"],
    seconds: ["с", "s", "s"],
    elapsed: ["Время", "Elapsed", "Laufzeit"],
    noData: ["Нет данных", "No data", "Keine Daten"],
    logNote: ["Показаны последние строки. Прокрутка следует за журналом только когда вы находитесь внизу.", "Recent lines only. Auto-scroll follows the log only while you are at the bottom.", "Nur die letzten Zeilen. Automatisches Scrollen folgt dem Protokoll nur am Ende."],
    lines: ["строк показано", "lines displayed", "angezeigte Zeilen"]
  };
  const number = (v, name) => {
    if (v === undefined || v === null) return null;
    if (typeof v !== "number" || !Number.isFinite(v) || v < 0) throw new TypeError(name + ": expected a nonnegative finite number or null");
    return v;
  };
  const percentage = (v, name) => { const n = number(v, name); if (n !== null && n > 100) throw new TypeError(name + ": expected 0..100"); return n; };
  const text = v => v === undefined || v === null ? "" : String(v);
  function array(v, name) { if (v === undefined) return []; if (!Array.isArray(v)) throw new TypeError(name + ": expected an array"); return v; }
  function normalize(raw) {
    if (!raw || raw.schemaVersion !== 1 || !raw.job || !jobs.has(raw.job.status)) throw new TypeError("Expected schemaVersion: 1 and a valid job.status");
    const metrics = {}, coverage = {};
    ["files", "lessons", "questions", "issues", "errors"].forEach(k => { metrics[k] = number(raw.metrics?.[k], "metrics." + k); });
    ["lessons", "questions"].forEach(k => {
      const c = raw.coverage?.[k];
      const done = number(c?.done, "coverage." + k + ".done"), total = number(c?.total, "coverage." + k + ".total");
      if (done !== null && total !== null && done > total) throw new TypeError("Coverage done exceeds total");
      coverage[k] = { done, total, percent: done !== null && total > 0 ? 100 * done / total : null };
    });
    const normalizeSteps = (list, name) => array(list, name).map((s, i) => {
      if (!s || !steps.has(s.status)) throw new TypeError(name + ": invalid status");
      return { id: text(s.id || i), label: text(s.label), status: s.status, percent: percentage(s.percent, name + ".percent") };
    });
    const counts = (list, name) => array(list, name).map(i => ({ label: text(i.label), value: number(i.value, name + ".value"), tone: text(i.tone) }));
    const rates = array(raw.rateSamples, "rateSamples").map(s => ({ elapsedSeconds: number(s.elapsedSeconds, "sample.time"), value: number(s.value, "sample.value") }));
    if (rates.some((s, i) => s.elapsedSeconds === null || s.value === null || (i && s.elapsedSeconds <= rates[i - 1].elapsedSeconds))) throw new TypeError("Rate samples require strictly increasing times and numeric values");
    const logs = array(raw.logs, "logs").map(e => {
      if (!e || !levels.has(e.level)) throw new TypeError("Invalid log level");
      return { time: text(e.time), level: e.level, code: text(e.code), message: text(e.message) };
    });
    return {
      job: { id: text(raw.job.id), label: text(raw.job.label), status: raw.job.status, percent: percentage(raw.job.percent, "job.percent"), etaSeconds: number(raw.job.etaSeconds, "job.etaSeconds"), elapsedSeconds: number(raw.job.elapsedSeconds, "job.elapsedSeconds") },
      metrics, coverage, stages: normalizeSteps(raw.stages, "stages"), topics: normalizeSteps(raw.topics, "topics"),
      issuesByCode: counts(raw.issuesByCode, "issuesByCode"), languages: counts(raw.languages, "languages"), outcomes: counts(raw.outcomes, "outcomes"),
      lessonWords: array(raw.lessonWords, "lessonWords").map(v => number(v, "lessonWords")), rateSamples: rates, logs
    };
  }
  function node(tag, cls, value) { const e = document.createElement(tag); if (cls) e.className = cls; if (value !== undefined) e.textContent = String(value); return e; }
  function mount(host, options = {}) {
    if (!(host instanceof Element)) throw new TypeError("Expected a host element");
    const C = window.HomenS.processCharts;
    if (!C) throw new Error("Load process-charts.js first");
    const lang = ["ru", "en", "de"].includes(options.locale) ? options.locale : "ru", languageIndex = { ru: 0, en: 1, de: 2 }[lang];
    const own = options.labels && typeof options.labels === "object" ? options.labels : {};
    // options.labels заменяет подписи под предметную область проекта: { files: ["Моделей", "Models", "Modelle"] } или строка на всех языках.
    const L = key => { const o = own[key]; if (typeof o === "string") return o; if (Array.isArray(o) && o[languageIndex]) return String(o[languageIndex]); return labels[key]?.[languageIndex] || key; }, locale = { ru: "ru-RU", en: "en-GB", de: "de-DE" }[lang];
    const fmt = v => v === null ? "—" : v.toLocaleString(locale, { maximumFractionDigits: 1 });
    const pct = v => v === null ? "—" : fmt(v) + "%";
    const maxLines = Math.max(1, Math.min(2000, Math.floor(Number(options.maxLogLines)) || 200));
    const controller = new AbortController(), shell = node("div", "pv"), toolbar = node("div", "pv-toolbar"), title = node("h2", "pv-job"), state = node("p", "pv-state badge"), panels = {}, slots = {}, buttons = {};
    shell.lang = lang; toolbar.setAttribute("role", "group"); toolbar.setAttribute("aria-label", L("modes"));
    state.setAttribute("role", "status"); state.setAttribute("aria-live", "polite");
    let mode = ["A", "B", "C"].includes(options.mode) ? options.mode : "A", current = null, destroyed = false;
    if (!options.mode && options.storageKey) { try { const saved = localStorage.getItem(options.storageKey); if (["A", "B", "C"].includes(saved)) mode = saved; } catch (_) { /* хранение необязательно */ } }
    function setMode(next) {
      if (destroyed) throw new Error("View is destroyed");
      if (!["A", "B", "C"].includes(next)) throw new TypeError("Expected A, B or C");
      mode = next;
      Object.keys(panels).forEach(k => { panels[k].hidden = k !== mode; buttons[k].setAttribute("aria-pressed", String(k === mode)); });
      if (options.storageKey) { try { localStorage.setItem(options.storageKey, mode); } catch (_) { /* хранение необязательно */ } }
    }
    ["A", "B", "C"].forEach(k => {
      const button = node("button", "", L(k)); button.type = "button"; button.dataset.mode = k;
      button.addEventListener("click", () => setMode(k), { signal: controller.signal }); toolbar.append(button); buttons[k] = button;
      panels[k] = node("section", "pv-panel"); panels[k].dataset.panel = k; panels[k].setAttribute("aria-label", L(k)); slots[k] = {};
    });
    shell.append(toolbar, title, state, ...Object.values(panels)); host.replaceChildren(shell);
    function card(parent, heading) { const e = node("div", "pv-card"); e.append(node("h3", "", L(heading))); parent.append(e); return e; }
    function slot(parent, k, name, tag = "div", cls = "") { const e = node(tag, cls); parent.append(e); slots[k][name] = e; return e; }
    function grid(parent, cls) { const e = node("div", "pv-grid " + cls); parent.append(e); return e; }
    function terminal(parent, k) {
      const e = node("div", "pv-terminal"), head = node("div", "pv-terminal-head");
      [1, 2, 3].forEach(() => { const dot = node("span", "pv-dot"); dot.setAttribute("aria-hidden", "true"); head.append(dot); });
      head.append(document.createTextNode("process@homensai ~ / " + L("log")), node("span", "spacer"));
      slot(head, k, "lines", "span"); e.append(head);
      const pre = slot(e, k, "log", "pre"); pre.tabIndex = 0; pre.setAttribute("role", "region"); pre.setAttribute("aria-label", L("log")); pre.setAttribute("aria-live", "off");
      parent.append(e, node("p", "pv-note", L("logNote")));
    }
    const aMetrics = grid(panels.A, "pv-grid4");
    ["files", "lessons", "questions", "issues"].forEach((key, i) => { const c = card(aMetrics, key); slot(c, "A", key, "div", "pv-metric pv-tone-" + ["accent", "teal", "ok", "warn"][i]); slot(c, "A", key + "Hint", "div", "pv-note"); });
    const aMiddle = grid(panels.A, "pv-grid3"), aProgress = card(aMiddle, "progress");
    slot(aProgress, "A", "ring"); slot(aProgress, "A", "eta", "p", "pv-note"); slot(aProgress, "A", "stages");
    slot(card(aMiddle, "codes"), "A", "codes");
    const aSource = card(aMiddle, "source"); slot(aSource, "A", "languages"); aSource.append(node("h3", "pv-subheading", L("words"))); slot(aSource, "A", "words"); terminal(panels.A, "A");
    const bTop = card(panels.B, "progress"); slot(bTop, "B", "percent", "p", "pv-metric"); slot(bTop, "B", "eta", "p", "pv-note"); slot(bTop, "B", "progress"); slot(bTop, "B", "stages");
    const bMiddle = grid(panels.B, "pv-grid2"), bRate = card(bMiddle, "rate"); slot(bRate, "B", "rate"); slot(bRate, "B", "rateNote", "p", "pv-note");
    const bOutcomes = card(bMiddle, "outcomes"); slot(bOutcomes, "B", "outcomes"); bOutcomes.append(node("h3", "pv-subheading", L("coverage"))); slot(bOutcomes, "B", "coverage");
    const bBottom = grid(panels.B, "pv-grid21"), bLog = node("div"); bBottom.append(bLog); terminal(bLog, "B"); slot(card(bBottom, "topics"), "B", "topics", "div", "pv-topics");
    slot(panels.C, "C", "status", "pre", "pv-status"); terminal(panels.C, "C");
    const cBottom = grid(panels.C, "pv-grid2 pv-terminal-grid"); slot(card(cBottom, "counters"), "C", "stats"); const textHist = slot(card(cBottom, "codes"), "C", "codes", "pre", "pv-text-hist"); textHist.tabIndex = 0; textHist.setAttribute("aria-label", L("codes"));
    function put(k, key, child) { slots[k][key].replaceChildren(child); }
    function setText(e, value) { if (e.textContent !== value) e.textContent = value; }
    function stages(list) {
      const e = node("div");
      if (!list.length) return node("p", "pv-note", L("noData"));
      list.forEach((s, i) => { const row = node("div", "pv-stage pv-stage-" + s.status), n = node("span", "pv-stage-number", s.status === "succeeded" ? "✓" : s.status === "failed" ? "✗" : i + 1); n.setAttribute("aria-hidden", "true"); row.append(n, node("span", "pv-stage-label", s.label + " · " + L(s.status)), node("b", "pv-percent", pct(s.percent))); e.append(row); }); return e;
    }
    function coverageRows(data) {
      const e = node("div");
      ["lessons", "questions"].forEach(key => { const c = data[key], row = node("div", "pv-topic"); row.append(node("div", "pv-note", `${L(key)}: ${fmt(c.done)} / ${fmt(c.total)} · ${pct(c.percent)}`), C.progress(c.percent, { label: L(key), tone: key === "questions" ? "ok" : "gradient" })); e.append(row); }); return e;
    }
    function renderLog(k, data) {
      const pre = slots[k].log, bottom = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 30, oldScroll = pre.scrollTop;
      const lines = data.slice(-maxLines), fragment = document.createDocumentFragment();
      lines.forEach(e => { const line = node("span", "pv-log-" + e.level), clock = node("span", "pv-time", e.time ? e.time + " " : ""); line.append(clock, document.createTextNode(`[${e.level.toUpperCase()}] ${e.code ? e.code + " " : ""}${e.message}\n`)); fragment.append(line); });
      pre.replaceChildren(fragment); pre.classList.toggle("pv-cursor", current.job.status === "running");
      if (bottom && !panels[k].hidden) pre.scrollTop = pre.scrollHeight; else pre.scrollTop = oldScroll;
      setText(slots[k].lines, `${lines.length} / ${data.length} · ${L("lines")}`);
    }
    function update(raw) {
      if (destroyed) throw new Error("View is destroyed");
      const data = normalize(raw); current = data;
      const j = data.job, rate = data.rateSamples.length ? data.rateSamples[data.rateSamples.length - 1].value : null;
      const eta = j.status === "running" && j.etaSeconds !== null ? `${L("eta")} ${fmt(j.etaSeconds)} ${L("seconds")}` : "—";
      setText(title, j.label || j.id || L("noData"));
      state.className = "pv-state badge " + (j.status === "succeeded" ? "ok" : j.status === "failed" ? "bad" : j.status === "running" ? "info" : "");
      setText(state, ({ succeeded: "✓ ", failed: "✗ ", cancelled: "■ ", running: "▶ ", idle: "○ " }[j.status]) + L(j.status));
      ["files", "lessons", "questions", "issues"].forEach(key => setText(slots.A[key], fmt(data.metrics[key])));
      setText(slots.A.filesHint, `${fmt(rate)} ${L("unit")}`);
      setText(slots.A.lessonsHint, data.topics.length ? `${data.topics.filter(t => t.status === "succeeded").length} / ${data.topics.length} · ${L("topics")}` : L("noData"));
      setText(slots.A.questionsHint, `${L("coverage")}: ${pct(data.coverage.questions.percent)}`);
      setText(slots.A.issuesHint, `${L("errors")}: ${fmt(data.metrics.errors)}`);
      put("A", "ring", C.ring(j.percent, { label: L("progress") })); setText(slots.A.eta, eta);
      put("A", "stages", stages(data.stages)); put("B", "stages", stages(data.stages));
      put("A", "codes", C.countBars(data.issuesByCode, { label: L("codes"), locale }));
      put("A", "languages", C.distribution(data.languages, { label: L("source"), locale }));
      put("A", "words", data.lessonWords.length ? C.histogram(data.lessonWords, { label: L("words") }) : node("p", "pv-note", L("noData")));
      setText(slots.B.percent, pct(j.percent)); setText(slots.B.eta, eta); put("B", "progress", C.progress(j.percent, { label: L("progress") }));
      put("B", "rate", C.rateLine(data.rateSamples, { label: L("rate"), unit: L("unit"), averageLabel: L("average") }));
      const recent = data.rateSamples.slice(-40), mean = recent.length ? recent.reduce((n, s) => n + s.value, 0) / recent.length : null;
      setText(slots.B.rateNote, `${L("current")}: ${fmt(rate)} ${L("unit")} · ${L("average")}: ${fmt(mean)} ${L("unit")}`);
      put("B", "outcomes", C.distribution(data.outcomes, { label: L("outcomes"), locale })); put("B", "coverage", coverageRows(data.coverage));
      const topics = node("div");
      if (!data.topics.length) topics.append(node("p", "pv-note", L("noData")));
      data.topics.forEach(t => { const row = node("div", "pv-topic"); row.append(node("div", "pv-note", `${t.label} · ${L(t.status)} · ${pct(t.percent)}`), C.progress(t.percent, { label: t.label })); topics.append(row); }); put("B", "topics", topics);
      const terminalStatus = slots.C.status; terminalStatus.replaceChildren();
      [["info", `${j.id || "process"} · ${j.label}\n${L(j.status)}\n`], ["progress", `[${C.textBar(j.percent, 40)}] ${pct(j.percent)} · ${eta}\n`], ["info", `${L("files")} ${fmt(data.metrics.files)} · ${L("lessons")} ${fmt(data.metrics.lessons)} · ${L("questions")} ${fmt(data.metrics.questions)}\n`], ["warn", `${L("issues")} ${fmt(data.metrics.issues)} · `], ["error", `${L("errors")} ${fmt(data.metrics.errors)}\n`], ["progress", `${L("rate")} ${C.sparkline(data.rateSamples.map(s => s.value))} ${fmt(rate)} ${L("unit")}`]].forEach(([level, value]) => terminalStatus.append(node("span", "pv-log-" + level, value)));
      const table = node("table", "pv-stats"), caption = node("caption", "pv-note", L("counters")); table.append(caption);
      const body = node("tbody"); ["files", "lessons", "questions", "issues", "errors"].forEach(k => { const row = node("tr"), h = node("th", "", L(k)); h.scope = "row"; row.append(h, node("td", "", fmt(data.metrics[k]))); body.append(row); });
      ["lessons", "questions"].forEach(k => { const row = node("tr"), h = node("th", "", L("coverage") + " · " + L(k)); h.scope = "row"; row.append(h, node("td", "", pct(data.coverage[k].percent))); body.append(row); });
      const timeRow = node("tr"), timeHeading = node("th", "", L("elapsed")); timeHeading.scope = "row"; timeRow.append(timeHeading, node("td", "", `${fmt(j.elapsedSeconds)} ${L("seconds")}`)); body.append(timeRow); table.append(body); put("C", "stats", table);
      setText(slots.C.codes, C.textHistogram(data.issuesByCode)); ["A", "B", "C"].forEach(k => renderLog(k, data.logs));
    }
    setMode(mode);
    update({ schemaVersion: 1, job: { status: "idle" } });
    return { update, setMode, getMode: () => mode, destroy: () => { controller.abort(); shell.remove(); current = null; destroyed = true; } };
  }
  window.HomenS = window.HomenS || {};
  window.HomenS.processView = { mount };
})();
