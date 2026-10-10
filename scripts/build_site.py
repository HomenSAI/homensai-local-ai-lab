#!/usr/bin/env python3
# Local AI Lab - (c) 2026 Serhii Khomenko - https://homensai.com/
"""Builds the documentation site (GitHub Pages) with the site builder of HomenS.AI Style (SITE_RULES.md of the core).

The Markdown files stay the source. This script turns them into the page content of the core site builder:
site/site.json and site/content/<page>.<lang>.body.html (only what goes inside <main>), then runs
`tools/site.py build site` of the style core, which writes the pages site/<page>.<lang>.html with the fixed frame
of every HomenS.AI site (logo, menu, EN | DE | RU buttons, theme, footer, "Top", Contact page with the robot) and copies
the core into site/style/. The old page addresses (index.html, README.ru.html, docs/INSTALL.ru.html, ...) become
redirects to the new pages; .nojekyll makes GitHub Pages serve everything as it is.

  python scripts/build_site.py [--style ../homensai-style]   # build (needs a copy of the style core, version >= 1.8.0)
  python scripts/build_site.py --check                       # CI: content, redirects and pages are up to date

The style core is found with --style, the HOMENSAI_STYLE variable or ../homensai-style. Standard library only.
"""
import html
import json
import os
import posixpath
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "site"
REPO_URL = "https://github.com/HomenSAI/homensai-local-ai-lab"
BENCH_URL = "https://github.com/HomenSAI/rtx3080-local-ai-benchmarks"
LANGS = ["en", "ru", "de"]               # the first language gets index.html (the address people already link)
MIN_CORE = (1, 8, 0)                     # subpages ("parent") came with HomenS.AI Style 1.8.0
AUTHOR = ("<!-- HomenS.AI Local AI Lab · © 2026 Serhii Khomenko · https://homensai.com/ · https://github.com/HomenSAI · "
          "https://www.linkedin.com/in/serhii-khomenko-homensai/ -->")


def L(en, ru, de):
    return {"en": en, "ru": ru, "de": de}


def by_lang(pattern):
    return {lang: pattern.format(lang=lang) for lang in LANGS}


def plain_and(path, ru, de):
    return {"en": path, "ru": ru, "de": de}


