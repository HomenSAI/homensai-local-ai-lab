/* Interface language (RU / EN / DE). The page text is written in Russian; this layer translates text nodes and
   placeholder / title / aria-label attributes in place, including text that scripts or the server insert later.
   Phrases are matched as whole words (Cyrillic-aware), longest first, so numbers and model names stay untouched.
   The phrase table lives in i18n-dict.js (window.I18N_DICT = [[ru, en, de], ...]). */
(() => {
  const D = window.I18N_DICT || [];
  const LANGS = {ru: 0, en: 1, de: 2};
  const SKIP = "script,style,textarea,input,pre,code,#chatLog,#jobLog,#rLog,[data-no-i18n]";
  const CYR = /[А-Яа-яЁё]/;
  const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  let lang = "ru";
  try { lang = localStorage.getItem("uiLang") || (navigator.language || "ru").slice(0, 2); } catch (e) { /* storage blocked */ }
  if (!(lang in LANGS)) lang = "ru";
  const maps = {}, regs = {};
  function build(code) {
    const idx = LANGS[code], map = new Map();
    for (const row of D) map.set(row[0].toLowerCase(), row[idx]);
    const keys = [...map.keys()].sort((a, b) => b.length - a.length).map(esc);
    maps[code] = map;
    regs[code] = new RegExp("(?<![А-Яа-яЁё])(?:" + keys.join("|") + ")(?![А-Яа-яЁё])", "gi");
  }
  function tr(text, code) {
    if (code === "ru" || !CYR.test(text)) return text;
    if (!regs[code]) build(code);
    const quoted = text.replace(regs[code], m => {
      const out = maps[code].get(m.toLowerCase());
      if (out == null) return m;
      return m[0] !== m[0].toLowerCase() && out[0] === out[0].toLowerCase() ? out[0].toUpperCase() + out.slice(1) : out;
    });
    return code === "de" ? quoted.replace(/«/g, "„").replace(/»/g, "“") : quoted.replace(/«/g, "“").replace(/»/g, "”");
  }
  const applied = new WeakMap();
  function node(n) {
    if (n.nodeType === 3) {
      const p = n.parentElement;
      if (!p || p.closest(SKIP)) return;
      const cur = n.nodeValue;
      if (applied.get(n) === cur) return;               // our own output
      const out = tr(cur, lang);
      applied.set(n, out);
      if (out !== cur) n.nodeValue = out;
    } else if (n.nodeType === 1) {
      if (n.closest("[data-no-i18n]")) return;
      for (const a of ["placeholder", "title", "aria-label"]) attr(n, a);
      if (n.closest(SKIP)) return;
      n.childNodes.forEach(node);
    }
  }
  function attr(el, name) {
    const v = el.getAttribute(name);
    if (!v || !CYR.test(v) || el.closest("[data-no-i18n]")) return;
    const out = tr(v, lang);
    if (out !== v) el.setAttribute(name, out);
  }
  let busy = false;
  const observer = new MutationObserver(list => {
    if (busy) return;
    busy = true;
    try {
      for (const m of list) {
        if (m.type === "characterData") node(m.target);
        else if (m.type === "attributes") attr(m.target, m.attributeName);
        else m.addedNodes.forEach(node);
      }
    } finally { busy = false; observer.takeRecords(); }
  });
  function start() {
    document.documentElement.lang = lang;
    if (lang !== "ru") {
      document.title = tr(document.title, lang);
      node(document.body);
      observer.observe(document.body, {subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ["placeholder", "title", "aria-label"]});
    }
    const bar = document.querySelector(".topbar");
    if (bar && !document.getElementById("langSwitch")) {
      const sel = document.createElement("select");
      sel.id = "langSwitch"; sel.className = "lang-switch"; sel.setAttribute("aria-label", "Language"); sel.setAttribute("data-no-i18n", "");
      sel.innerHTML = '<option value="ru">RU</option><option value="en">EN</option><option value="de">DE</option>';
      sel.value = lang;
      sel.addEventListener("change", () => { try { localStorage.setItem("uiLang", sel.value); } catch (e) { /* storage blocked */ } location.reload(); });
      bar.appendChild(sel);
    }
  }
  fetch("/api/version").then(r => r.json()).then(v => document.querySelectorAll("[data-version]").forEach(e => { e.textContent = "v" + v.version; if (v.repo) { const a = e.closest(".site-footer"); const link = a && a.querySelector("[data-repo]"); if (link) { link.href = v.repo; link.parentElement.hidden = false; } } })).catch(() => {});
  window.i18n = {tr: text => tr(text, lang), lang: () => lang};
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
