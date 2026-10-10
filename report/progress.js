/* Local AI Lab · © 2026 Serhii Khomenko · https://homensai.com/ */
/* "Test progress" page: the stage plan of the report builder (live-data.json, field plan) shown with the process view
   A/B/C of HomenS.AI Style 1.4.0. Only display: nothing here starts or stops a test. */
(() => {
  const H = window.HomenS;
  const lang = (window.i18n && window.i18n.lang()) || "ru";
  const box = document.getElementById("connection");
  const view = H.processView.mount(document.getElementById("process"), {
    locale: lang, storageKey: "local-ai-lab.progress-mode", maxLogLines: 300,
    labels: {
      files: ["Моделей в плане", "Models in the plan", "Modelle im Plan"],
      lessons: ["Этапов завершено", "Stages finished", "Phasen abgeschlossen"],
      questions: ["Результатов модель × этап", "Results model × stage", "Ergebnisse Modell × Phase"],
      issues: ["Снято по правилу 64K", "Removed by the 64K rule", "Durch die 64K-Regel entfernt"],
      errors: ["Не загрузились", "Failed to load", "Nicht geladen"],
      topics: ["Модели текущего этапа", "Models of the current stage", "Modelle der aktuellen Phase"],
      codes: ["Снятые модели", "Removed models", "Entfernte Modelle"],
      outcomes: ["Готово по этапам", "Done per stage", "Erledigt je Phase"],
      log: ["Последние итоги этапов", "Latest stage results", "Letzte Phasenergebnisse"],
      idle: ["Сейчас этап не идёт", "No stage is running", "Keine Phase läuft"],
      rate: ["Скорость", "Rate", "Geschwindigkeit"], unit: ["мин/модель", "min/model", "Min./Modell"],
      source: ["Этапы по состоянию", "Stages by state", "Phasen nach Status"],
      words: ["Время на модель", "Time per model", "Zeit pro Modell"],
    },
  });
  const STATE = {done: "succeeded", running: "running", paused: "pending", waiting: "pending"};
  const clockOf = iso => (iso ? new Date(iso).toLocaleTimeString(lang, {hour: "2-digit", minute: "2-digit"}) : "");
  const clamp = n => Math.max(0, Math.min(100, Math.round(n)));

  function snapshot(data) {
    const plan = data.plan || {stages: [], overall: {}};
    const o = plan.overall || {}, stages = plan.stages || [];
    const running = stages.find(s => s.state === "running");
    const counted = stages.filter(s => s.total);
    const stagePercent = s => (s.state === "done" ? 100 : s.total ? clamp(100 * s.done / s.total) : 0);
    const excluded = new Map();
    stages.forEach(s => (s.excluded || []).forEach(x => excluded.set(x.model, x.reason)));
    const failed = (data.models || []).filter(m => m.failed).length;
    const done = stages.filter(s => s.state === "done").length;
    return {
      schemaVersion: 1,
      job: {
        id: "local-ai-lab", label: running ? running.title : "Испытания моделей",
        status: stages.length && o.finished ? "succeeded" : running ? "running" : "idle",
        percent: clamp(o.percent || 0),
        elapsedSeconds: o.elapsed_minutes != null ? o.elapsed_minutes * 60 : null,
        etaSeconds: running && o.remaining_minutes != null ? o.remaining_minutes * 60 : null,
      },
      metrics: {files: plan.models_total ?? null, lessons: done, questions: counted.reduce((n, s) => n + s.done, 0), issues: excluded.size, errors: failed},
      coverage: {
        lessons: {done, total: stages.length},
        questions: {done: counted.reduce((n, s) => n + Math.min(s.done, s.total), 0), total: counted.reduce((n, s) => n + s.total, 0)},
      },
      stages: stages.map(s => ({id: s.id, label: s.title, status: STATE[s.state] || "pending", percent: stagePercent(s)})),
      topics: running ? [
        ...(running.current ? [{id: "current", label: running.current, status: "running", percent: clamp(running.current_pct || 0)}] : []),
        ...(running.next_models || []).map((m, i) => ({id: "next-" + i, label: m, status: "pending", percent: 0})),
      ] : [],
      issuesByCode: [...excluded.keys()].map(m => ({label: m, value: 1, tone: "warn"})),
      languages: [["Готово", "done", "ok"], ["Идёт", "running", "accent"], ["Пауза", "paused", "warn"], ["Ждёт", "waiting", "muted"]]
        .map(([label, state, tone]) => ({label, value: stages.filter(s => s.state === state).length, tone})).filter(x => x.value),
      outcomes: counted.map(s => ({label: s.title, value: s.done, tone: s.state === "done" ? "ok" : s.state === "running" ? "accent" : "muted"})),
      logs: stages.filter(s => s.last || s.fact).map(s => ({
        time: clockOf(s.log_updated_utc), level: s.state === "done" ? "ok" : s.state === "running" ? "progress" : "info",
        code: s.id, message: `${s.title}: ${s.fact || s.last}`,
      })),
    };
  }

  async function poll() {
    try {
      const r = await fetch("/report/live-data.json", {cache: "no-store"});
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      view.update(snapshot(await r.json()));
      box.hidden = true;
    } catch (e) {
      box.hidden = false;
      box.className = "notice bad";
      box.textContent = "Нет данных испытаний: " + e.message;   // the last real numbers stay on the page
    }
  }
  poll();
  setInterval(poll, 15000);
})();