# The site: menu pages, the documentation section with its subpages, external menu items. "src" is the Markdown file
# per language; a (file, heading) pair takes one language section of a file written in three languages.
PAGES = [
    dict(id="home", nav=L("Home", "Главная", "Start"), src=plain_and("README.md", "README.ru.md", "README.de.md")),
    dict(id="install", nav=L("Installation", "Установка", "Installation"), src=by_lang("docs/INSTALL.{lang}.md")),
    dict(id="docs", nav=L("Documentation", "Документация", "Dokumentation"), hub=True,
         title=L("Documentation", "Документация", "Dokumentation")),
    dict(id="operator", parent="docs", group=0, src=by_lang("docs/AI_OPERATOR.{lang}.md"),
         desc=L("How an AI assistant installs the server, runs the tests and checks every result.",
                "Как ИИ-ассистент ставит сервер, запускает тесты и проверяет каждый результат.",
                "Wie ein KI-Assistent den Server installiert, die Tests startet und jedes Ergebnis prüft.")),
    dict(id="prompt", parent="docs", group=0,
         src={"en": ("PROMPT_FOR_AI.md", "English"), "ru": ("PROMPT_FOR_AI.md", "Русский"), "de": ("PROMPT_FOR_AI.md", "Deutsch")},
         title=L("Start here: the prompt for your AI assistant", "Начните здесь: промпт для вашего ИИ-ассистента",
                 "Hier beginnen: der Prompt für Ihren KI-Assistenten"),
         desc=L("The text to paste into an assistant that can run commands on your PC; optional.",
                "Текст, который вставляют ассистенту, умеющему выполнять команды на вашем ПК; необязательно.",
                "Der Text für einen Assistenten, der Befehle auf Ihrem PC ausführen kann; optional.")),
    dict(id="virtual-3080", parent="docs", group=0, src=plain_and("tests/virtual-3080/README.md",
                                                                  "tests/virtual-3080/README.ru.md", "tests/virtual-3080/README.de.md"),
         desc=L("Install and try the whole system on a Linux machine without a GPU, with a virtual RTX 3080.",
                "Поставить и опробовать всю систему на Linux-машине без видеокарты, с виртуальной RTX 3080.",
                "Das ganze System auf einem Linux-Rechner ohne Grafikkarte mit einer virtuellen RTX 3080 ausprobieren.")),
    dict(id="methodology", parent="docs", group=1, src=by_lang("docs/METHODOLOGY.{lang}.md"),
         desc=L("How the published results were produced and which rules the tests follow.",
                "Как получены опубликованные результаты и по каким правилам идут тесты.",
                "Wie die veröffentlichten Ergebnisse entstanden und nach welchen Regeln getestet wird.")),
    dict(id="runners", parent="docs", group=1, src=plain_and("benchmarks/README.md", "benchmarks/README.ru.md", "benchmarks/README.de.md"),
         desc=L("Every test, its runner, its task set and its result file.",
                "Каждый тест: его раннер, набор задач и файл результатов.",
                "Jeder Test mit Runner, Aufgabensatz und Ergebnisdatei.")),
    dict(id="results-format", parent="docs", group=1, src=plain_and("docs/RESULTS_FORMAT.md", "docs/RESULTS_FORMAT.ru.md", "docs/RESULTS_FORMAT.de.md"),
         desc=L("The result files and the stage plan that a test tool writes for the report.",
                "Файлы результатов и план этапов, которые инструмент тестирования пишет для отчёта.",
                "Ergebnisdateien und Phasenplan, die ein Testwerkzeug für den Bericht schreibt.")),
    dict(id="models", parent="docs", group=1, src=plain_and("MODELS.md", "MODELS.ru.md", "MODELS.de.md"),
         desc=L("The models and gateway profiles, with sources, sizes and checksums.",
                "Модели и профили шлюза: источники, размеры и контрольные суммы.",
                "Modelle und Gateway-Profile mit Quellen, Größen und Prüfsummen.")),
    dict(id="design", parent="docs", group=2, src=by_lang("docs/DESIGN.{lang}.md"),
         desc=L("Why the server is built this way: every decision with its reason.",
                "Почему сервер устроен именно так: каждое решение и его причина.",
                "Warum der Server so gebaut ist: jede Entscheidung mit Begründung.")),
    dict(id="architecture", parent="docs", group=2, src=plain_and("docs/ARCHITECTURE.md", "docs/ARCHITECTURE.ru.md", "docs/ARCHITECTURE.de.md"),
         desc=L("The containers, the files of the repository and how data flows between them.",
                "Контейнеры, файлы репозитория и как между ними идут данные.",
                "Container, Dateien des Repositorys und wie Daten zwischen ihnen fließen.")),
    dict(id="api", parent="docs", group=2, src=plain_and("docs/API.md", "docs/API.ru.md", "docs/API.de.md"),
         desc=L("The HTTP interfaces of the console and the gateway for operators and scripts.",
                "HTTP-интерфейсы консоли и шлюза для операторов и скриптов.",
                "Die HTTP-Schnittstellen von Konsole und Gateway für Betreiber und Skripte.")),
    dict(id="security", parent="docs", group=2, src=plain_and("SECURITY.md", "SECURITY.ru.md", "SECURITY.de.md"),
         desc=L("Threat model, protections of the console and how to report a vulnerability.",
                "Модель угроз, защита консоли и как сообщить об уязвимости.",
                "Bedrohungsmodell, Schutz der Konsole und wie man eine Schwachstelle meldet.")),
    dict(id="licences", parent="docs", group=2, src=by_lang("legal/README.md"),
         title=L("Licences", "Лицензии", "Lizenzen"),
         desc=L("Noncommercial licences of the results and of the code, third-party rights.",
                "Некоммерческие лицензии результатов и кода, права третьих лиц.",
                "Nichtkommerzielle Lizenzen der Ergebnisse und des Codes, Rechte Dritter.")),
    dict(id="results", nav=L("Results", "Результаты", "Ergebnisse"), href=BENCH_URL),
    dict(id="github", nav=L("GitHub", "GitHub", "GitHub"), href=REPO_URL),
]
GROUPS = [L("Install and run", "Установка и работа", "Installieren und betreiben"),
          L("Tests and results", "Тесты и результаты", "Tests und Ergebnisse"),
          L("How it is built", "Как это устроено", "Wie es gebaut ist")]
