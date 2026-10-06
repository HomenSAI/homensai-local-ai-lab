/* Excel-style sorting for every table of the report.
   Click a header: ascending; click again: descending; third click: back to the original order.
   Shift+click adds a further sort level (1, 2, 3 ... shown next to the arrow). Numbers, percentages, "12 / 19", dates and text are
   recognised; empty cells ("", "-", "n/a") always stay at the bottom. The sort is re-applied whenever the page re-renders a table. */
(() => {
  const EMPTY = /^(|-|—|–|n\/a|нет данных|none)$/i;
  const NUM = /-?\d+(?:[  ]\d{3})*(?:[.,]\d+)?/;
  const DATE = /^(\d{2})\.(\d{2})\.(\d{4})(?:[, ]+(\d{2}):(\d{2})(?::(\d{2}))?)?/;
  const ISO = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/;
  const states = new WeakMap();

  function value(cell) {
    const raw = (cell.dataset.sort ?? cell.innerText ?? "").replace(/ /g, " ").trim();
    if (EMPTY.test(raw)) return {empty: true};
    let m = raw.match(DATE);
    if (m) return {num: Date.UTC(+m[3], +m[2] - 1, +m[1], +(m[4] || 0), +(m[5] || 0), +(m[6] || 0))};
    m = raw.match(ISO);
    if (m) return {num: Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0))};
    m = raw.match(NUM);
    if (m && raw.indexOf(m[0]) <= 2 && raw.length - m[0].length <= 24) {
      const number = parseFloat(m[0].replace(/[  ]/g, "").replace(",", "."));
      if (!Number.isNaN(number)) return {num: number, text: raw};
    }
    return {text: raw.toLowerCase()};
  }

  function compare(a, b) {
    if (a.num !== undefined && b.num !== undefined) return a.num - b.num || 0;
    if (a.num !== undefined) return -1;
    if (b.num !== undefined) return 1;
    return (a.text || "").localeCompare(b.text || "", undefined, {numeric: true, sensitivity: "base"});
  }

  function apply(table) {
    const st = states.get(table), body = table.tBodies[0];
    if (!body) return;
    const rows = [...body.rows];
    rows.forEach((row, i) => { if (row.__i === undefined || !st.seen.has(row)) { row.__i = i; st.seen.add(row); } });
    let ordered = rows;
    if (st.keys.length) {
      const cache = new Map(rows.map(r => [r, st.keys.map(k => value(r.cells[k.col] || document.createElement("td")))]));
      ordered = [...rows].sort((r1, r2) => {
        const v1 = cache.get(r1), v2 = cache.get(r2);
        for (let i = 0; i < st.keys.length; i++) {
          const a = v1[i], b = v2[i];
          if (a.empty || b.empty) { if (a.empty && b.empty) continue; return a.empty ? 1 : -1; }   // blanks always last
          const c = compare(a, b);
          if (c) return st.keys[i].dir === "asc" ? c : -c;
        }
        return r1.__i - r2.__i;
      });
    } else ordered = [...rows].sort((a, b) => a.__i - b.__i);
    if (ordered.some((r, i) => r !== rows[i])) {
      st.busy = true;
      ordered.forEach(r => body.appendChild(r));
      st.observer.takeRecords();
      st.busy = false;
    }
    [...table.tHead.rows[table.tHead.rows.length - 1].cells].forEach((th, col) => {
      const i = st.keys.findIndex(k => k.col === col), mark = th.querySelector(".sort-ind");
      th.setAttribute("aria-sort", i < 0 ? "none" : st.keys[i].dir === "asc" ? "ascending" : "descending");
      if (mark) mark.textContent = i < 0 ? "↕" : (st.keys[i].dir === "asc" ? "▲" : "▼") + (st.keys.length > 1 ? i + 1 : "");
      th.classList.toggle("sorted", i >= 0);
    });
  }

  function click(table, col, shift) {
    const st = states.get(table), at = st.keys.findIndex(k => k.col === col);
    if (shift) {
      if (at < 0) st.keys.push({col, dir: "asc"});
      else if (st.keys[at].dir === "asc") st.keys[at].dir = "desc";
      else st.keys.splice(at, 1);
    } else if (at >= 0 && st.keys.length === 1) {
      if (st.keys[0].dir === "asc") st.keys[0].dir = "desc"; else st.keys = [];
    } else st.keys = [{col, dir: "asc"}];
    apply(table);
  }

  function setup(table) {
    if (states.has(table) || !table.tHead || !table.tBodies[0]) return;
    const headRow = table.tHead.rows[table.tHead.rows.length - 1];
    const st = {keys: [], seen: new WeakSet(), busy: false, observer: null};
    states.set(table, st);
    [...headRow.cells].forEach((th, col) => {
      th.classList.add("sortable");
      th.tabIndex = 0;
      th.setAttribute("role", "columnheader");
      th.title = "Сортировка: щелчок — по возрастанию, ещё раз — по убыванию, третий — сбросить; Shift+щелчок — добавить уровень сортировки";
      const mark = document.createElement("span");
      mark.className = "sort-ind"; mark.setAttribute("aria-hidden", "true"); mark.textContent = "↕";
      th.appendChild(mark);
      th.addEventListener("click", e => click(table, col, e.shiftKey));
      th.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); click(table, col, e.shiftKey); } });
    });
    st.observer = new MutationObserver(() => { if (!st.busy && st.keys.length) apply(table); else if (!st.busy) { [...table.tBodies[0].rows].forEach((r, i) => { r.__i = i; st.seen.add(r); }); } });
    st.observer.observe(table.tBodies[0], {childList: true});
    apply(table);
  }

  function init() { document.querySelectorAll("table").forEach(setup); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
  window.tableSort = {init};
})();
