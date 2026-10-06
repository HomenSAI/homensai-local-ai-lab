(() => {
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const fmt = (v, d = 0) => v == null ? "—" : Number(v).toLocaleString("ru-RU", {maximumFractionDigits: d});
  const ago = iso => {
    const t = Date.parse(iso || ""); if (!t) return "—";
    const s = Math.max(0, (Date.now() - t) / 1000);
    return s < 60 ? `${Math.round(s)} с назад` : s < 5400 ? `${Math.round(s / 60)} мин назад` : s < 172800 ? `${Math.round(s / 3600)} ч назад` : `${Math.round(s / 86400)} дн назад`;
  };
  const when = iso => iso ? new Date(iso).toLocaleString("ru-RU", {day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"}) : "—";
  const size = n => n > 1048576 ? `${(n / 1048576).toFixed(1)} МБ` : `${Math.max(1, Math.round(n / 1024))} КБ`;
  const signature = m => JSON.stringify([m.total, m.pp, m.tg, m.vram_mib, m.max_ctx, m.failed, m.tested_utc]);
  const raw = (m, c) => m.raw?.[c] ? `${m.raw[c][0]}/${m.raw[c][1]}` : "—";
  let data = null, version = null, lastChecked = null, previous = new Map();

  function render() {
    if (!data) return;
    renderPlan();
    const models = data.models || [];
    const ok = models.filter(m => !m.failed), bad = models.length - ok.length;
    $("liveCount").textContent = `${models.length} ${models.length === 1 ? "модель" : "моделей"}${bad ? ` · ${bad} не загрузилась` : ""}`;
    $("liveStatus").textContent = data.status || "Статус прогона не указан в report.md.";
    const maxTotal = Math.max(...ok.map(m => m.total || 0), 1);
    $("liveBody").innerHTML = models.map((m, i) => {
      const changed = previous.size && previous.get(m.model) !== signature(m);
      const fresh = Date.now() - Date.parse(m.tested_utc || 0) < 3600e3;
      if (m.failed) return `<tr class="${changed ? "flash" : ""}"><td>${i + 1}</td><td><strong>${esc(m.model)}</strong><code>${esc(m.file || "")}</code></td><td colspan="10" class="bad">не загрузилась: ${esc(m.error)}</td><td>${when(m.tested_utc)}</td></tr>`;
      const warn = m.fits === false ? ` <span class="tag" title="часть слоёв на CPU">ngl ${esc(m.ngl)}</span>` : "";
      return `<tr class="${changed ? "flash" : ""}"><td>${i + 1}</td>
        <td><strong>${esc(m.model)}${fresh ? ' <span class="tag new">свежее</span>' : ""}</strong><code>${esc((m.file || "").split("/").pop())}</code></td>
        <td>${esc(m.quant || "—")}</td><td>${fmt(m.size_gb, 2)}</td><td>${fmt(m.vram_mib)}${warn}</td>
        <td>${fmt(m.pp, 0)}</td><td>${fmt(m.tg, 1)}</td><td>${m.max_ctx ? Math.round(m.max_ctx / 1024) + "K" : "—"}</td>
        <td>${raw(m, "Русский")}</td><td>${raw(m, "Логика")}</td><td>${raw(m, "Код")}</td>
        <td class="score-cell"><div class="bar-track"><div class="bar-fill" style="width:${(m.total || 0) / maxTotal * 100}%"></div></div><b>${m.total ?? "—"}%</b></td>
        <td>${when(m.tested_utc)}</td></tr>`;
    }).join("") || '<tr><td colspan="13" class="muted">Результатов пока нет.</td></tr>';
    previous = new Map(models.map(m => [m.model, signature(m)]));
    $("liveActivity").innerHTML = (data.activity || []).map(a => `<li><code>${esc(a.path)}</code><span>${size(a.size)} · ${ago(a.modified_utc)}</span></li>`).join("");
    const fb = (data.fallback || []).filter(x => x.guard_killed || x.error);
    $("liveFallback").hidden = !fb.length;
    $("liveFallback").innerHTML = fb.length ? `<strong>Прерванные загрузки (${fb.length})</strong> — сторож RAM или ошибка контейнера: ${fb.slice(0, 6).map(x => `${esc(x.model)} ${esc(x.ctx)}`).join(", ")}${fb.length > 6 ? "…" : ""}` : "";
    renderClock();
  }

  function renderPlan() {
    const box = $("livePlan"), run = (data.plan?.stages || []).find(s => s.state === "running") || {};
    const mins = m => m < 90 ? `${Math.round(m)} мин` : `${Math.floor(m / 60)} ч ${String(Math.round(m % 60)).padStart(2, "0")} мин`;
        const cur = run.current_pct != null ? `<div class="live-plan-row"><span>Сейчас: <b>${esc(run.current || "подготовка")}</b></span><div class="live-bar"><i style="width:${run.current_pct}%"></i></div><b>${run.pct_exact ? "" : "≈ "}${run.current_pct}%</b></div>` : "";
    const o = data.plan?.overall;
    const all = o && !o.finished ? `<div class="live-plan-row"><span>До конца всех тестов: прошло ${mins(o.elapsed_minutes)}, осталось ≈ ${mins(o.remaining_minutes)}</span><div class="live-bar"><i style="width:${o.percent}%"></i></div><b>${o.percent}%</b></div>` : "";
    box.innerHTML = cur + all;
    box.hidden = !(cur || all);
  }
  function renderClock() {
    if (!data) return;
    const stale = Date.now() - Date.parse(data.latest_result_utc || 0) > 6 * 3600e3;
    $("liveClock").innerHTML = `Последний результат: <b>${ago(data.latest_result_utc)}</b> · страница проверила: ${lastChecked ? ago(lastChecked) : "—"}${stale ? ' · <span class="bad">новых результатов давно нет</span>' : ""}`;
    $("livePulse").className = "live-pulse" + (stale ? " stale" : "");
  }

  async function poll() {
    try {
      const status = await (await fetch("/report/live-status.json", {cache: "no-store"})).json();
      lastChecked = status.checked_utc;
      if (status.version !== version) {
        data = await (await fetch("/report/live-data.json", {cache: "no-store"})).json();
        version = data.version;
        render();
      } else renderClock();
      $("liveError").hidden = true;
    } catch (e) {
      $("liveError").hidden = false;
      $("liveError").textContent = "Данные свежих испытаний недоступны: " + e.message;
    }
  }
  poll();
  setInterval(poll, 10000);
  setInterval(renderClock, 5000);
})();