UI = {
    "en": dict(toc="Contents", back="Documentation", source="Source text on GitHub", hub_lead=(
        "Everything about the server: installation, the tests, how it is built. The Markdown files in the repository are the "
        "source of these pages."), changelog="What changed in each version", changelog_where="changelog on GitHub",
        about="Local AI Lab", about_text=(
        "A self-hosted server for local language models on one NVIDIA graphics card: gateway, web console, automatic test "
        "reports and versions of the results."),
        licence="Results and code may be used only for noncommercial purposes with credit to the author (homensai.com).",
        repo="Source code on GitHub", moved="This page has moved"),
    "ru": dict(toc="Содержание", back="Документация", source="Исходный текст на GitHub", hub_lead=(
        "Всё о сервере: установка, тесты, устройство. Источник этих страниц — файлы Markdown в репозитории."),
        changelog="Что изменилось в каждой версии", changelog_where="журнал изменений на GitHub",
        about="Local AI Lab", about_text=(
        "Самостоятельно разворачиваемый сервер для локальных языковых моделей на одной видеокарте NVIDIA: шлюз, "
        "веб-консоль, автоматические отчёты по тестам и версии результатов."),
        licence="Результаты и код можно использовать только в некоммерческих целях со ссылкой на автора (homensai.com).",
        repo="Исходный код на GitHub", moved="Страница переехала"),
    "de": dict(toc="Inhalt", back="Dokumentation", source="Quelltext auf GitHub", hub_lead=(
        "Alles über den Server: Installation, Tests, Aufbau. Die Quelle dieser Seiten sind die Markdown-Dateien im "
        "Repository."), changelog="Was sich in jeder Version geändert hat", changelog_where="Änderungsprotokoll auf GitHub",
        about="Local AI Lab", about_text=(
        "Ein selbst betriebener Server für lokale Sprachmodelle auf einer NVIDIA-Grafikkarte: Gateway, Webkonsole, "
        "automatische Testberichte und Versionen der Ergebnisse."),
        licence="Ergebnisse und Code dürfen nur nichtkommerziell und mit Nennung des Autors (homensai.com) verwendet werden.",
        repo="Quellcode auf GitHub", moved="Diese Seite ist umgezogen"),
}
# Files that stay on GitHub: a link that only shows their file name gets a readable text (SITE_RULES.md, section 5).
GITHUB_LABELS = {
    "results-public/RESULTS.md": L("published test results (GitHub)", "опубликованные результаты тестов (GitHub)",
                                   "veröffentlichte Testergebnisse (GitHub)"),
    "results-public": L("folder of the published results (GitHub)", "папка опубликованных результатов (GitHub)",
                        "Ordner der veröffentlichten Ergebnisse (GitHub)"),
    "legal/NOTICE-THIRD-PARTY.md": L("third-party rights (GitHub)", "права третьих лиц (GitHub)", "Rechte Dritter (GitHub)"),
    "tests/virtual-3080/REPORT.ru.md": L("test report of 10.10.2026, in Russian (GitHub)", "отчёт о проверке 10.10.2026 (GitHub)",
                                         "Prüfbericht vom 10.10.2026, auf Russisch (GitHub)"),
}
CONTENTS_HEADINGS = {"содержание", "contents", "table of contents", "inhalt", "inhaltsverzeichnis"}
LANG_LINE = re.compile(r"^(?:\*\*English\*\*\s*·.*|(?:Other languages|Другие языки|Andere Sprachen|Languages|Языки|Sprachen)\s*:.*)$")
MAIL = re.compile(r"\b([A-Za-z0-9._%+-]+)@homensai\.com\b")


# ------------------------------------------------------------------------------------------------ Markdown -> HTML
def slug(text, used):
    """Anchor of a heading the way GitHub makes it, so links like (#4-step-by-step-installation) keep working."""
    s = re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")
    base, n = s, 1
    while s in used:
        s = f"{base}-{n}"
        n += 1
    used.add(s)
    return s


