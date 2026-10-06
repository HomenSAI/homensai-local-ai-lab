(() => {
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  let catalog = [], selected = null, status = null, pollTimer = null, currentJob = null, chatMessages = [], unloadTimer = null;
  const gpuHistory = [];
  const gpuHistoryLimit = 60;
  const tokenSpeedHistory = new Map();
  const api = async (url, options={}) => {
    const r = await fetch(url, {cache:"no-store", ...options, headers:{"Content-Type":"application/json",...(options.headers||{})}});
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
    return data;
  };
  function addMessage(role, text, meta="") {
    const log=$("chatLog");
    const empty=log.querySelector(".empty-state"); if (empty) empty.remove();
    const node=document.createElement("div"); node.className=`bubble ${role}`;
    node.textContent=text;
    const stamp=new Date().toLocaleString((window.i18n&&{ru:"ru-RU",en:"en-GB",de:"de-DE"}[window.i18n.lang()])||"ru-RU",{day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:false});
    {const m=document.createElement("div");m.className="meta";m.textContent=(meta?meta+" · ":"")+stamp;node.appendChild(m);}
    log.appendChild(node);log.scrollTop=log.scrollHeight;
  }
  function selectModel(key) {
    const model=catalog.find(x=>x.key===key); if(!model||!["chat","vision"].includes(model.kind))return;
    const changed=selected?.key!==key;
    selected=model;
    if(changed){chatMessages=[];$("visionFile").value="";$("visionFileName").textContent="";}
    document.querySelectorAll(".catalog-card").forEach(n=>n.classList.toggle("selected",n.dataset.key===key));
    $("chatModel").value=key;
    $("imageAttachRow").hidden=model.kind!=="vision";
    $("interactionTitle").textContent=model.kind==="vision"?"Диалог с изображением":"Диалог с моделью";
    $("apiAddress").textContent="API: http://"+location.hostname+":8080/v1";
    if(changed)renderChatEmpty();
    renderChatState();
  }
  function renderChatEmpty() {
    $("chatLog").innerHTML='<div class="empty-state">'+(selected?(selected.kind==="vision"?"Прикрепите изображение и задайте вопрос.":"Напишите сообщение.")+(["running","busy"].includes(catalogState(selected))?"":" Шлюз загрузит модель при первом сообщении."):"Выберите модель в каталоге или в списке справа сверху.")+'</div>';
  }
  function renderChatState() {
    const badge=$("chatModelState"), send=$("sendBtn"), input=$("promptInput");
    const st=selected?catalogState(selected):null;
    const labels={running:"Запущена",busy:"Генерирует",loading:"Загружается…",stopping:"Выгружается…",idle:"Не загружена",missing:"Нет файла"};
    badge.textContent=selected?labels[st]:"Модель не выбрана";
    badge.className="badge"+(st==="running"||st==="busy"?" on":st==="loading"||st==="stopping"?" warn":"");
    input.disabled=!selected;
    if(!send.dataset.sending)send.disabled=!selected;
    $("chatHint").textContent=!selected?"Сначала выберите модель.":st==="idle"?"Модель не в памяти: первый ответ придёт после загрузки (до минуты).":selected.kind==="vision"?"Vision API · можно добавить изображение":"Локальный OpenAI-compatible API";
    $("chatPanel").classList.toggle("dim",!selected);
  }
  function syncChatModels() {
    const chats=catalog.filter(m=>m.exists&&["chat","vision"].includes(m.kind));
    const sig=chats.map(m=>m.key).join("|");
    const select=$("chatModel");
    if(select.dataset.sig!==sig){
      select.dataset.sig=sig;
      select.innerHTML='<option value="" disabled>Выберите модель…</option>'+chats.map(m=>`<option value="${esc(m.key)}">${esc(m.name)}</option>`).join("");
      select.value=selected?.key||"";
    }
  }
  const stoppingKeys=new Set();
  function loadingJob() {
    return [currentJob,status?.job].find(j=>j&&["queued","running"].includes(j.status)&&j.model_key);
  }
  function catalogState(m) {
    if(!m.exists)return "missing";
    if(stoppingKeys.has(m.key))return "stopping";
    const live=(status?.active_models||[]).find(x=>!x.external&&x.key===m.key);
    if(live)return live.activity?.busy?"busy":live.api_ready?"running":"loading";
    return loadingJob()?.model_key===m.key?"loading":"idle";
  }
  function renderCatalog() {
    if(!catalog.length){$("modelList").innerHTML='<p class="muted">Каталог пуст или шлюз недоступен.</p>';return;}
    const labels={running:"Запущена",busy:"Генерирует",loading:"Загружается…",stopping:"Выгружается…",idle:"Остановлена",missing:"Файл не найден"};
    const job=loadingJob();
    const query=$("catalogSearch").value.trim().toLowerCase(), onlyRunning=$("catalogOnlyRunning").checked;
    const rank={busy:0,running:0,loading:1,stopping:1,idle:2,missing:3};
    const shown=catalog.filter(m=>(!query||m.name.toLowerCase().includes(query))&&(!onlyRunning||["running","busy","loading","stopping"].includes(catalogState(m))))
      .sort((a,b)=>rank[catalogState(a)]-rank[catalogState(b)]||a.name.localeCompare(b.name));
    const groups=new Map(); for(const m of shown){const g=m.group||"Другое";if(!groups.has(g))groups.set(g,[]);groups.get(g).push(m);}
    let running=catalog.filter(m=>["running","busy"].includes(catalogState(m))).length;
    $("modelList").innerHTML=[...groups.entries()].map(([group,models])=>`<div class="catalog-group"><p class="group-title">${esc(group)}</p><div class="catalog-cards">${models.map(m=>{
      const st=catalogState(m);
      const on=st==="running"||st==="busy";
      const busyAction=st==="loading"||st==="stopping";
      const blocked=!on&&!busyAction&&job&&job.model_key!==m.key;
      const button=st==="missing"?"":`<button class="button catalog-action ${on?"stop":"start"}" data-action="${on?"stop":"start"}" data-key="${esc(m.key)}" ${busyAction||blocked?"disabled":""} title="${blocked?"Дождитесь окончания текущей загрузки":on?"Выгрузить из видеопамяти":"Загрузить в видеопамять"}">${busyAction?"…":on?"■ Стоп":"▶ Старт"}</button>`;
      const meta=m.exists?`${esc(m.quant||"asset")} · ${(m.size_bytes/1024**3).toFixed(2)} GiB${m.context?` · ${Math.round(m.context/1024)}K`:""}`:"Файл не найден";
      return `<article class="model-card catalog-card st-${st}${selected?.key===m.key?" selected":""}" data-key="${esc(m.key)}" tabindex="0">
        <div class="catalog-card-main"><span class="ai-dot"></span><div><strong>${esc(m.name)}</strong><small class="${m.exists?"":"missing"}">${meta}</small></div></div>
        <div class="catalog-card-side"><span class="catalog-state">${labels[st]}</span>${button}</div>
      </article>`;
    }).join("")}</div></div>`).join("");
    if(!shown.length)$("modelList").innerHTML='<p class="muted">Ничего не найдено.</p>';
    $("catalogCount").textContent=running?`${running} ${plural(running,"запущена","запущены","запущено")} из ${catalog.length}`:`${catalog.length} ${plural(catalog.length,"модель","модели","моделей")} · все остановлены`;
    $("catalogCount").classList.toggle("on",running>0);
    syncChatModels();renderChatState();
  }
  async function catalogAction(action,key) {
    const model=catalog.find(m=>m.key===key); if(!model)return;
    if(action==="start"){
      try{const j=await api("/api/start",{method:"POST",body:JSON.stringify({model_key:key})});pollJob(j.job_id,`Загрузка ${model.name}`,key);selectModel(key);renderCatalog();}
      catch(e){alert(e.message);}
      return;
    }
    stoppingKeys.add(key);renderCatalog();
    try{await api("/api/unload",{method:"POST",body:JSON.stringify({model_key:key})});}
    catch(e){alert(e.message);}
    finally{stoppingKeys.delete(key);await refresh();}
  }
  function formatCount(value) { return Number(value||0).toLocaleString("ru-RU"); }
  function plural(n,one,few,many){const a=Math.abs(n)%100,b=a%10;return a>10&&a<20?many:b===1?one:b>1&&b<5?few:many;}
  function since(iso){
    const t=Date.parse(iso||"");if(!t||t<0)return "";
    const s=Math.max(0,(Date.now()-t)/1000);
    return s<90?`${Math.round(s)} с`:s<5400?`${Math.round(s/60)} мин`:s<172800?`${Math.round(s/3600)} ч`:`${Math.round(s/86400)} дн`;
  }
  function hostAiTone(e){
    const a=e.activity||{};
    if(e.state==="restarting"||e.health==="unhealthy")return "bad";
    if(e.state!=="running")return "off";
    if(a.busy)return "busy";
    return a.ready===false?"wait":"ok";
  }
  function renderHostAi() {
    const all=status.host_ai||[];
    const running=all.filter(e=>e.state==="running"), stopped=all.filter(e=>e.state!=="running");
    const busy=running.filter(e=>e.activity?.busy).length, bad=all.filter(e=>hostAiTone(e)==="bad").length;
    const badge=$("hostAiCount");
    badge.textContent=running.length?`${running.length} ${plural(running.length,"работает","работают","работают")}${busy?` · ${busy} генерирует`:""}${bad?` · ${bad} с ошибкой`:""}`:"Ничего не запущено";
    badge.classList.toggle("danger",bad>0);
    $("hostAiList").innerHTML=running.length?running.map(e=>{
      const a=e.activity||{};
      const ports=(e.ports||[]).map(p=>`<a href="http://${p.host==="127.0.0.1"?"localhost":esc(p.host)}:${p.port}/" target="_blank" rel="noreferrer" title="${esc(p.target)}">:${p.port}${p.public?" · LAN":""}</a>`).join("");
      const chips=(e.details||[]).map(d=>`<span class="setting-chip"><small>${esc(d.label)}</small><strong>${esc(d.value)}</strong></span>`).join("");
      const live=[];
      if(a.busy&&a.generated_tokens!=null)live.push(`${formatCount(a.generated_tokens)} ток. в ответе`);
      if(a.speed_tps!=null)live.push(`${Number(a.speed_tps).toLocaleString("ru-RU",{maximumFractionDigits:1})} ток/с`);
      const foot=[`работает ${since(e.started_utc)}`,e.health&&e.health!=="healthy"?`health: ${e.health}`:"",e.project&&e.project!=="local-ai-server"?e.project:""].filter(Boolean);
      return `<article class="ai-card ${hostAiTone(e)}">
        <div class="ai-card-head"><span class="ai-dot"></span><div class="ai-card-title"><strong>${esc(e.container)}</strong><small>${esc(e.role_label)}${e.gpu?' · <b class="gpu-tag">GPU</b>':""}</small></div><span class="ai-state">${esc(a.state||"")}</span></div>
        ${e.model?`<p class="ai-model" title="${esc(e.image)}">${esc(e.model)}</p>`:`<p class="ai-model dim" title="${esc(e.image)}">${esc(e.image)}</p>`}
        ${live.length?`<p class="ai-live">${esc(live.join(" · "))}</p>`:""}
        ${chips?`<div class="settings-list">${chips}</div>`:""}
        ${e.last_log?`<pre class="ai-log" title="Последняя строка журнала">${esc(e.last_log)}</pre>`:""}
        <div class="ai-card-foot"><span>${esc(foot.join(" · "))}</span><span class="ai-ports">${ports}</span></div>
      </article>`;
    }).join(""):'<div class="active-empty">На хосте нет запущенных ИИ-контейнеров.</div>';
    $("hostAiStoppedBox").hidden=!stopped.length;
    $("hostAiStoppedTitle").textContent=`Остановленные ИИ-контейнеры · ${stopped.length}`;
    $("hostAiStopped").innerHTML=stopped.map(e=>{
      const when=e.state==="restarting"?"перезапускается":e.finished_utc?`${since(e.finished_utc)} назад`:"";
      const code=e.exit_code!=null&&e.state!=="restarting"?`код ${e.exit_code}`:"";
      return `<div class="stopped-row ${hostAiTone(e)}"><span class="ai-dot"></span><strong title="${esc(e.container)} · ${esc(e.image)}">${esc(e.container)}</strong><span>${esc(e.role_label)}</span><span class="dim">${esc([code,when].filter(Boolean).join(" · "))}</span></div>`;
    }).join("");
  }
  function renderUnloadTimer() {
    const state=unloadTimer?.status||"idle";
    const remaining=state==="counting"?Math.max(0,Math.ceil((unloadTimer.deadline*1000-Date.now())/1000)):0;
    $("unloadCountdown").textContent=state==="counting"?`${formatCount(remaining)} с`:state==="unloading"?"Выгрузка…":state==="waiting"?"Ожидание":"—";
    $("unloadTimerState").textContent=state==="counting"?`Осталось ${formatCount(remaining)} с. По завершении будут выгружены все модели.`:state==="unloading"?"Отправлена команда выгрузки всех моделей…":state==="waiting"?"Все модели выгружены. Шлюз работает в режиме ожидания.":state==="error"?`Ошибка выгрузки: ${unloadTimer.error||"неизвестная ошибка"}`:"После отсчёта все модели будут выгружены; шлюз останется в режиме ожидания.";
    $("unloadTimerCancel").hidden=state!=="counting";
    $("unloadTimerStart").disabled=state==="unloading";
  }
  async function refreshUnloadTimer() {
    try{unloadTimer=await api("/api/timer");renderUnloadTimer();if(status)renderTaskStatus();}
    catch(e){$("unloadTimerState").textContent="Таймер недоступен: "+e.message;}
  }
  // ---- live speed (tokens/s) of the request being processed, measured between polls from the server's own counters
  const liveSpeed = new Map();
  const ema = (old, value) => old == null ? value : old * 0.55 + value * 0.45;
  function updateLiveSpeed(models) {
    const now = Date.now();
    for (const m of models) {
      const key = `${m.key}|${m.container||""}`, a = m.activity || {};
      let st = liveSpeed.get(key);
      if (!a.busy) { if (st) { st.idle = true; st.stalled = false; } continue; }
      const processed = a.prompt_processed ?? 0, decoded = a.generated_tokens ?? 0;
      if (!st || st.idle || processed < st.processed || decoded < st.decoded) {
        liveSpeed.set(key, {idle: false, startedAt: now, changeT: now, processed, decoded, read: null, gen: null, phase: "read", hist: [], stalledS: 0});
        continue;
      }
      if (decoded > st.decoded) {
        const dt = (now - st.changeT) / 1000;
        if (dt > 0.2) { st.gen = ema(st.gen, (decoded - st.decoded) / dt); st.phase = "gen"; st.hist.push({v: st.gen, p: "gen"}); }
        st.changeT = now; st.decoded = decoded; st.processed = Math.max(processed, st.processed);
      } else if (processed > st.processed) {
        const dt = (now - st.changeT) / 1000;
        if (dt > 0.2) { st.read = ema(st.read, (processed - st.processed) / dt); st.phase = "read"; st.hist.push({v: st.read, p: "read"}); }
        st.changeT = now; st.processed = processed;
      }
      st.stalledS = Math.round((now - st.changeT) / 1000);
      if (st.hist.length > 40) st.hist.splice(0, st.hist.length - 40);
    }
  }
  function sparkline(hist) {
    if (hist.length < 2) return "";
    const W = 150, H = 34, max = Math.max(...hist.map(h => h.v), 1);
    const pts = hist.map((h, i) => `${(i / (hist.length - 1) * W).toFixed(1)},${(H - 3 - (h.v / max) * (H - 6)).toFixed(1)}`).join(" ");
    return `<svg class="spark" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" aria-hidden="true"><polyline points="${pts}"/></svg>`;
  }
  function speedBlock(model) {
    const a = model.activity || {}, st = liveSpeed.get(`${model.key}|${model.container||""}`), ts = a.token_stats || {};
    const tps = v => `${Number(v).toLocaleString("ru-RU", {maximumFractionDigits: v >= 100 ? 0 : 1})} ток/с`;
    if (a.busy && st && !st.idle) {
      const gen = st.phase === "gen", value = gen ? st.gen : st.read;
      const waiting = st.stalledS >= 3 && value != null;
      return `<div class="speed-live ${gen ? "gen" : "read"}"><div class="sl-main"><span class="sl-label">${gen ? "Пишет ответ" : "Читает запрос"} · скорость сейчас</span>
        <strong class="sl-value">${value != null ? tps(value) : "измеряю…"}</strong>${waiting ? `<small>новая порция данных не пришла ${st.stalledS} с — показана последняя скорость</small>` : ""}</div>${sparkline(st.hist)}</div>`;
    }
    const parts = [];
    if (ts.prompt_speed_tps != null) parts.push(`<span><small>чтение запроса</small><b>${tps(ts.prompt_speed_tps)}</b></span>`);
    if (ts.speed_tps != null) parts.push(`<span><small>генерация ответа</small><b>${tps(ts.speed_tps)}</b></span>`);
    return parts.length ? `<div class="speed-live idle"><span class="sl-label">Скорость последнего запроса</span><div class="sl-pair">${parts.join("")}</div></div>` : "";
  }
  function renderCurrentModels() {
    const models=status.active_models||[];
    updateLiveSpeed(models);
    $("runningModelCount").textContent=models.length?`${models.length} ${plural(models.length,"модель","модели","моделей")}`:"Нет моделей";
    if(!models.length) {
      $("currentModelList").innerHTML='<div class="active-empty">Модели не загружены. Нажмите «Старт» у нужной модели выше.</div>';
      return;
    }
    $("currentModelList").innerHTML=models.map(model=>{
      const activity=model.activity||{};
      const stateClass=activity.busy?"busy":model.api_ready?"ready":"loading";
      const stateLabel=activity.state|| (activity.busy?"Генерирует ответ":model.api_ready?"Загружена · ожидает запрос":"Сервис запускается");
      const launch=(model.parameters||[]).map(p=>`<span class="setting-chip"><small>${esc(p.label)}</small><strong>${esc(p.value)}</strong></span>`).join("");
      const request=(activity.request_parameters||[]).map(p=>`<span class="setting-chip request-chip"><small>${esc(p.label)}</small><strong>${esc(p.value)}</strong></span>`).join("");
      const context=activity.context;
      const contextMarkup=context?`<div class="context-block"><div class="context-label"><strong>Контекстное окно</strong><span>${formatCount(context.percent)}% занято</span></div><div class="context-bar" role="progressbar" aria-label="Заполненность контекстного окна" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(context.percent)}"><i></i></div><div class="context-values"><span>Занято <strong>${formatCount(context.used_tokens)}</strong> / ${formatCount(context.total_tokens)}</span><span>Свободно <strong>${formatCount(context.free_tokens)}</strong></span></div></div>`:"";
      const tokenStats=activity.token_stats||{};
      const tokenPieces=[];
      if(tokenStats.prompt_tokens_total!=null)tokenPieces.push(`<span class="setting-chip"><small>Вход с загрузки</small><strong>${formatCount(tokenStats.prompt_tokens_total)} токенов</strong></span>`);
      if(tokenStats.generated_tokens_total!=null)tokenPieces.push(`<span class="setting-chip"><small>Выход с загрузки</small><strong>${formatCount(tokenStats.generated_tokens_total)} токенов</strong></span>`);
      if(tokenStats.prompt_speed_tps!=null)tokenPieces.push(`<span class="setting-chip"><small>Средняя скорость чтения</small><strong>${Number(tokenStats.prompt_speed_tps).toLocaleString("ru-RU",{maximumFractionDigits:0})} ток/с</strong></span>`);
      if(tokenStats.speed_tps!=null)tokenPieces.push(`<span class="setting-chip"><small>Средняя скорость</small><strong>${Number(tokenStats.speed_tps).toLocaleString("ru-RU",{maximumFractionDigits:1})} ток/с</strong></span>`);
      const tokenMarkup=tokenPieces.length?`<div class="settings-block"><span class="settings-title">Токены и скорость</span><div class="settings-list">${tokenPieces.join("")}</div></div>`:"";
      const tuning=model.tuning||{};
      const tuned=[];
      if(tuning.recommended_context_tokens!=null)tuned.push(["Подобранное окно",`${formatCount(tuning.recommended_context_tokens)} токенов`]);
      if(tuning.recommended_max_input_tokens!=null)tuned.push(["Проверенный ввод",`${formatCount(tuning.recommended_max_input_tokens)} токенов`]);
      if(tuning.largest_tested_context_tokens!=null)tuned.push(["Макс. проверенное окно",`${formatCount(tuning.largest_tested_context_tokens)} токенов`]);
      if(tuning.peak_vram_mib!=null)tuned.push(["Пик VRAM в тесте",`${formatCount(tuning.peak_vram_mib)} МиБ`]);
      if(tuning.runtime)tuned.push(["Подобранный режим",tuning.runtime]);
      const tunedMarkup=tuned.length?`<div class="settings-block"><span class="settings-title">Подобранные параметры</span><div class="settings-list">${tuned.map(([label,value])=>`<span class="setting-chip"><small>${esc(label)}</small><strong>${esc(value)}</strong></span>`).join("")}</div>${tuning.notes?`<p class="idle-note">${esc(tuning.notes)}</p>`:""}</div>`:"";
      let progress="";
      if(activity.busy) {
        const total=activity.prompt_tokens, done=activity.prompt_processed, gen=activity.generated_tokens||0, max=activity.max_tokens;
        const reading=gen===0&&total&&done!=null&&done<total;
        if(reading) {
          const pct=Math.round(100*done/total);
          progress=`<p class="request-progress"><b>Читает запрос:</b> ${formatCount(done)} из ${formatCount(total)} токенов (${pct}%)</p><div class="context-bar read-bar"><i style="width:${pct}%"></i></div><p class="idle-note">Ответ ещё не начат: сначала модель читает весь запрос. Счётчик обновляется порциями (до 2048 токенов), на медленных режимах он стоит на месте десятки секунд.</p>`;
        } else progress=`<p class="request-progress"><b>Пишет ответ:</b> ${formatCount(gen)}${max&&max>0?` из ${formatCount(max)} максимум`:""} токенов${total?` · запрос ${formatCount(total)} токенов`:""}</p>`;
      }
      const port=model.port?` · 127.0.0.1:${model.port}`:"";
      return `<article class="active-model ${stateClass}">
        <div class="active-model-head"><div><h3>${esc(model.name)}${model.external?' <span class="external-tag">вне шлюза</span>':""}</h3><p>${esc(model.api_model_id||model.service||"")}${esc(port)}</p></div><span class="live-state">${esc(stateLabel)}</span></div>
        ${speedBlock(model)}
        ${contextMarkup}
        ${tokenMarkup}
        <div class="settings-block"><span class="settings-title">Параметры запуска</span><div class="settings-list">${launch||'<span class="muted">Нет данных конфигурации</span>'}</div></div>
        ${tunedMarkup}
        ${activity.busy?model.kind==="image"?'<p class="idle-note">Генерация изображения выполняется в контейнере.</p>':`<div class="settings-block request-block"><span class="settings-title">Текущий запрос</span>${progress}<div class="settings-list">${request||'<span class="muted">Параметры запроса не переданы сервером</span>'}</div></div>`:'<p class="idle-note">Сейчас генерация не выполняется.</p>'}
      </article>`;
    }).join("");
    $("currentModelList").querySelectorAll(".active-model").forEach((card,index)=>{
      const context=models[index]?.activity?.context;
      const fill=card.querySelector(".context-bar i");
      if(fill&&context)fill.style.width=`${Math.max(0,Math.min(100,context.percent))}%`;
    });
  }
  function renderGpuChart(gpu) {
    if(gpu?.available&&gpu.utilization_percent!=null) {
      const stamp=gpu.sampled_utc||new Date().toISOString();
      const last=gpuHistory[gpuHistory.length-1];
      if(last?.time===stamp)last.value=Number(gpu.utilization_percent);
      else gpuHistory.push({time:stamp,value:Number(gpu.utilization_percent)});
      while(gpuHistory.length>gpuHistoryLimit)gpuHistory.shift();
      $("gpuPercent").textContent=`${Number(gpu.utilization_percent)}%`;
      $("gpuChartNote").textContent=`${gpu.name||"GPU"} · опрос каждые 5 секунд · последние 5 минут`;
    } else {
      $("gpuPercent").textContent="—%";
      $("gpuChartNote").textContent=gpu?.error||"Нет данных от nvidia-smi.";
    }
    const svg=$("gpuChart"), width=700,height=210,left=46,right=14,top=12,bottom=32,plotW=width-left-right,plotH=height-top-bottom;
    const now=Date.parse(gpuHistory[gpuHistory.length-1]?.time||new Date().toISOString()), windowMs=5*60*1000;
    const xAt=time=>left+Math.max(0,Math.min(1,(time-(now-windowMs))/windowMs))*plotW;
    const yAt=value=>top+(100-Math.max(0,Math.min(100,value)))/100*plotH;
    const grid=[100,75,50,25,0].map(value=>{
      const y=yAt(value);
      return `<line class="chart-grid" x1="${left}" y1="${y}" x2="${width-right}" y2="${y}"/><text class="chart-y-label" x="${left-10}" y="${y+4}" text-anchor="end">${value}%</text>`;
    }).join("");
    const xLabels=`<text class="chart-x-label" x="${left}" y="${height-6}" text-anchor="start">−5 мин</text><text class="chart-x-label" x="${left+plotW/2}" y="${height-6}" text-anchor="middle">−2,5 мин</text><text class="chart-x-label" x="${width-right}" y="${height-6}" text-anchor="end">сейчас</text>`;
    const points=gpuHistory.map(point=>`${xAt(Date.parse(point.time)).toFixed(1)},${yAt(point.value).toFixed(1)}`);
    let line="",area="",dot="";
    if(points.length) {
      line=`<polyline class="chart-line" points="${points.join(" ")}"/>`;
      const firstX=points[0].split(",")[0],lastX=points[points.length-1].split(",")[0],baseY=yAt(0);
      area=`<polygon class="chart-area" points="${firstX},${baseY} ${points.join(" ")} ${lastX},${baseY}"/>`;
      const last=gpuHistory[gpuHistory.length-1];dot=`<circle class="chart-dot" cx="${xAt(Date.parse(last.time))}" cy="${yAt(last.value)}" r="4"><title>${last.value}%</title></circle>`;
    }
    svg.innerHTML=`<defs><linearGradient id="gpuFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#4bd6b4" stop-opacity=".27"/><stop offset="100%" stop-color="#4bd6b4" stop-opacity="0"/></linearGradient></defs>${grid}${xLabels}${area}${line}${dot}`;
    svg.setAttribute("aria-label",gpu?.available?`Загрузка GPU: ${gpu.utilization_percent} процентов; показана история за 5 минут.`:"График загрузки GPU недоступен.");
  }
  function renderIssues() {
    const all=status.issues||[];
    const issues=all.filter(x=>x.severity!=="info");
    const notes=all.filter(x=>x.severity==="info");
    const count=$("issueCount");
    count.textContent=issues.length?`${issues.length} ${issues.length===1?"проблема":"замечаний"}`:"Ошибок нет";
    count.classList.toggle("danger",issues.some(x=>x.severity==="error"));
    const noteHtml=notes.map(issue=>`<article class="issue-item"><span class="issue-mark">i</span><div><strong>${esc(issue.title)}</strong><p>${esc(issue.detail)}</p><small>${esc(issue.source||"")}</small></div></article>`).join("");
    if(!issues.length) {
      $("issueList").innerHTML='<div class="no-issues"><span class="issue-check">✓</span><span>Активных ошибок и предупреждений не обнаружено.</span></div>'+noteHtml;
      return;
    }
    $("issueList").innerHTML=issues.map(issue=>`<article class="issue-item ${issue.severity==="error"?"issue-error":"issue-warning"}"><span class="issue-mark">${issue.severity==="error"?"!":"△"}</span><div><strong>${esc(issue.title)}</strong><p>${esc(issue.detail)}</p><small>${esc(issue.source||"")}</small></div></article>`).join("")+noteHtml;
  }
  function averageTokenSpeed(model) {
    const activity=model.activity||{};
    if(!activity.busy||activity.generated_tokens==null)return "";
    const key=model.key;
    const now=Date.parse(status.utc)||Date.now();
    const samples=tokenSpeedHistory.get(key)||[];
    if(samples.length&&Number(activity.generated_tokens)<samples[samples.length-1].tokens)samples.length=0;
    if(!samples.length||samples[samples.length-1].time!==now) {
      samples.push({time:now,tokens:Number(activity.generated_tokens)});
      while(samples.length>2&&now-samples[0].time>30000)samples.shift();
      tokenSpeedHistory.set(key,samples);
    }
    const first=samples[0],last=samples[samples.length-1];
    const seconds=(last.time-first.time)/1000;
    if(seconds<4)return "средняя скорость: измеряется";
    const rate=Math.max(0,(last.tokens-first.tokens)/seconds);
    const formatted=rate.toLocaleString("ru-RU",{maximumFractionDigits:1});
    return `средняя скорость ${formatted} ток/с · ${Math.round(seconds)} с`;
  }
  function renderTaskStatus() {
    const job=[status.job,currentJob].find(item=>item&&["queued","running"].includes(item.status));
    const modelByKey=key=>catalog.find(item=>item.key===key);
    if(job) {
      const model=modelByKey(job.model_key);
      const names={start:"Запускает модель",stop:"Останавливает модель",smoke:"Выполняет короткий тест",protocol:"Выполняет протокол тестов",image:"Генерирует изображение"};
      $("jobState").textContent=job.status==="queued"?"Задача в очереди":(names[job.kind]||"Выполняет задачу");
      const progress=(job.log||"").trim().split(/\r?\n/).filter(Boolean).at(-1);
      const busyModel=(status.active_models||[]).find(item=>item.activity?.busy&&(!job.model_key||item.key===job.model_key));
      $("jobDetail").textContent=[model?.name||job.model_key,progress,busyModel&&averageTokenSpeed(busyModel)].filter(Boolean).join(" · ");
      return;
    }
    const activeModels=status.active_models||[];
    const busy=activeModels.find(model=>model.activity?.busy);
    if(busy) {
      const activity=busy.activity;
      $("jobState").textContent=activity.state||"Генерирует ответ";
      const details=[busy.name];
      if(activity.prompt_processed!=null)details.push(`вход ${formatCount(activity.prompt_processed)} токенов`);
      if(activity.generated_tokens!=null)details.push(`ответ ${formatCount(activity.generated_tokens)} токенов`);
      details.push(averageTokenSpeed(busy));
      $("jobDetail").textContent=details.join(" · ");
      return;
    }
    const hostRunning=(status.host_ai||[]).filter(e=>e.state==="running");
    const hostBusy=hostRunning.find(e=>e.activity?.busy);
    if(hostBusy) {
      $("jobState").textContent=hostBusy.activity.state||"Выполняет задачу";
      $("jobDetail").textContent=[hostBusy.container,hostBusy.model].filter(Boolean).join(" · ");
      return;
    }
    const hostJob=hostRunning.find(e=>e.role==="job"||e.role==="train");
    if(hostJob) {
      $("jobState").textContent=`Фоновая задача · ${hostJob.container}`;
      $("jobDetail").textContent=hostJob.last_log||hostJob.model||"";
      return;
    }
    const ready=activeModels.filter(model=>model.api_ready);
    if(ready.length) {
      $("jobState").textContent="Ожидает запрос";
      $("jobDetail").textContent=ready.map(model=>model.name).join(" · ");
      return;
    }
    const starting=activeModels.filter(model=>!model.api_ready);
    if(starting.length) {
      $("jobState").textContent="Запускает сервис";
      $("jobDetail").textContent=starting.map(model=>model.name).join(" · ");
      return;
    }
    if(unloadTimer?.status==="waiting") {
      $("jobState").textContent="Режим ожидания";
      $("jobDetail").textContent="Все модели выгружены из памяти. Шлюз готов к новому запросу.";
      return;
    }
    const services=[...new Set([...hostRunning.map(e=>e.container),...(status.docker_project_services||[]).filter(service=>service.state==="running").map(service=>service.name)])];
    if(services.length) {
      $("jobState").textContent="Модели не генерируют";
      $("jobDetail").textContent=`Работают: ${services.join(" · ")}`;
      return;
    }
    $("jobState").textContent=status.docker_available?"Сервер простаивает":"Docker недоступен";
    $("jobDetail").textContent=status.docker_available?"Нет активной генерации или фоновой задачи.":(status.docker_error||"Нет подключения к Docker.");
  }
  function renderStatus() {
    if(!status)return;
    $("dockerState").textContent=status.docker_available?"Подключён":"Недоступен";
    const gpu=status.gpu||{};
    if(gpu.available){$("gpuState").textContent=`${gpu.name} · ${(gpu.memory_free_mib/1024).toFixed(2)} GiB свободно`;$("gpuDetail").textContent=`Занято ${gpu.memory_used_mib} / ${gpu.memory_total_mib} MiB · ${gpu.utilization_percent}% · ${gpu.power_w} W · ${gpu.temperature_c}°C`;$ ("gpuMeter").style.width=`${Math.min(100,100*gpu.memory_used_mib/gpu.memory_total_mib)}%`;}
    else {$("gpuState").textContent="Недоступна";$("gpuDetail").textContent=gpu.error||"";}
    const currentModels=status.active_models||[];
    const hostAi=status.host_ai||[], hostRunning=hostAi.filter(e=>e.state==="running");
    const hostBusy=hostRunning.filter(e=>e.activity?.busy).length;
    $("activeModels").textContent=hostRunning.length?`${hostRunning.length} ${plural(hostRunning.length,"работает","работают","работают")}${hostBusy?` · ${hostBusy} генерирует`:""}`:"Ничего не запущено";
    const inMemory=currentModels.map(x=>x.name);
    $("modelApiState").textContent=[inMemory.length?`В памяти: ${inMemory.join(" · ")}`:status.gateway_available?"Шлюз: модели выгружены":"Шлюз остановлен",
      hostAi.length>hostRunning.length?`остановлено ${hostAi.length-hostRunning.length}`:""].filter(Boolean).join(" · ");
    renderCatalog();
    const issues=(status.issues||[]).filter(x=>x.severity!=="info");
    $("issueSummary").textContent=issues.length?`${issues.length} ${plural(issues.length,"замечание","замечания","замечаний")} · см. справа`:"Ошибок нет";
    $("issueSummary").classList.toggle("warn",issues.length>0);
    renderHostAi();
    renderCurrentModels();
    renderGpuChart(gpu);
    renderIssues();
    renderTaskStatus();
  }
  async function refresh() {
    try {const [models,s]=await Promise.all([api("/api/models"),api("/api/status")]);catalog=models.models;status=s;renderCatalog();const preferred=selected?.key||(s.active_models||[]).find(m=>!m.external&&catalog.some(c=>c.key===m.key))?.key;if(preferred)selectModel(preferred);renderStatus();}
    catch(e){$("dockerState").textContent="Проверка недоступна";$("gpuState").textContent=e.message;}
  }
  function showJob(title) {$("jobPanel").hidden=false;$("jobTitle").textContent=title;$("jobStatus").textContent="Выполняется";$("jobLog").textContent="Подготовка…";$("jobResult").hidden=true;}
  async function pollJob(id,title,modelKey=selected?.key) {
    currentJob={job_id:id,status:"queued",kind:title,model_key:modelKey};showJob(title);if(modelKey)trackLoad(modelKey,false);
    if(pollTimer)clearInterval(pollTimer);
    pollTimer=setInterval(async()=>{
      try{const j=await api(`/api/jobs/${id}`);currentJob=j;$("jobStatus").textContent=j.status;$("jobLog").textContent=j.log||j.error||"";$("jobLog").scrollTop=$("jobLog").scrollHeight;
        if(j.status==="complete"||j.status==="error") {clearInterval(pollTimer);pollTimer=null;$("jobResult").hidden=false;$("jobResult").textContent=j.error||j.result?.message||JSON.stringify(j.result||{},null,2);$("jobStatus").textContent=j.status==="complete"?"Готово":"Ошибка";$("jobStatus").className="badge"+(j.status==="complete"?" on":" danger");await refresh();if(j.status==="complete")setTimeout(()=>{if(currentJob?.job_id===j.job_id)$("jobPanel").hidden=true;},4000);}
        renderStatus();
      }catch(e){$("jobLog").textContent=e.message;clearInterval(pollTimer);pollTimer=null;}
    },1500);
  }
  // ---- model load / swap status and answer statistics, shown right in the chat panel
  let loadTrack = null;
  const loadedKeys = () => (status.models || []).filter(m => m.api_ready).map(m => m.key);
  function loadEstimateSec(key) {
    const m = catalog.find(x => x.key === key);
    let est = m && m.size_bytes ? m.size_bytes / 350e6 : 20;
    try { const learned = Number(localStorage.getItem("loadSec:" + key)); if (learned > 0) est = learned; } catch (e) { /* storage blocked */ }
    return Math.min(120, Math.max(6, est));
  }
  function stopTrack() {
    if (loadTrack) { clearInterval(loadTrack.timer); loadTrack = null; }
    $("chatLoad").hidden = true;
  }
  function trackLoad(key, withAnswer) {
    if (loadTrack && loadTrack.key === key) { loadTrack.answer = loadTrack.answer || !!withAnswer; return; }
    stopTrack();
    const others = loadedKeys().filter(k => k !== key);
    const st = loadTrack = {key, answer: !!withAnswer, t0: Date.now(), tLoad: null, tUnload: null, oldNames: others.join(", "), est: loadEstimateSec(key), gen: {t: 0, n: 0, speed: null}, doneAt: null};
    const show = (text, pct, sub) => {
      $("chatLoad").hidden = false;
      $("clText").textContent = text; $("clPct").textContent = pct == null ? "" : pct + "%";
      $("clBar").style.width = (pct == null ? 100 : pct) + "%"; $("clSub").textContent = sub || "";
      const log = $("chatLog"); log.scrollTop = log.scrollHeight;
    };
    const tick = async () => {
      try { status = await api("/api/status"); } catch (e) { /* keep the last status */ }
      if (loadTrack !== st) return;
      const now = Date.now(), loaded = loadedKeys();
      if (loaded.includes(key)) {
        if (!st.doneAt) {
          st.doneAt = now;
          if (st.tLoad) { try { const sec = (now - st.tLoad) / 1000, old = Number(localStorage.getItem("loadSec:" + key)) || sec; localStorage.setItem("loadSec:" + key, String(0.5 * old + 0.5 * sec)); } catch (e) { /* storage blocked */ } }
        }
        if (!st.answer) { show("Модель загружена: " + key, 100, st.tLoad ? "заняло " + Math.round((st.doneAt - st.tLoad) / 1000) + " с" : ""); if (now - st.doneAt > 2500) stopTrack(); return; }
        const entry = (status.active_models || []).find(m => m.key === key), act = (entry && entry.activity) || {};
        const gen = act.generated_tokens, pp = act.prompt_processed;
        if (gen != null && gen > 0) {
          if (st.gen.t && gen > st.gen.n) st.gen.speed = (gen - st.gen.n) / ((now - st.gen.t) / 1000);
          st.gen.t = now; st.gen.n = gen;
          show("Пишет ответ: " + gen + " ток", null, (st.gen.speed ? Math.round(st.gen.speed * 10) / 10 + " ток/с · " : "") + (pp != null ? "вход " + pp + " ток" : ""));
        } else show("Читает запрос" + (pp != null ? ": " + pp + " ток" : "") + " · " + key, null, "");
        return;
      }
      if (loaded.some(k => k !== key)) {
        if (!st.tUnload) st.tUnload = now;
        st.oldNames = loaded.filter(k => k !== key).join(", ");
        const pct = Math.min(90, Math.round((now - st.tUnload) / 4000 * 100));
        show("Выгружается: " + st.oldNames + " → затем " + key, pct, "освобождается видеопамять");
        return;
      }
      if (!st.tLoad) st.tLoad = now;
      const elapsed = (now - st.tLoad) / 1000, pct = Math.min(95, Math.round(elapsed / st.est * 100)), left = Math.max(0, Math.round(st.est - elapsed));
      show((st.oldNames ? "Выгружено: " + st.oldNames + " · " : "") + "Загружается: " + key, pct,
        left > 0 ? "осталось ≈ " + left + " с (оценка по размеру файла и прошлым загрузкам)" : "дольше ожидаемого — ждём, модель ещё читается с диска");
    };
    st.timer = setInterval(tick, 1000);
    tick();
  }
  $("chatForm").addEventListener("submit",async ev=>{
    ev.preventDefault();if(!selected)return;const text=$("promptInput").value.trim();if(!text)return;const send=$("sendBtn");send.disabled=true;send.dataset.sending="1";
    addMessage("user",text);$("promptInput").value="";
    const message={role:"user",content:text};const file=$("visionFile").files[0];
    if(file&&selected.kind==="vision") {const dataUrl=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(file);});message.content=[{type:"text",text:text},{type:"image_url",image_url:{url:dataUrl}}];}
    const payload={messages:[...chatMessages,message],max_tokens:1024,temperature:0.7,stream:false};
    payload.chat_template_kwargs={enable_thinking:false};
    const sentAt=Date.now();trackLoad(selected.key,true);
    try{const result=await api("/api/chat",{method:"POST",body:JSON.stringify({model_key:selected.key,payload})});const choice=result.choices?.[0]||{};const msg=choice.message||{};const answer=msg.content||"[Модель не вернула пользовательский текст в поле content.]";
      const tm=result.timings||{},us=result.usage||{},r1=v=>v==null?"?":(Math.round(v*10)/10);
      addMessage("assistant",answer,`${choice.finish_reason||"готово"} · вход ${us.prompt_tokens??tm.prompt_n??"?"} ток · выход ${us.completion_tokens??tm.predicted_n??"?"} ток · чтение ${r1(tm.prompt_per_second)} ток/с · выдача ${r1(tm.predicted_per_second)} ток/с · ${Math.round((Date.now()-sentAt)/100)/10} с`);if(msg.content)chatMessages.push(message,{role:"assistant",content:msg.content});}
    catch(e){addMessage("assistant","Ошибка: "+e.message);}finally{stopTrack();delete send.dataset.sending;send.disabled=false;renderChatState();}
  });
  $("visionFile").addEventListener("change",e=>$("visionFileName").textContent=e.target.files[0]?.name||"");
  $("refreshBtn").addEventListener("click",refresh);
  $("unloadTimerStart").addEventListener("click",async()=>{
    const seconds=Number($("unloadSeconds").value);
    if(!Number.isInteger(seconds)||seconds<1||seconds>604800){$("unloadTimerState").textContent="Укажите целое число секунд от 1 до 604800.";return;}
    try{unloadTimer=await api("/api/timer",{method:"POST",body:JSON.stringify({seconds})});renderUnloadTimer();}
    catch(e){$("unloadTimerState").textContent="Ошибка запуска: "+e.message;}
  });
  $("unloadTimerCancel").addEventListener("click",async()=>{
    try{unloadTimer=await api("/api/timer/cancel",{method:"POST"});renderUnloadTimer();}
    catch(e){$("unloadTimerState").textContent="Ошибка отмены: "+e.message;}
  });
  $("modelList").addEventListener("click",event=>{
    const action=event.target.closest(".catalog-action");
    if(action){event.stopPropagation();if(!action.disabled)catalogAction(action.dataset.action,action.dataset.key);return;}
    const card=event.target.closest(".model-card");
    if(card&&!card.classList.contains("st-missing"))selectModel(card.dataset.key);
  });
  $("catalogSearch").addEventListener("input",renderCatalog);
  $("catalogOnlyRunning").addEventListener("change",renderCatalog);
  $("chatModel").addEventListener("change",e=>selectModel(e.target.value));
  $("modelList").addEventListener("keydown",event=>{
    const card=event.target.closest(".model-card");
    if(card&&event.target===card&&(event.key==="Enter"||event.key===" ")){event.preventDefault();selectModel(card.dataset.key);}
  });
  $("reportLink").href="/report/";$("videoLink").href=`${location.protocol}//${location.hostname}:8767/`;
  // ---- test results: every kind of test on one row, sorted by any metric chosen above the list
  const testsSeen = new Map();
  const nf = (v, d = 0) => Number(v).toLocaleString("ru-RU", {maximumFractionDigits: d});
  const catPct = (e, c) => e.general?.pct?.[c] ?? null;
  const ctxOf = e => e.context?.stable_ctx ?? e.context?.best_ctx ?? null;
  const TEST_METRICS = [
    {id: "total", label: "Итог общего теста", get: e => e.general?.total, fmt: v => v + "%", unit: "общий тест", cls: true},
    {id: "tg", label: "Скорость генерации", get: e => e.general?.tg, fmt: v => nf(v, 1) + " ток/с", unit: "генерация"},
    {id: "pp", label: "Скорость чтения промпта", get: e => e.general?.pp, fmt: v => nf(v) + " ток/с", unit: "чтение промпта"},
    {id: "ru", label: "Русский язык", get: e => catPct(e, "Русский"), fmt: v => v + "%", unit: "русский", cls: true},
    {id: "logic", label: "Логика", get: e => catPct(e, "Логика"), fmt: v => v + "%", unit: "логика", cls: true},
    {id: "code", label: "Код", get: e => catPct(e, "Код"), fmt: v => v + "%", unit: "код", cls: true},
    {id: "instr", label: "Следование инструкциям", get: e => catPct(e, "Инструкции"), fmt: v => v + "%", unit: "инструкции", cls: true},
    {id: "vision", label: "Зрение", get: e => catPct(e, "Зрение"), fmt: v => v + "%", unit: "зрение", cls: true},
    {id: "german", label: "Немецкий язык", get: e => e.german?.pct, fmt: v => v + "%", unit: "немецкий", cls: true},
    {id: "stem", label: "Математика и физика (всего)", get: e => e.stem?.pct, fmt: v => v + "%", unit: "матем. и физика", cls: true},
    {id: "math", label: "Математика", get: e => e.stem && e.stem.n ? Math.round(100 * e.stem.math / (e.stem.n / 2)) : null, fmt: v => v + "%", unit: "математика", cls: true},
    {id: "phys", label: "Физика", get: e => e.stem && e.stem.n ? Math.round(100 * e.stem.phys / (e.stem.n / 2)) : null, fmt: v => v + "%", unit: "физика", cls: true},
    {id: "code20", label: "Код (20 задач)", get: e => e.code20?.passed, fmt: v => v + " из 20", unit: "код 20", cls: false},
    {id: "chem", label: "Химия", get: e => e.chem?.pct, fmt: v => v + "%", unit: "химия", cls: true},
    {id: "ctx", label: "Длинный контекст", get: e => ctxOf(e), fmt: v => Math.round(v / 1024) + "K", unit: "контекст"},
    {id: "vram", label: "Меньше видеопамяти", get: e => e.general?.vram_mib, fmt: v => fmtGb(v), unit: "VRAM", low: true},
    {id: "size", label: "Меньше размер на диске", get: e => e.general?.size_gb, fmt: v => nf(v, 1) + " ГБ", unit: "размер", low: true},
    {id: "library", label: "Номер в библиотеке", get: e => e.library_no ? Number(e.library_no) : null, fmt: v => "№ " + String(v).padStart(3, "0"), unit: "номер", low: true},
    {id: "updated", label: "Недавно обновлённые", get: e => Date.parse(e.updated_utc) || null, fmt: v => testTime(new Date(v).toISOString()), unit: "обновление"},
  ];
  let testsMetric = "total", testsFlip = false, testsOnlyWith = false;
  try {
    testsMetric = localStorage.getItem("testsMetric") || "total"; testsFlip = localStorage.getItem("testsFlip") === "1"; testsOnlyWith = localStorage.getItem("testsOnlyWith") === "1";
  } catch (e) { /* storage blocked */ }
  if (!TEST_METRICS.some(m => m.id === testsMetric)) testsMetric = "total";
  const saveTestsPrefs = () => { try { localStorage.setItem("testsMetric", testsMetric); localStorage.setItem("testsFlip", testsFlip ? "1" : "0"); localStorage.setItem("testsOnlyWith", testsOnlyWith ? "1" : "0"); } catch (e) { /* ignore */ } };
  const fmtGb = v => v == null ? "—" : (v / 1024).toFixed(1).replace(".", ",") + " ГБ";
  const scoreClass = p => p == null ? "" : p >= 85 ? "good" : p >= 70 ? "mid" : "low";
  function testTime(iso) { return iso ? new Date(iso).toLocaleString("ru-RU", {day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"}) : ""; }
  const archivedTag = on => on ? ' <span class="arch-tag" title="Результат сохранён в базе, исходный файл теста уже не содержит эту строку">из архива</span>' : "";

  function testBlocks(e) {
    const blocks = [];
    const g = e.general;
    if (g) {
      if (g.failed) blocks.push(`<div class="test-block"><span class="tb-title">Общий тест${archivedTag(g.archived)}</span><span class="bad">не загрузилась: ${esc(g.error || "")}</span></div>`);
      else {
        const cats = ["Русский", "Логика", "Код", "Инструкции", "Зрение"].filter(c => g.raw && g.raw[c]).map(c => `<span class="setting-chip"><small>${esc(c)}</small><strong>${g.raw[c][0]}/${g.raw[c][1]}</strong></span>`).join("");
        const speed = [g.tg != null ? `генерация ${nf(g.tg, 1)} ток/с` : null, g.pp != null ? `чтение ${nf(g.pp)} ток/с` : null, g.vram_mib ? `VRAM ${fmtGb(g.vram_mib)}` : null].filter(Boolean).join(" · ");
        blocks.push(`<div class="test-block"><span class="tb-title">Общий тест${g.total != null ? ` · итог ${g.total}%` : ""}${archivedTag(g.archived)}</span><small>${esc(speed)}</small><div class="settings-list">${cats}</div></div>`);
      }
    }
    if (e.german) {
      const d = e.german, weak = (d.weak || []).map(w => `${w[0]} ${w[1]}/${w[2]}`).join(", ");
      blocks.push(`<div class="test-block"><span class="tb-title">Немецкий язык · ${d.score}/${d.n} верных (${d.pct}%)${archivedTag(d.archived)}</span>${weak ? `<small title="Темы с ошибками">слабые темы: ${esc(weak)}</small>` : ""}</div>`);
    }
    if (e.context) {
      const c = e.context, best = c.stable_ctx ?? c.best_ctx;
      blocks.push(`<div class="test-block"><span class="tb-title">Длинный контекст · стабильно до ${best ? Math.round(best / 1024) + "K" : "—"}${c.native_ctx ? ` из ${Math.round(c.native_ctx / 1024)}K родных` : ""}${archivedTag(c.archived)}</span>${c.recommended_cfg ? `<small>рекомендуемый режим: ${esc(c.recommended_cfg)}</small>` : ""}</div>`);
    }
    if (e.stem) {
      const t = e.stem, th = t.think_run;
      blocks.push(`<div class="test-block"><span class="tb-title">Математика и физика · ${t.pct != null ? t.pct + "%" : "—"}${archivedTag(t.archived)}</span><small>математика ${t.math}/${(t.n || 40) / 2} · физика ${t.phys}/${(t.n || 40) / 2}${t.truncated ? ` · обрезано ${t.truncated}` : ""}${t.minutes ? ` · ${t.minutes} мин` : ""}${t.think === true ? " · с размышлением" : ""}${th ? ` · с размышлением ${th.pct}%` : ""}</small></div>`);
    }
    if (e.code20) {
      const c = e.code20, levels = Object.entries(c.by_level || {}).map(([k, v]) => `ур. ${k}: ${v[0]}/${v[1]}`).join(" · ");
      const failed = (c.failed || []).length ? `не прошли: ${c.failed.map(esc).join(", ")}` : "все задачи пройдены";
      blocks.push(`<div class="test-block"><span class="tb-title">Код (20 задач) · ${c.passed} из ${c.n}${archivedTag(c.archived)}</span><small>${levels}${c.minutes ? ` · ${c.minutes} мин` : ""}${c.request_errors ? ` · ошибок запросов ${c.request_errors}` : ""}</small><small>${failed}</small></div>`);
    }
    if (e.chem) {
      const c = e.chem, th = c.think_run;
      blocks.push(`<div class="test-block"><span class="tb-title">Химия · ${c.score != null ? c.score + " из 10" : "—"}${archivedTag(c.archived)}</span><small>${c.truncated ? `обрезано ${c.truncated} · ` : ""}${c.minutes ? `${c.minutes} мин` : ""}${c.think === true ? " · с размышлением" : ""}${th ? ` · с размышлением ${th.score} из 10` : ""}</small></div>`);
    }
    return blocks.join("");
  }

  function testRow(e, metric, place, isNew, hasValue) {
    const no = e.library_no ? `№ ${e.library_no}` : "№ —";
    const g = e.general || {};
    const facts = [g.quant, g.size_gb ? `${String(g.size_gb).replace(".", ",")} ГБ на диске` : null, g.placement === "fit" ? "частично на CPU" : null].filter(Boolean).join(" · ");
    const v = metric.get(e);
    const cls = metric.cls ? scoreClass(v) : "";
    const podium = hasValue && place <= 3 ? ` podium p${place}` : "";
    return `<article class="test-row${isNew ? " fresh" : ""}${podium}"><span class="test-no">${no}</span>
      <div class="test-main"><strong>${esc(e.model)}</strong>${facts ? `<small>${esc(facts)}</small>` : ""}${testBlocks(e)}</div>
      <div class="test-side"><span class="test-score ${cls}">${v != null ? esc(metric.fmt(v)) : "—"}</span><small>${hasValue ? `место ${place} по «${esc(metric.unit)}»` : `нет теста «${esc(metric.unit)}»`}</small><small>обновлено ${esc(testTime(e.updated_utc))}</small></div></article>`;
  }

  function sortedTests(entries) {
    const metric = TEST_METRICS.find(m => m.id === testsMetric) || TEST_METRICS[0];
    const bestHigh = !metric.low;
    const dirHigh = testsFlip ? !bestHigh : bestHigh;
    const withVal = entries.filter(e => metric.get(e) != null).sort((a, b) => dirHigh ? metric.get(b) - metric.get(a) || (b.general?.tg ?? 0) - (a.general?.tg ?? 0) : metric.get(a) - metric.get(b) || (b.general?.tg ?? 0) - (a.general?.tg ?? 0));
    const without = testsOnlyWith ? [] : entries.filter(e => metric.get(e) == null).sort((a, b) => Date.parse(b.updated_utc) - Date.parse(a.updated_utc));
    return {metric, withVal, without};
  }

  function renderTestControls() {
    const sel = $("testsMetric");
    if (!sel.options.length) sel.innerHTML = TEST_METRICS.map(m => `<option value="${m.id}">${esc(m.label)}</option>`).join("");
    sel.value = testsMetric;
    const metric = TEST_METRICS.find(m => m.id === testsMetric);
    const dirHigh = testsFlip ? !!metric.low : !metric.low;
    $("testsDir").textContent = dirHigh ? "↓ лучшие сверху" : "↑ худшие сверху";
    $("testsDir").title = "Поменять порядок сортировки";
    $("testsOnlyWith").checked = testsOnlyWith;
  }

  // ---- benchmark pipeline: what is measured, what is done, what runs now, what comes next
  const fmtEta = m => m == null ? "" : m < 90 ? `≈ ${m} мин` : `≈ ${Math.floor(m / 60)} ч ${String(m % 60).padStart(2, "0")} мин`;
  const STAGE_ICON = {done: "✅", running: "▶", paused: "⏸", waiting: "⏳"};
  const stageBar = (o) => {
    if (!o || o.finished) return "";
    return `<div class="plan-total"><b>До конца всех тестов</b><div class="plan-bar plan-bar-cur"><i style="width:${o.percent}%"></i></div><b>${o.percent}%</b><small>прошло ${fmtEta(o.elapsed_minutes).replace("≈ ", "")} · осталось ${fmtEta(o.remaining_minutes)}</small></div>`;
  };
  function renderPlan(plan) {
    const box = $("testsPlan");
    if (!plan || !plan.stages || !plan.stages.length) { box.innerHTML = ""; return; }
    const titles = new Map(plan.stages.map(s => [s.id, s.title]));
    const running = plan.stages.find(s => s.state === "running");
    const nextStage = plan.stages.find(s => s.id === plan.next);
    const doneTitles = plan.stages.filter(s => s.state === "done").map(s => s.title);
    const summary = running
      ? `Сейчас: «${running.title}»${running.current ? ` — ${running.current}` : ""}${running.total ? ` (${running.done + (running.current ? 1 : 0)} из ${running.total})` : ""}${plan.overall && !plan.overall.finished ? ` · до конца всех тестов ${fmtEta(plan.overall.remaining_minutes)} (${plan.overall.percent}%)` : ""}`
      : nextStage ? `Сейчас ничего не запущено. Дальше: «${nextStage.title}»` : "Все этапы пройдены";
    const items = plan.stages.map(s => {
      const pct = s.total ? Math.round(100 * s.done / s.total) : null;
      const bar = s.fact ? `<small class="plan-count">${esc(s.fact)}</small>` : pct == null ? "" : `<div class="plan-bar"><i style="width:${pct}%"></i></div><small class="plan-count">${s.done} из ${s.total} моделей</small>`;
      let status = "";
      if (s.state === "running") {
        const rest = s.next_models.length ? ` · далее: ${s.next_models.map(esc).join(", ")}${s.pending_count > s.next_models.length ? ` и ещё ${s.pending_count - s.next_models.length}` : ""}` : "";
        const cur = s.current_pct != null ? `<div class="plan-cur"><div class="plan-bar plan-bar-cur"><i style="width:${s.current_pct}%"></i></div><b>${s.pct_exact ? "" : "≈ "}${s.current_pct}%</b></div>` : "";
        status = `${cur}<p class="plan-now"><b>Сейчас тестируется:</b> ${esc(s.current || "подготовка")}</p>${s.eta_minutes ? `<p class="plan-calc"><b>Осталось до конца этапа ≈ ${fmtEta(s.eta_minutes)}.</b> Расчёт: ${s.model_eta_minutes != null ? `текущая модель ещё ≈ ${s.model_eta_minutes} мин` : "текущая модель ≈ среднее время"} + ${s.queue_count} ${plural(s.queue_count, "модель", "модели", "моделей")} в очереди × ${s.avg_minutes} мин (среднее по уже готовым) = ≈ ${s.eta_minutes} мин.</p>` : ""}<p class="plan-now">${rest}</p>${s.last ? `<small class="plan-last">последний итог: ${esc(s.last)}</small>` : ""}`;
      } else if (s.state === "paused") {
        status = `<p class="plan-now warn">Остановлен на ${s.done}${s.total ? ` из ${s.total}` : ""} — продолжится с готовых результатов.</p>`;
      } else if (s.state === "waiting") {
        status = `<p class="plan-wait">Ждёт${s.after && titles.get(s.after) ? `: стартует после «${esc(titles.get(s.after))}»` : ""}${s.id === plan.next ? " — следующий в очереди" : ""}.</p>`;
      } else if (s.note) status = `<p class="plan-wait">${esc(s.note)}</p>`;
      return `<li class="plan-item st-${s.state}"><span class="plan-icon" aria-hidden="true">${STAGE_ICON[s.state] || ""}</span>
        <div class="plan-body"><strong>${esc(s.title)}</strong><small class="plan-what">${esc(s.what || "")}</small>${bar}${status}</div></li>`;
    }).join("");
    const oldList = box.querySelector(".plan-list"), oldTop = oldList ? oldList.scrollTop : 0;
    const wasClosed = box.querySelector(".plan-box") && !box.querySelector(".plan-box").open;
    box.innerHTML = `<details class="plan-box" open><summary><span class="plan-sum-title">Ход тестирования</span><span class="plan-sum-now">${esc(summary)}</span></summary>
      ${doneTitles.length ? `<p class="plan-done-line">Пройдено: ${doneTitles.map(esc).join(" · ")}</p>` : ""}${stageBar(plan.overall)}<ol class="plan-list">${items}</ol></details>`;
    if (wasClosed) box.querySelector(".plan-box").open = false;
    const newList = box.querySelector(".plan-list");
    if (newList) newList.scrollTop = oldTop;
  }

  let testsData = null;
  function renderTests() {
    if (!testsData) return;
    const d = testsData, first = testsSeen.size === 0;
    const dropped = (d.plan?.stages || []).find(x => x.excluded?.length)?.excluded.length || 0;
    $("testsCount").textContent = `${d.total} ${plural(d.total, "модель", "модели", "моделей")}${dropped ? ` · допущено ${d.total - dropped}, снято ${dropped}` : ""}`;
    const ageMin = d.latest_result_utc ? Math.max(0, Math.round((Date.now() - Date.parse(d.latest_result_utc)) / 60000)) : null;
    const suites = (d.suites || []).map(s => `${s.label}: ${s.count}`).join(" · ");
    $("testsStatus").textContent = (ageMin == null ? "Результатов пока нет." : `Последний результат: ${ageMin < 1 ? "только что" : ageMin < 90 ? ageMin + " мин назад" : Math.round(ageMin / 60) + " ч назад"}`) + (suites ? ` · ${suites}` : "") + " · все результаты сохраняются в базу";
    renderTestControls();
    renderPlan(d.plan);
    const {metric, withVal, without} = sortedTests(d.entries || []);
    const rows = [];
    if (d.current) rows.push(`<article class="test-row running"><span class="test-no">${d.current.library_no ? "№ " + d.current.library_no : "№ —"}</span><div class="test-main"><strong>${esc(d.current.model)}</strong><small>тестируется прямо сейчас…</small><small class="test-log">${esc((d.current.log || []).slice(-2).join(" · "))}</small></div><span class="test-score wait">…</span></article>`);
    withVal.forEach((e, i) => { const key = e.model + ":" + e.updated_utc; rows.push(testRow(e, metric, i + 1, !first && testsSeen.get(e.model) !== key, true)); });
    without.forEach(e => { const key = e.model + ":" + e.updated_utc; rows.push(testRow(e, metric, 0, !first && testsSeen.get(e.model) !== key, false)); });
    (d.entries || []).forEach(e => testsSeen.set(e.model, e.model + ":" + e.updated_utc));
    const listTop = $("testsList").scrollTop;
    $("testsList").innerHTML = rows.join("") || '<p class="muted">Результатов пока нет.</p>';
    $("testsList").scrollTop = listTop;
  }
  async function refreshTests() {
    try {
      const d = await api("/api/tests");
      if (d.error) { $("testsStatus").textContent = d.error; return; }
      testsData = d; renderTests();
    } catch (e) { $("testsStatus").textContent = "Результаты недоступны: " + e.message; }
  }
  $("testsMetric").addEventListener("change", e => { testsMetric = e.target.value; testsFlip = false; saveTestsPrefs(); renderTests(); $("testsList").scrollTop = 0; });
  $("testsDir").addEventListener("click", () => { testsFlip = !testsFlip; saveTestsPrefs(); renderTests(); $("testsList").scrollTop = 0; });
  $("testsOnlyWith").addEventListener("change", e => { testsOnlyWith = e.target.checked; saveTestsPrefs(); renderTests(); });
  renderTestControls();
  refreshTests(); setInterval(refreshTests, 10000);
  refresh();
  (function pollStatus() {
    const busy=(status?.active_models||[]).some(m=>m.activity?.busy);
    setTimeout(()=>{
      if(currentJob&&["running","queued"].includes(currentJob.status)) { pollStatus(); return; }
      api("/api/status").then(s=>{status=s;renderStatus();}).catch(()=>{}).finally(pollStatus);
    },busy?1500:5000);
  })();
  refreshUnloadTimer();setInterval(renderUnloadTimer,250);setInterval(refreshUnloadTimer,1000);
})();
