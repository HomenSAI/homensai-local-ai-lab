(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const fmt = (v, digits=2) => v === null || v === undefined || v === "" ? "n/a" : (typeof v === "number" ? Number(v).toLocaleString("ru-RU",{maximumFractionDigits:digits}) : esc(v));
  const mib = (bytes) => bytes ? `${fmt(bytes/1048576)} MiB` : "n/a";
  const dataUrl = "/report/report-data.json";
  let data;
  function fillSelect(id, values, first) {
    const node=$(id); node.innerHTML=`<option value="">${esc(first)}</option>`+values.map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join("");
  }
  function summaryValue(run,key) { return run.summary?.[key] ?? run.summary?.[key.replaceAll("_","-")] ?? null; }
  function renderAssets() {
    $("assetsBody").innerHTML=data.assets.map(a=>`<tr><td><strong>${esc(a.model_name)}</strong></td><td><code>${esc(a.filename||"")}</code></td><td>${esc(a.quant||"n/a")}</td><td>${a.size_bytes?`${fmt(a.size_bytes,0)} B`:"pending"}</td><td><code>${esc(a.sha256||"pending")}</code></td><td>${esc(a.runtime||"")}</td><td>${esc(a.status)}</td></tr>`).join("");
  }
  function selectedRuns() {
    const model=$("modelFilter").value, suite=$("suiteFilter").value, phase=$("phaseFilter").value;
    return data.runs.filter(r=>(!model||r.model_name===model)&&(!suite||r.suite===suite)&&(!phase||r.phase===phase));
  }
  function median(values) {
    const sorted=values.filter(Number.isFinite).sort((a,b)=>a-b);
    if(!sorted.length)return null;
    const mid=Math.floor(sorted.length/2);
    return sorted.length%2?sorted[mid]:(sorted[mid-1]+sorted[mid])/2;
  }
  function speedGroups(runs) {
    const groups=new Map();
    for(const r of runs) {
      const rate=Number(r.summary?.tg_tok_s);
      if(r.phase!=="server"||r.suite!=="accelerator_ab"||r.status!=="complete"||!Number.isFinite(rate)||rate<=0||/benchmark|validation|smoke/i.test(r.model_name))continue;
      const variant=r.config?.variant||"default",key=`${r.model_name}|||${variant}`;
      const group=groups.get(key)||{model:r.model_name,variant,rates:[],vram:[]};
      group.rates.push(rate);
      const memory=Number(r.summary?.vram_peak_mib);if(Number.isFinite(memory)&&memory>0)group.vram.push(memory);
      groups.set(key,group);
    }
    return [...groups.values()].map(g=>({model:g.model,variant:g.variant,count:g.rates.length,rate:median(g.rates),vram:median(g.vram)})).sort((a,b)=>b.rate-a.rate);
  }
  function qualityGroups(runs, cleanOnly=false) {
    const byId=new Map(runs.map(r=>[r.run_id,r])),groups=new Map();
    for(const score of data.scores||[]) {
      const run=byId.get(score.run_id),correct=Number(score.correct),attempted=Number(score.attempted),total=Number(score.total_cases);
      if(!run||run.phase!=="server"||score.correct==null||!Number.isFinite(correct)||!Number.isFinite(attempted)||attempted<=0||!Number.isFinite(total)||total<=0)continue;
      const coverage=Number(score.coverage??attempted/total),apiErrors=Number(score.api_errors||0),truncated=Number(score.truncated||0);
      if(cleanOnly&&(run.status!=="complete"||apiErrors>0||truncated>0||coverage<0.999))continue;
      const key=`${run.model_name}|||${score.suite}`;
      const group=groups.get(key)||{model:run.model_name,suite:score.suite,correct:0,attempted:0,total:0,apiErrors:0,truncated:0,runs:0,completeRuns:0};
      group.correct+=correct;group.attempted+=attempted;group.total+=total;group.apiErrors+=apiErrors;group.truncated+=truncated;group.runs++;
      if(run.status==="complete")group.completeRuns++;
      groups.set(key,group);
    }
    return [...groups.values()].map(g=>({...g,accuracy:g.correct/g.attempted,coverage:g.attempted/g.total})).sort((a,b)=>a.suite.localeCompare(b.suite)||b.accuracy-a.accuracy);
  }
  function renderSpeedChart(runs) {
    const groups=speedGroups(runs),chart=$("speedChart");
    $("speedCount").textContent=groups.length?`${groups.length} профилей`:"нет данных";
    const visible=groups.slice(0,14),max=Math.max(1,...visible.map(x=>x.rate));
    chart.innerHTML=visible.map(x=>{
      const label=`${x.model} · ${x.variant}`;
      return `<div class="bar-row"><span title="${esc(label)}">${esc(label)}</span><div class="bar-track" role="img" aria-label="${esc(label)}: ${fmt(x.rate)} токенов в секунду"><div class="bar-fill" style="width:${Math.max(1,x.rate/max*100)}%"></div></div><b>${fmt(x.rate)} tok/s</b></div>`;
    }).join("")||'<p class="muted">Для выбранных фильтров нет завершённых серверных замеров скорости.</p>';
  }
  function renderQualityViews(runs) {
    const groups=qualityGroups(runs),chart=$("qualityChart");
    $("qualityCount").textContent=groups.length?`${groups.length} оценок`:"нет данных";
    $("scoreCount").textContent=`${groups.length} строк`;
    const visible=[...groups].sort((a,b)=>b.accuracy-a.accuracy).slice(0,14);
    chart.innerHTML=visible.map(g=>{
      const label=`${g.model} · ${g.suite}`,accuracy=Math.max(0,Math.min(100,g.accuracy*100));
      return `<div class="bar-row quality-bar"><span title="${esc(label)}">${esc(label)}</span><div class="bar-track" role="img" aria-label="${esc(label)}: точность ${fmt(accuracy)} процентов, полнота ${fmt(g.coverage*100)} процентов"><div class="bar-fill" style="width:${accuracy}%"></div></div><b>${fmt(accuracy)}%</b><small>покрытие ${fmt(g.coverage*100)}%</small></div>`;
    }).join("")||'<p class="muted">Объективных оценок для выбранных фильтров нет.</p>';
    $("scoresBody").innerHTML=groups.map(g=>`<tr><td><strong>${esc(g.model)}</strong></td><td>${esc(g.suite)}</td><td>${fmt(g.correct,0)} / ${fmt(g.attempted,0)} из ${fmt(g.total,0)} · ${fmt(g.accuracy*100)}%</td><td>${fmt(g.coverage*100)}%</td><td>${fmt(g.apiErrors,0)}</td><td>${fmt(g.truncated,0)}</td><td>${g.completeRuns} / ${g.runs}</td></tr>`).join("")||'<tr><td colspan="7" class="muted">Для выбранных фильтров нет объективно оцениваемых результатов.</td></tr>';
  }
  function renderRecommendations() {
    const rows=[],speeds=speedGroups(data.runs),fmtMemory=value=>value==null?"n/a":`${fmt(value/1024)} GiB`;
    const add=(scenario,profile,evidence,advice)=>rows.push({scenario,profile,evidence,advice});
    const fastest=speeds.find(x=>x.count>=3);
    if(fastest) {
      const baseline=speeds.find(x=>x.model===fastest.model&&/off/i.test(x.variant));
      const comparison=baseline?`; DSpark OFF — ${fmt(baseline.rate)} tok/s, ${fmtMemory(baseline.vram)} VRAM`:"";
      add("Максимальная скорость",`${fastest.model} · ${fastest.variant}`,`Медиана ${fmt(fastest.rate)} tok/s по ${fastest.count} завершённым замерам; пик VRAM ${fmtMemory(fastest.vram)}${comparison}.`,"Выбирать, когда важна скорость вывода; сравните дополнительный расход VRAM.");
    }
    const math=qualityGroups(data.runs,true).filter(g=>g.suite==="math_10min"&&g.coverage>=0.999&&g.apiErrors===0).sort((a,b)=>b.accuracy-a.accuracy)[0];
    if(math)add("Математические задачи",math.model,`${fmt(math.correct,0)} из ${fmt(math.attempted,0)} верных · покрытие ${fmt(math.coverage*100)}% · без API-ошибок.`,"Лучший результат среди завершённых прогонов набора math_10min.");
    const n2=speeds.find(x=>x.model==="Qwen3.5-9B"&&/MTP n-max=2/i.test(x.variant));
    const n4=speeds.find(x=>x.model==="Qwen3.5-9B"&&/MTP n-max=4/i.test(x.variant));
    const off=speeds.find(x=>x.model==="Qwen3.5-9B"&&/MTP OFF/i.test(x.variant));
    if(n2&&n4) {
      const relation=n2.rate>=n4.rate*0.97&&n2.vram!=null&&n4.vram!=null&&n2.vram<n4.vram;
      add("Qwen3.5 · баланс MTP","MTP n-max=2",`n=2: ${fmt(n2.rate)} tok/s и ${fmtMemory(n2.vram)} VRAM; n=4: ${fmt(n4.rate)} tok/s и ${fmtMemory(n4.vram)}${off?`; MTP OFF: ${fmt(off.rate)} tok/s`:""}.`,relation?"По этим замерам n=2 почти не уступает n=4 по скорости и занимает меньше VRAM.":"Сверьте скорость и VRAM n=2/n=4 под своей нагрузкой.");
    }
    const longContext=data.runs.filter(r=>r.phase==="server"&&r.suite==="context_probe"&&r.status==="complete"&&Number(r.config?.context)>=65536&&Number(r.summary?.vram_peak_mib)>0).sort((a,b)=>a.summary.vram_peak_mib-b.summary.vram_peak_mib)[0];
    if(longContext)add("Контекст 64K",longContext.model_name,`Проба на ${fmt(longContext.config.context,0)} токенов завершена; пиковая VRAM ${fmtMemory(longContext.summary.vram_peak_mib)}.`,"Подходит как отправная точка для длинных документов; учитывайте запас памяти под параллельную нагрузку.");
    const dual=data.runs.find(r=>r.phase==="server"&&r.suite==="dual_resident_stress"&&r.status==="complete"&&r.summary?.endpoints_healthy&&!r.summary?.runtime_errors);
    if(dual)add("Две модели одновременно","MiniCPM5 + Spark",`Обе точки API оставались доступны; пик VRAM ${fmtMemory(dual.summary.peak_vram_mib)}, свободно на пике ${fmtMemory(dual.summary.free_at_peak_mib)}.`,"Можно держать обе модели загруженными в проверенной конфигурации.");
    const special=data.runs.filter(r=>r.phase==="server"&&r.status==="complete"&&["vision_smoke","whisper_smoke","image_generation"].includes(r.suite));
    if(special.length) {
      const details=special.map(r=>{
        const seconds=Number(r.summary?.elapsed_seconds??r.summary?.active_seconds);
        return `${r.model_name}: ${r.suite.replace("_smoke", " smoke")}${Number.isFinite(seconds)&&seconds>0?`, ${fmt(seconds)} с`:""}`;
      }).join("; ");
      add("Изображения и аудио",special.map(r=>r.model_name).join(" · "),details,"Эти проверки подтверждают запуск профилей; это smoke-тесты, не сравнительная оценка качества.");
    }
    $("recommendationsBody").innerHTML=rows.map(r=>`<tr><td><strong>${esc(r.scenario)}</strong></td><td>${esc(r.profile)}</td><td>${esc(r.evidence)}</td><td class="status">${esc(r.advice)}</td></tr>`).join("")||'<tr><td colspan="4" class="muted">Пока недостаточно завершённых измерений для рекомендаций.</td></tr>';
    const complete=data.runs.filter(r=>r.phase==="server"&&r.status==="complete").length;
    $("recommendationNote").textContent=`Автоматическая сводка по ${complete} завершённым серверным прогонам. Для советов по скорости использованы повторные A/B-замеры; советы по точности учитывают только полное покрытие и ноль API-ошибок.`;
  }
  function renderRuns(runs) {
    $("runCount").textContent=`${runs.length} запусков`;
    $("runsBody").innerHTML=runs.map(r=>{
      const s=r.summary||{}, asset=data.assets.find(a=>a.asset_id===r.model_asset_id)||{};
      const statusClass=/blocked|fail|error/i.test(r.status)?"status blocked":"status";
      const score=s.reading_first_cycle||s.math_first_cycle||s.objective||{};
      const metric=score.correct!==undefined?`${score.correct}/${score.total??score.attempted??"?"} · cov ${fmt(score.coverage_percent ?? (score.coverage!==undefined?score.coverage*100:null))}%`:s.coverage||"n/a";
      const gpu=(s.gpu_util_avg_percent!==undefined?`${fmt(s.gpu_util_avg_percent)}%`:"n/a")+" / "+(s.vram_peak_mib!==undefined?`${fmt(s.vram_peak_mib,0)} MiB`:"n/a");
      return `<tr><td><strong>${esc(r.model_name)}</strong><code>${esc(r.gguf||asset.filename||"")}</code></td><td>${esc(r.suite)}</td><td>${esc(r.phase)}</td><td class="${statusClass}">${esc(r.status)}</td><td>${fmt(s.load_seconds)} s</td><td>${fmt(s.pp_tok_s)}</td><td>${fmt(s.tg_tok_s)}</td><td>${fmt(s.ttft_seconds)} s</td><td>${s.rss_peak_bytes?mib(s.rss_peak_bytes):fmt(s.ram_peak_sampled_gib?`${s.ram_peak_sampled_gib.toFixed(2)} GiB`:null)}</td><td>${gpu}</td><td>${metric}</td></tr>`;
    }).join("")||`<tr><td colspan="11" class="muted">Под фильтр ничего не попало.</td></tr>`;
  }
  function renderResponses(runs) {
    const ids=new Set(runs.map(r=>r.run_id));
    const query=$("searchFilter").value.trim().toLocaleLowerCase();
    const rows=data.responses.filter(r=>ids.has(r.run_id)&&(!query||`${r.case_id} ${r.prompt||""} ${r.answer||""}`.toLocaleLowerCase().includes(query))).slice(0,600);
    $("responseCount").textContent=`${rows.length}${rows.length===600?"+":""} записей`;
    $("responses").innerHTML=rows.map(r=>{
      const run=data.runs.find(x=>x.run_id===r.run_id);
      const headline=`${run?.model_name||r.run_id} · ${r.suite}/${r.case_id} · cycle ${r.cycle||1} · ${fmt(r.duration_seconds)} s${r.after_deadline?" · after deadline":""}${r.error?" · ERROR":""}`;
      return `<details><summary>${esc(headline)}<span class="tag">${esc(r.finish_reason||"no finish reason")}</span></summary><div class="response-content"><h3>PROMPT</h3><pre>${esc(r.prompt||JSON.stringify(r.request?.messages||[],null,2))}</pre><h3>ОТВЕТ</h3><pre>${esc(r.answer||"")}</pre>${r.error?`<h3>ОШИБКА</h3><pre>${esc(r.error)}</pre>`:""}<h3>RAW METRICS</h3><pre>${esc(JSON.stringify({prompt_tokens:r.prompt_tokens,completion_tokens:r.completion_tokens,timings:r.timings,after_deadline:r.after_deadline,raw:r.raw},null,2))}</pre></div></details>`;
    }).join("")||`<p class="muted">Ответы появятся после импорта raw logs.</p>`;
  }
  function render() {
    const runs=selectedRuns();
    const resp=data.responses.filter(r=>runs.some(x=>x.run_id===r.run_id));
    const successful=runs.filter(r=>r.phase==="server"&&r.status==="complete").length;
    const generated=new Date(data.generated_utc);
    const updated=Number.isNaN(generated.getTime())?"—":generated.toLocaleString("ru-RU",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"});
    const cards=[
      ["Прогонов в выборке",runs.length], ["Успешных GPU-прогонов",successful], ["Ответов для просмотра",resp.length],
      ["Обновлено",updated]
    ];
    $("cards").innerHTML=cards.map(([k,v])=>`<div class="card"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join("");
    renderRuns(runs); renderResponses(runs);renderSpeedChart(runs);renderQualityViews(runs);
  }
  fetch(dataUrl).then(r=>{if(!r.ok)throw new Error(`Не удалось загрузить ${dataUrl}: HTTP ${r.status}`);return r.json()}).then(value=>{
    data=value;
    const generated=new Date(value.generated_utc),generatedText=Number.isNaN(generated.getTime())?"—":generated.toLocaleString("ru-RU");
    $("generated").textContent=`База испытаний обновлена ${generatedText} · ${value.runs.length} прогонов · ${value.responses.length} ответов`;
    const notes=[];
    if(value.baseline_quant_note)notes.push(value.baseline_quant_note+" Сравнение производительности между стендами не является чистым сравнением моделей; аппаратные условия и quant различаются.");
    if(value.gpu_benchmark_status==="blocked")notes.push(value.gpu_benchmark_blocker+" В таблице сейчас только ноутбучный baseline.");
    else if(!value.runs.some(x=>x.phase==="server"))notes.push("GPU-запуски на RTX 3080 пока отсутствуют. В таблице сейчас только ноутбучный baseline.");
    else if(value.gpu_benchmark_status==="partial")notes.push("База сохраняет и ранние частичные/OOM-попытки, и чистые завершённые прогоны; два чистых полного протокола завершились 175/175 без API-ошибок.");
    if(notes.length){$("notice").hidden=false;$("notice").textContent=notes.join(" ");}
    fillSelect("modelFilter",[...new Set(value.runs.map(x=>x.model_name))].sort(),"Все модели");
    fillSelect("suiteFilter",[...new Set(value.runs.map(x=>x.suite))].sort(),"Все suites");
    fillSelect("phaseFilter",[...new Set(value.runs.map(x=>x.phase))].sort(),"Все источники");
    renderAssets();renderRecommendations(); ["modelFilter","suiteFilter","phaseFilter","searchFilter"].forEach(id=>$(id).addEventListener("input",render));
    render();
  }).catch(error=>{ $("generated").textContent=error.message; $("notice").hidden=false; $("notice").textContent="Откройте отчёт через python -m http.server (скрипт scripts/serve-report.ps1), чтобы браузер разрешил загрузить JSON."; });
})();