class Markdown:
    """The Markdown used in this repository: headings, paragraphs, lists with nested blocks, tables, fenced code,
    quotes, rules, links, images, code spans, emphasis, autolinks. Raw HTML is shown as text."""

    def __init__(self, link):
        self.link = link             # function(href) -> href for the page
        self.used = set()
        self.headings = []           # (level, id, text, html)

    # ---------------------------------------------------------------- inline
    def inline(self, text, links=True, keep=None):
        keep = [] if keep is None else keep           # held fragments, shared with the text of a link

        def hold(fragment):
            keep.append(fragment)
            return f"\x00{len(keep) - 1}\x00"

        def code(m):
            return hold("<code>" + html.escape(m.group(2).strip() if m.group(2).strip() else m.group(2)) + "</code>")

        text = re.sub(r"(`+)(.+?)\1", code, text)
        text = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|<>~])", lambda m: hold(html.escape(m.group(1))), text)
        if links:
            text = re.sub(r"<((?:https?|mailto):[^\s<>]+)>",
                          lambda m: hold(f'<a href="{html.escape(self.link(m.group(1)))}">{html.escape(m.group(1))}</a>'), text)
            text = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
                          lambda m: hold(f'<img src="{html.escape(self.link(m.group(2)))}" alt="{html.escape(m.group(1))}">'), text)

            def link(m):
                href = self.link(m.group(2))
                external = re.match(r"https?:", href) and not href.startswith(REPO_URL + "/blob")
                attrs = ' rel="noopener"' if external else ""
                return hold(f'<a href="{html.escape(href)}"{attrs}>{self.inline(m.group(1), links=False, keep=keep)}</a>')

            text = re.sub(r"\[((?:[^\[\]]|\[[^\]]*\])+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", link, text)
        text = html.escape(text, quote=False)
        if links:
            def bare(m):
                url = m.group(0)
                tail = ""
                while url and url[-1] in ".,;:!?)»":
                    tail = url[-1] + tail
                    url = url[:-1]
                return hold(f'<a href="{html.escape(url)}" rel="noopener">{url}</a>') + tail

            text = re.sub(r"https?://[^\s<>\x00\"]+", bare, text)
        text = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"(?<![\w])__(?=\S)(.+?)(?<=\S)__(?![\w])", r"<strong>\1</strong>", text)
        text = re.sub(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])", r"<em>\1</em>", text)
        text = re.sub(r"(?<![\w])_(?=[^\s_])(.+?)(?<=[^\s_])_(?![\w])", r"<em>\1</em>", text)
        text = re.sub(r"(?: {2,}|\\)\n", "<br>\n", text)
        while "\x00" in text:
            text = re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], text)
        return text

    # ---------------------------------------------------------------- blocks
    LIST = re.compile(r"^( {0,3})([-*+]|\d{1,9}[.)])( +|$)")
    FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
    HEAD = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
    RULE = re.compile(r"^ {0,3}([-*_])(?:\s*\1){2,}\s*$")

    def starts_block(self, line):
        return bool(self.FENCE.match(line) or self.HEAD.match(line) or self.RULE.match(line) or self.LIST.match(line)
                    or line.lstrip().startswith(">") or line.lstrip().startswith("|"))

    def blocks(self, lines):
        out, i = [], 0
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            m = self.FENCE.match(line)
            if m:
                mark, info = m.group(1), m.group(2).strip()
                indent = len(line) - len(line.lstrip())
                body, i = [], i + 1
                while i < len(lines) and not re.match(r"^ {0,3}" + re.escape(mark[0]) + "{" + str(len(mark)) + r",}\s*$", lines[i]):
                    body.append(lines[i][indent:] if lines[i][:indent].strip() == "" else lines[i])
                    i += 1
                i += 1
                cls = f' class="language-{html.escape(info.split()[0])}"' if info else ""
                out.append(f"<pre><code{cls}>" + html.escape("\n".join(body)) + "</code></pre>")
                continue
            m = self.HEAD.match(line)
            if m:
                level, content = len(m.group(1)), m.group(2)
                rendered = self.inline(content)
                plain = html.unescape(re.sub(r"<[^>]+>", "", rendered))
                hid = slug(plain, self.used)
                self.headings.append((level, hid, plain, rendered))
                out.append(f'<h{level} id="{hid}">{rendered}</h{level}>')
                i += 1
                continue
            if self.RULE.match(line):
                out.append("<hr>")
                i += 1
                continue
            if line.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$", lines[i + 1]):
                i = self.table(lines, i, out)
                continue
            if line.lstrip().startswith(">"):
                quote = []
                while i < len(lines) and lines[i].strip() and (lines[i].lstrip().startswith(">") or not self.starts_block(lines[i])):
                    quote.append(re.sub(r"^\s*> ?", "", lines[i]))
                    i += 1
                out.append("<blockquote>\n" + "\n".join(self.blocks(quote)) + "\n</blockquote>")
                continue
            if self.LIST.match(line):
                i = self.list(lines, i, out)
                continue
            para = [line.strip()]
            i += 1
            while i < len(lines) and lines[i].strip() and not self.starts_block(lines[i]):
                para.append(lines[i].strip() if not lines[i].endswith("  ") else lines[i].strip() + "  ")
                i += 1
            out.append("<p>" + self.inline("\n".join(para)) + "</p>")
        return out

    def cells(self, row):
        row = row.strip()
        row = row[1:] if row.startswith("|") else row
        row = row[:-1] if row.endswith("|") and not row.endswith("\\|") else row
        parts, cur, tick = [], "", False
        k = 0
        while k < len(row):
            ch = row[k]
            if ch == "\\" and k + 1 < len(row) and row[k + 1] == "|":
                cur += "\\|"
                k += 2
                continue
            if ch == "`":
                tick = not tick
            if ch == "|" and not tick:
                parts.append(cur.strip())
                cur = ""
            else:
                cur += ch
            k += 1
        parts.append(cur.strip())
        return parts

    def table(self, lines, i, out):
        head = self.cells(lines[i])
        aligns = []
        for spec in self.cells(lines[i + 1]):
            aligns.append("center" if spec.startswith(":") and spec.endswith(":") else "right" if spec.endswith(":") else "")
        i += 2
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            rows.append(self.cells(lines[i]))
            i += 1

        def cell(tag, text, k):
            a = aligns[k] if k < len(aligns) else ""
            cls = f' class="{"n" if a == "right" else "c"}"' if a else ""
            return f"<{tag}{cls}>{self.inline(text.replace(chr(92) + '|', '|'))}</{tag}>"

        h = "".join(cell("th", t, k) for k, t in enumerate(head))
        body = "\n".join("<tr>" + "".join(cell("td", t, k) for k, t in enumerate(r[:len(head)] + [""] * (len(head) - len(r)))) + "</tr>"
                         for r in rows)
        out.append(f'<div class="table-wrap"><table>\n<thead><tr>{h}</tr></thead>\n<tbody>\n{body}\n</tbody>\n</table></div>')
        return i

    def list(self, lines, i, out):
        first = self.LIST.match(lines[i])
        ordered = first.group(2)[0].isdigit()
        start = int(first.group(2)[:-1]) if ordered else 1
        items, loose = [], False
        while i < len(lines):
            m = self.LIST.match(lines[i])
            if not m or m.group(2)[0].isdigit() != ordered:
                break
            col = len(m.group(1)) + len(m.group(2)) + max(1, min(len(m.group(3)), 4))
            body = [lines[i][len(m.group(0)):]]
            i += 1
            while i < len(lines):
                line = lines[i]
                if not line.strip():
                    nxt = next((l for l in lines[i + 1:] if l.strip()), None)
                    if nxt is not None and len(nxt) - len(nxt.lstrip()) >= col:
                        body.append("")
                        loose = loose or not self.FENCE.match(nxt)
                        i += 1
                        continue
                    break
                indent = len(line) - len(line.lstrip())
                if indent >= col:
                    body.append(line[col:])
                elif self.LIST.match(line) or self.starts_block(line):
                    break
                else:
                    body.append(line.strip())          # lazy continuation of the paragraph
                i += 1
            items.append(body)
            if i < len(lines) and not lines[i].strip():
                nxt = next((k for k in range(i, len(lines)) if lines[k].strip()), None)
                if nxt is not None and self.LIST.match(lines[nxt]) and self.LIST.match(lines[nxt]).group(2)[0].isdigit() == ordered:
                    loose = True
                    i = nxt
        html_items = []
        for body in items:
            parts = self.blocks(body)
            if not loose and parts and parts[0].startswith("<p>"):
                parts[0] = parts[0][3:-4]
            html_items.append("<li>" + "\n".join(parts) + "</li>")
        tag = "ol" if ordered else "ul"
        attr = f' start="{start}"' if ordered and start != 1 else ""
        out.append(f"<{tag}{attr}>\n" + "\n".join(html_items) + f"\n</{tag}>")
        return i

    def render(self, text):
        return "\n".join(self.blocks(text.replace("\r\n", "\n").replace("\t", "    ").split("\n")))


