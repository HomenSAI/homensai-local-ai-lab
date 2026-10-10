// Lists Russian fragments in the UI sources that console/i18n-dict.js does not translate completely.
// Usage: node scripts/check_i18n.js [de|en]   (prints the missing fragments; exit code 1 if any)
const fs = require("fs");
const vm = require("vm");
const sandbox = { window: {} };
vm.runInNewContext(fs.readFileSync(process.env.I18N_DICT || "console/i18n-dict.js", "utf8"), sandbox);
const D = sandbox.window.I18N_DICT;
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
function build(i) {
  const m = new Map();
  for (const r of D) m.set(r[0].toLowerCase(), r[i]);
  const k = [...m.keys()].sort((a, b) => b.length - a.length).map(esc);
  return [m, new RegExp("(?<![А-Яа-яЁё])(?:" + k.join("|") + ")(?![А-Яа-яЁё])", "gi")];
}
const R = {en: build(1), de: build(2)};
const tr = (t, l) => t.replace(R[l][1], x => R[l][0].get(x.toLowerCase()) ?? x);
const files = ["console/index.html", "console/app.js", "console/container_server.py", "console/tests_feed.py", "report/index.html", "report/report.js", "report/progress.html", "report/progress.js", "report/live.js", "scripts/build_live_report.py"];
const files2 = process.env.I18N_FILES ? process.env.I18N_FILES.split(",") : null;
const lang = process.argv[2] || "de";
const missing = new Map();
for (const f of (files2 || files)) {
  let t = fs.readFileSync(f, "utf8");
  t = t.replace(/\$\{[^}]*\}/g, "\u0001");
  if (f.endsWith(".py")) t = t.replace(/\{[^{}]*\}/g, "\u0001");
  for (const line of t.split("\n")) {
    if (/^\s*(#|\/\/)/.test(line)) continue;
    for (const m of line.matchAll(/[«А-Яа-яЁё][А-Яа-яЁё0-9 ,.:;!?()«»"%\/·—–\-'+№]*/g)) {
      const s = m[0].trim().replace(/[ ,.:;"']+$/, "");
      if (s.length < 2) continue;
      const o = tr(s, lang);
      if (/[А-Яа-яЁё]/.test(o) && !missing.has(s)) missing.set(s, f);
    }
  }
}
for (const [s, f] of missing) console.log(f.split("/").pop() + " | " + s);
console.log("missing:", missing.size);
process.exit(missing.size ? 1 : 0);