# ------------------------------------------------------------------------------------------------ site
def read(rel_path):
    with open(os.path.join(ROOT, rel_path), encoding="utf-8") as f:
        return f.read()


def page_file(pid, lang):
    """File names of the core site builder: home -> index.html (first language) / index.<lang>.html, else <id>.<lang>.html."""
    if pid == "home":
        return "index.html" if lang == LANGS[0] else f"index.{lang}.html"
    return f"{pid}.{lang}.html"


def tracked_markdown():
    try:
        done = subprocess.run(["git", "ls-files", "-z", "*.md"], cwd=ROOT, capture_output=True, check=True)
        files = [f for f in done.stdout.decode("utf-8").split("\0") if f]
    except (OSError, subprocess.CalledProcessError):
        files = []
        for top, dirs, names in os.walk(ROOT):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in {"bench_results", "secrets", "node_modules", "site"})
            files += [os.path.relpath(os.path.join(top, n), ROOT).replace(os.sep, "/") for n in names if n.endswith(".md")]
    return sorted(f for f in files if not f.startswith(SITE + "/") and os.path.exists(os.path.join(ROOT, f)))


def old_page(md):
    """Where the previous sites (GitHub's own theme, then version 1.5.0) served a Markdown file."""
    return "index.html" if md == "README.md" else md[:-3] + ".html"


def source_text(src):
    """Markdown of one page language: a whole file, or one '## <heading>' section of a file in three languages."""
    if isinstance(src, str):
        return read(src)
    path, heading = src
    text = read(path)
    m = re.search(r"^## " + re.escape(heading) + r"\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        raise SystemExit(f"{path}: no section '## {heading}'")
    return m.group(1)


def src_path(src):
    return src if isinstance(src, str) else src[0]


class Site:
    def __init__(self):
        self.version = read("VERSION").strip()
        self.md_page = {}                                     # Markdown file -> (page id, language of the file or None)
        for p in PAGES:
            for lang, src in (p.get("src") or {}).items():
                path = src_path(src)
                single = len({src_path(s) for s in p["src"].values()}) == 1
                self.md_page.setdefault(path, (p["id"], None if single else lang))

    # ---------------------------------------------------------------- links inside the content
    def link(self, href, md, lang):
        if re.match(r"^[a-z][a-z0-9+.-]*:", href, re.I) or href.startswith("#"):
            return href
        path, _, frag = href.partition("#")
        frag = "#" + frag if frag else ""
        target = posixpath.normpath(posixpath.join(posixpath.dirname(md), path)) if path else md
        if target.startswith(".."):
            return href
        if target in self.md_page:
            return page_file(self.md_page[target][0], lang) + frag
        if os.path.isdir(os.path.join(ROOT, target)) or path.endswith("/"):
            readme = target.rstrip("/") + "/README.md"
            if readme in self.md_page:
                return page_file(self.md_page[readme][0], lang) + frag
            return f"{REPO_URL}/tree/main/{target.rstrip('/')}"
        return f"{REPO_URL}/blob/main/{target}{frag}"

    # ---------------------------------------------------------------- page content (inside <main>)
    def doc_body(self, page, lang):
        src = page["src"][lang]
        md = src_path(src)
        text = "\n".join(line for line in source_text(src).split("\n") if not LANG_LINE.match(line.strip()))
        text = MAIL.sub(r"\1 [at] homensai [dot] com", text)
        conv = Markdown(lambda href: self.link(href, md, lang))
        body = conv.render(text)
        h1 = next((h for h in conv.headings if h[0] == 1), None)
        title = (page.get("title") or {}).get(lang) or (h1[2] if h1 else page["id"])
        if h1:
            body = re.sub(r'<h1 id="[^"]*">.*?</h1>\n?', "", body, count=1, flags=re.S)
            heading = f'<h1 id="{h1[1]}">{h1[3]}</h1>' if not page.get("title") else f"<h1>{html.escape(title)}</h1>"
        else:
            heading = f"<h1>{html.escape(title)}</h1>"
        ui = UI[lang]
        h2 = [h for h in conv.headings if h[0] == 2]
        toc = ""
        if len(h2) >= 3 and not any(h[2].strip().lower() in CONTENTS_HEADINGS for h in conv.headings):
            items = "".join(f'<li><a href="#{h[1]}">{html.escape(h[2])}</a></li>' for h in h2)
            toc = f'\n    <nav class="card help-toc doc-toc" aria-label="{ui["toc"]}"><h2>{ui["toc"]}</h2><ol>{items}</ol></nav>'
        back = f'<a href="{page_file(page["parent"], lang)}">← {ui["back"]}</a> · ' if page.get("parent") else ""
        meta = f'\n    <p class="doc-meta">{back}<a href="{REPO_URL}/blob/main/{md}" rel="noopener">{ui["source"]}</a></p>'
        names = getattr(self, "titles", {})              # a link that shows a file name gets the title of the page
        files = {page_file(pid, lng): t for (pid, lng), t in names.items()}
        body = re.sub(r'<a href="([^"#:]+\.html)(#[^"]*)?">([\w./-]+\.md)</a>',
                      lambda m: f'<a href="{m.group(1)}{m.group(2) or ""}">{html.escape(files[m.group(1)])}</a>'
                      if m.group(1) in files else m.group(0), body)
        def readable(m):
            kind, path, attrs, text = m.groups()
            if path not in GITHUB_LABELS or not re.fullmatch(r"[\w./-]+", text):
                return m.group(0)
            return f'<a href="{REPO_URL}/{kind}/main/{path}"{attrs}>{html.escape(GITHUB_LABELS[path][lang])}</a>'
        body = re.sub(r'<a href="' + re.escape(REPO_URL) + r'/(blob|tree)/main/([^"#]+)"([^>]*)>([^<]*)</a>', readable, body)
        return title, f"{AUTHOR}\n    {heading}{toc}\n    <article class=\"card lesson-body doc-body\">\n{body}\n    </article>{meta}\n"

    def hub_body(self, page, lang):
        ui = UI[lang]
        parts = [f"{AUTHOR}\n    <h1>{html.escape(page['title'][lang])}</h1>\n    <p class=\"lead\">{html.escape(ui['hub_lead'])}</p>"]
        for g, group in enumerate(GROUPS):
            cards = []
            for p in PAGES:
                if p.get("parent") != page["id"] or p.get("group") != g:
                    continue
                title = self.titles[(p["id"], lang)]
                cards.append(f'      <section class="card doc-card"><h3><a href="{page_file(p["id"], lang)}">{html.escape(title)}</a></h3>'
                             f'<p>{html.escape(p["desc"][lang])}</p></section>')
            parts.append(f"    <h2>{html.escape(group[lang])}</h2>\n    <div class=\"grid2 doc-cards\">\n" + "\n".join(cards) + "\n    </div>")
        parts.append(f'    <p class="doc-meta">{html.escape(ui["changelog"])}: <a href="{REPO_URL}/blob/main/CHANGELOG.md" rel="noopener">'
                     f'{html.escape(ui["changelog_where"])}</a></p>\n')
        return "\n".join(parts)

    def contact_body(self, lang):
        ui = UI[lang]
        return (f"{AUTHOR}\n      <section class=\"card\"><h2>{ui['about']}</h2><p>{html.escape(ui['about_text'])}</p>"
                f"<p>{html.escape(ui['licence'])}</p><p><a href=\"{REPO_URL}\" rel=\"noopener\">{ui['repo']}</a> · "
                f"<a href=\"{page_file('licences', lang)}\">{html.escape(self.titles[('licences', lang)])}</a></p></section>\n")

    # ---------------------------------------------------------------- everything the core builder reads
    def sources(self):
        files, self.titles = {}, {}
        bodies = {}
        for p in PAGES:                                     # first the titles, then the bodies that name them
            if "src" in p:
                for lang in LANGS:
                    self.titles[(p["id"], lang)] = self.doc_body(p, lang)[0]
            elif p.get("hub"):
                for lang in LANGS:
                    self.titles[(p["id"], lang)] = p["title"][lang]
        for p in PAGES:
            if "src" in p:
                for lang in LANGS:
                    title, body = self.doc_body(p, lang)
                    self.titles[(p["id"], lang)] = title
                    bodies[(p["id"], lang)] = body
        for p in PAGES:
            if p.get("hub"):
                for lang in LANGS:
                    self.titles[(p["id"], lang)] = p["title"][lang]
                    bodies[(p["id"], lang)] = self.hub_body(p, lang)
        for (pid, lang), body in bodies.items():
            files[f"{SITE}/content/{pid}.{lang}.body.html"] = body
        for lang in LANGS:
            files[f"{SITE}/content/contact.{lang}.body.html"] = self.contact_body(lang)
        pages = []
        for p in PAGES:
            item = {"id": p["id"]}
            if p.get("parent"):
                item["parent"] = p["parent"]
            else:
                item["nav"] = p["nav"]
            if "href" in p:
                item["href"] = p["href"]
            elif p["id"] != "home":
                item["title"] = {lang: self.titles[(p["id"], lang)] for lang in LANGS}
            pages.append(item)
        config = {"name": "Local AI Lab", "title": L("Local AI Lab", "Local AI Lab", "Local AI Lab"), "languages": LANGS,
                  "version": self.version, "out": ".", "pages": pages, "css": ["assets/site.css"], "js": {"*": []}}
        files[f"{SITE}/site.json"] = json.dumps(config, ensure_ascii=False, indent=1) + "\n"
        return files

    def redirects(self):
        """Old addresses -> new pages, so links people saved keep working (meta refresh, no script)."""
        files = {".nojekyll": ""}
        for md in tracked_markdown():
            old = old_page(md)
            if md in self.md_page:
                pid, lang = self.md_page[md]
                lang = lang or (re.search(r"\.(ru|de|en)\.md$", md) or [None, "en"])[1]
                target = posixpath.relpath(f"{SITE}/{page_file(pid, lang)}", posixpath.dirname(old) or ".")
            elif md == "README.md":
                continue
            else:
                lang, target = "en", f"{REPO_URL}/blob/main/{md}"
            if md == "README.md":
                target, lang = f"{SITE}/index.html", "en"
            files[old] = (f"<!doctype html>\n{AUTHOR}\n<html lang=\"{lang}\">\n<head>\n  <meta charset=\"utf-8\">\n"
                          f"  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
                          f"  <meta http-equiv=\"refresh\" content=\"0; url={html.escape(target)}\">\n"
                          f"  <link rel=\"icon\" href=\"{posixpath.relpath(SITE + '/style/brand/logo-mark.svg', posixpath.dirname(old) or '.')}\" type=\"image/svg+xml\">\n"
                          f"  <link rel=\"canonical\" href=\"{html.escape(target)}\">\n  <meta name=\"robots\" content=\"noindex\">\n"
                          f"  <title>Local AI Lab</title>\n</head>\n<body>\n  <p><a href=\"{html.escape(target)}\">{UI[lang]['moved']}: "
                          f"{html.escape(target)}</a></p>\n</body>\n</html>\n")
        return files

    def built_pages(self):
        names = [page_file(p["id"], lang) for p in PAGES if "href" not in p for lang in LANGS]
        return names + [f"contact.{lang}.html" for lang in LANGS]


def core_dir(argv):
    if "--style" in argv:
        return os.path.abspath(argv[argv.index("--style") + 1])
    return os.path.abspath(os.environ.get("HOMENSAI_STYLE") or os.path.join(ROOT, "..", "homensai-style"))


def write_all(files):
    changed = []
    for name, content in sorted(files.items()):
        path = os.path.join(ROOT, name)
        try:
            with open(path, encoding="utf-8") as f:
                if f.read() == content:
                    continue
        except OSError:
            pass
        os.makedirs(os.path.dirname(path) or ROOT, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        changed.append(name)
    return changed


def check(site, files):
    problems = []
    for name, content in sorted(files.items()):
        try:
            with open(os.path.join(ROOT, name), encoding="utf-8") as f:
                if f.read() != content:
                    problems.append(f"out of date: {name}")
        except OSError:
            problems.append(f"missing: {name}")
    known = set(files)
    for name in os.listdir(os.path.join(ROOT, SITE, "content")):
        if f"{SITE}/content/{name}" not in known:
            problems.append(f"left over: {SITE}/content/{name}")
    try:
        core = read(f"{SITE}/style/VERSION").strip()
    except OSError:
        core = None
        problems.append(f"missing: {SITE}/style/VERSION (run the build with the style core)")
    if core and tuple(int(x) for x in core.split(".")) < MIN_CORE:
        problems.append(f"{SITE}/style is HomenS.AI Style {core}, needs {'.'.join(map(str, MIN_CORE))} or newer")
    for name in site.built_pages():
        try:
            page = read(f"{SITE}/{name}")
        except OSError:
            problems.append(f"missing page: {SITE}/{name} (run the build)")
            continue
        if f'<meta name="homensai-style" content="{core}">' not in page:
            problems.append(f"{SITE}/{name}: not built with the style core in {SITE}/style")
        pid, _, rest = name.partition(".")
        lang = rest.split(".")[0] if rest != "html" else LANGS[0]
        body = files.get(f"{SITE}/content/{'home' if pid == 'index' else pid}.{lang}.body.html")
        if body:
            inner = re.sub(r"^\s*<!--[^>]*Serhii Khomenko[^>]*-->\s*", "", body).strip()
            if inner not in page:
                problems.append(f"{SITE}/{name}: older than its content (run the build)")
    return problems


def main(argv):
    site = Site()
    files = site.sources()
    files.update(site.redirects())
    if "--check" in argv:
        problems = check(site, files)
        for p in problems:
            print(p)
        print(f"{len(files)} files, {len(site.built_pages())} pages: " + ("up to date" if not problems else
              f"{len(problems)} problem(s), run python scripts/build_site.py"))
        return 1 if problems else 0
    core = core_dir(argv)
    builder = os.path.join(core, "tools", "site.py")
    try:
        version = tuple(int(x) for x in read_abs(os.path.join(core, "VERSION")).strip().split("."))
    except (OSError, ValueError):
        version = None
    if not os.path.exists(builder) or not version or version < MIN_CORE:
        raise SystemExit(f"HomenS.AI Style {'.'.join(map(str, MIN_CORE))} or newer is needed in {core} "
                         "(--style <folder> or HOMENSAI_STYLE); download the ZIP of the style repository")
    changed = write_all(files)
    for name in os.listdir(os.path.join(ROOT, SITE, "content")):
        if f"{SITE}/content/{name}" not in files:
            os.remove(os.path.join(ROOT, SITE, "content", name))
            changed.append(f"{SITE}/content/{name} (removed)")
    print(f"{len(files)} files, {len(changed)} changed; building the pages with HomenS.AI Style {'.'.join(map(str, version))}")
    return subprocess.run([sys.executable, builder, "build", os.path.join(ROOT, SITE)]).returncode


def read_abs(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
