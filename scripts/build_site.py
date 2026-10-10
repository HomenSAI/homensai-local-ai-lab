#!/usr/bin/env python3
# Local AI Lab - (c) 2026 Serhii Khomenko - https://homensai.com/
"""Builds the documentation site (GitHub Pages) in HomenS.AI Style.

Every Markdown file of the repository becomes an HTML page next to it (docs/INSTALL.ru.md -> docs/INSTALL.ru.html,
the root README.md -> index.html) with the header of the style (logo, menu, language switch, theme button), a table of
contents, the licence line and the author footer; site/contact.<lang>.html are the "Contact" pages with the robot.
The style files are the copy in console/style/ (no second copy, no external addresses, no inline styles or scripts);
.nojekyll makes GitHub Pages serve the pages as they are. The pages also open from the disk (file://).

  python scripts/build_site.py           # write the pages
  python scripts/build_site.py --check   # exit 1 if a page is missing or out of date (CI)

Standard library only.
"""
import html
import os
import posixpath
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_URL = "https://github.com/HomenSAI/homensai-local-ai-lab"
STYLE = "console/style"
STYLE_VERSION = "1.6.0"
SKIP_DIRS = {".git", "bench_results", "secrets", "node_modules", "media", "console", "report"}
LANGS = ("ru", "en", "de")
LANG_NAMES = {"ru": "Русский", "en": "English", "de": "Deutsch"}

T = {
    "ru": {"skip": "Перейти к содержанию", "nav": "Основная навигация", "home": "Главная", "install": "Установка",
           "docs": "Документация", "results": "Результаты", "contact": "Контакт", "toc": "Содержание",
           "lang": "Язык", "more": "Документы", "close": "Закрыть", "edit": "Исходный текст на GitHub",
           "noscript": "Тема, кнопка «Наверх» и ссылки автора работают с JavaScript; текст страницы виден и без него.",
           "license": "Результаты и код можно использовать только в некоммерческих целях со ссылкой на автора",
           "author": "Автор", "lic_results": "Лицензия результатов", "lic_code": "Лицензия кода",
           "third": "Права третьих лиц", "contact_title": "Контакт", "brand_sub": "Local AI Lab"},
    "en": {"skip": "Skip to content", "nav": "Main navigation", "home": "Home", "install": "Installation",
           "docs": "Documentation", "results": "Results", "contact": "Contact", "toc": "Contents",
           "lang": "Language", "more": "Documents", "close": "Close", "edit": "Source text on GitHub",
           "noscript": "The theme, the \"Top\" button and the author links need JavaScript; the page text is shown without it.",
           "license": "Results and code may be used only for noncommercial purposes with credit to the author",
           "author": "Author", "lic_results": "Licence of the results", "lic_code": "Licence of the code",
           "third": "Third-party rights", "contact_title": "Contact", "brand_sub": "Local AI Lab"},
    "de": {"skip": "Zum Inhalt springen", "nav": "Hauptnavigation", "home": "Start", "install": "Installation",
           "docs": "Dokumentation", "results": "Ergebnisse", "contact": "Kontakt", "toc": "Inhalt",
           "lang": "Sprache", "more": "Dokumente", "close": "Schließen", "edit": "Quelltext auf GitHub",
           "noscript": "Design, die Schaltfläche „Nach oben“ und die Autorenlinks brauchen JavaScript; der Text ist auch ohne sichtbar.",
           "license": "Ergebnisse und Code dürfen nur nichtkommerziell und mit Nennung des Autors verwendet werden",
           "author": "Autor", "lic_results": "Lizenz der Ergebnisse", "lic_code": "Lizenz des Codes",
           "third": "Rechte Dritter", "contact_title": "Kontakt", "brand_sub": "Local AI Lab"},
}

# Menu: (key, label per language, base name of the page; the page in the reader's language is chosen when it exists)
DOCS_MENU = [
    ({"ru": "ИИ-оператор", "en": "AI operator", "de": "KI-Operator"}, "docs/AI_OPERATOR"),
    ({"ru": "Методика тестов", "en": "Test methodology", "de": "Testmethodik"}, "docs/METHODOLOGY"),
    ({"ru": "Почему сделано так", "en": "Design decisions", "de": "Designentscheidungen"}, "docs/DESIGN"),
    ({"ru": "Архитектура", "en": "Architecture", "de": "Architektur"}, "docs/ARCHITECTURE"),
    ({"ru": "HTTP API", "en": "HTTP API", "de": "HTTP-API"}, "docs/API"),
    ({"ru": "Формат результатов", "en": "Result format", "de": "Ergebnisformat"}, "docs/RESULTS_FORMAT"),
    ({"ru": "Модели и профили", "en": "Models and profiles", "de": "Modelle und Profile"}, "MODELS"),
    ({"ru": "Задание для ИИ-ассистента", "en": "Prompt for an AI assistant", "de": "Auftrag für einen KI-Assistenten"}, "PROMPT_FOR_AI"),
    ({"ru": "Виртуальная RTX 3080", "en": "Virtual RTX 3080", "de": "Virtuelle RTX 3080"}, "tests/virtual-3080/README"),
    ({"ru": "Тесты (раннеры)", "en": "Test runners", "de": "Testprogramme"}, "benchmarks/README"),
    ({"ru": "Безопасность", "en": "Security", "de": "Sicherheit"}, "SECURITY"),
    ({"ru": "Изменения", "en": "Changelog", "de": "Änderungen"}, "CHANGELOG"),
    ({"ru": "Лицензии", "en": "Licences", "de": "Lizenzen"}, "legal/README"),
]
CONTENTS_HEADINGS = {"содержание", "contents", "table of contents", "inhalt", "inhaltsverzeichnis"}

BRAND_SVG = (
    '<svg class="brand-mark" viewBox="0 0 100 100" aria-hidden="true" focusable="false"><path d="M50.0 13.0 L48.1 13.1 '
    'L46.1 13.2 L44.2 13.5 L42.3 13.8 L42.2 21.0 L40.7 21.5 L39.2 22.0 L37.8 22.6 L36.4 23.3 L31.5 18.0 L29.8 19.0 L28.3 '
    '20.1 L26.7 21.2 L25.2 22.5 L28.8 28.8 L27.7 29.9 L26.7 31.1 L25.7 32.4 L24.8 33.7 L18.0 31.5 L17.0 33.2 L16.2 35.0 '
    'L15.5 36.7 L14.8 38.6 L21.0 42.2 L20.7 43.8 L20.4 45.3 L20.2 46.9 L20.0 48.4 L13.0 50.0 L13.1 51.9 L13.2 53.9 L13.5 '
    '55.8 L13.8 57.7 L21.0 57.8 L21.5 59.3 L22.0 60.8 L22.6 62.2 L23.3 63.6 L18.0 68.5 L19.0 70.2 L20.1 71.7 L21.2 73.3 '
    'L22.5 74.8 L28.8 71.2 L29.9 72.3 L31.1 73.3 L32.4 74.3 L33.7 75.2 L31.5 82.0 L33.2 83.0 L35.0 83.8 L36.7 84.5 L38.6 '
    '85.2 L42.2 79.0 L43.8 79.3 L45.3 79.6 L46.9 79.8 L48.4 80.0 L50.0 87.0 Z" fill="#c9a24a"/><path d="M50 20 A30 30 0 0 '
    '1 50 80" fill="none" stroke="#2bb3c4" stroke-width="5"/><g fill="none" stroke="#2bb3c4" stroke-width="4" '
    'stroke-linecap="round" stroke-linejoin="round"><path d="M50 36 H64 L70 30"/><path d="M50 50 H72"/><path d="M50 64 '
    'H62 L68 70"/></g><g fill="#2bb3c4"><circle cx="71" cy="29" r="4"/><circle cx="74" cy="50" r="4"/><circle cx="69" '
    'cy="71" r="4"/></g><circle cx="50" cy="50" r="9" fill="currentColor"/><circle cx="50" cy="50" r="3.5" '
    'fill="#c9a24a"/></svg>')


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
def sources():
    try:
        done = subprocess.run(["git", "ls-files", "-z", "*.md"], cwd=ROOT, capture_output=True, check=True)
        files = [f for f in done.stdout.decode("utf-8").split("\0") if f]
    except (OSError, subprocess.CalledProcessError):
        files = []
        for top, dirs, names in os.walk(ROOT):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
            files += [os.path.relpath(os.path.join(top, n), ROOT).replace(os.sep, "/") for n in names if n.endswith(".md")]
    return sorted(f for f in files if f.split("/")[0] not in SKIP_DIRS)


def out_path(md):
    return "index.html" if md == "README.md" else md[:-3] + ".html"


def lang_of(md, text):
    m = re.search(r"\.(ru|en|de)\.md$", md)
    if m:
        return m.group(1)
    letters = re.findall(r"[A-Za-zА-Яа-яЁёÄÖÜäöüß]", text)
    cyr = sum(1 for ch in letters if re.match(r"[А-Яа-яЁё]", ch))
    if letters and cyr / len(letters) > 0.3:
        return "ru"
    de = len(re.findall(r"\b(?:und|der|die|das|nicht|mit|für|wird)\b", text))
    en = len(re.findall(r"\b(?:and|the|with|not|for|is|are)\b", text))
    return "de" if de > en else "en"


def base_of(md):
    return re.sub(r"(\.(ru|en|de))?\.md$", "", md)


def rel(target, page):
    return posixpath.relpath(target, posixpath.dirname(page) or ".")


class Site:
    def __init__(self):
        self.files = sources()
        self.texts = {md: open(os.path.join(ROOT, md), encoding="utf-8").read() for md in self.files}
        self.langs = {md: lang_of(md, t) for md, t in self.texts.items()}
        self.alt = {}                                     # base -> {lang: md}
        for md in self.files:
            explicit = re.search(r"\.(ru|en|de)\.md$", md)
            group = self.alt.setdefault(base_of(md), {})
            if explicit or self.langs[md] not in group:
                group[self.langs[md]] = md
        self.version = open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read().strip()

    def page_for(self, base, lang):
        group = self.alt.get(base) or {}
        md = group.get(lang) or group.get("en") or next(iter(group.values()), None)
        return out_path(md) if md else None

    def link(self, href, md):
        if re.match(r"^[a-z][a-z0-9+.-]*:", href, re.I) or href.startswith("#"):
            return href
        path, _, frag = href.partition("#")
        frag = "#" + frag if frag else ""
        page = out_path(md)
        target = posixpath.normpath(posixpath.join(posixpath.dirname(md), path)) if path else md
        if target.startswith(".."):
            return href
        if target in self.texts:
            return rel(out_path(target), page) + frag
        if path.endswith("/") or os.path.isdir(os.path.join(ROOT, target)):
            if target + "/README.md" in self.texts:
                return rel(out_path(target + "/README.md"), page) + frag
            return f"{REPO_URL}/tree/main/{target}"
        if re.search(r"\.(png|jpe?g|svg|gif|webp)$", target, re.I):
            return rel(target, page)
        return f"{REPO_URL}/blob/main/{target}{frag}"

    # ---------------------------------------------------------------- page parts
    def head(self, page, lang, title, description, extra_css=()):
        r = rel(".", page)
        r = "" if r == "." else r + "/"
        s = r + STYLE
        css = "".join(f'\n  <link rel="stylesheet" href="{r}{c}">' for c in extra_css)
        return f"""<!doctype html>
<!-- Local AI Lab · © 2026 Serhii Khomenko · https://homensai.com/ · generated by scripts/build_site.py, do not edit -->
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; base-uri 'none'; form-action 'none'">
  <meta name="referrer" content="no-referrer">
  <meta name="homensai-style" content="{STYLE_VERSION}">
  <title>{html.escape(title)} — Local AI Lab</title>
  <meta name="description" content="{html.escape(description)}">
  <link rel="icon" href="{s}/brand/logo-mark.svg" type="image/svg+xml">
  <meta name="theme-color" content="#edf1f4" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#0f1720" media="(prefers-color-scheme: dark)">
  <link rel="preload" href="{s}/fonts/ibm-plex/IBMPlexSans-Regular.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="{s}/fonts/ibm-plex/IBMPlexSans-SemiBold.woff2" as="font" type="font/woff2" crossorigin>
  <script src="{s}/js/theme-init.js"></script>
  <link rel="stylesheet" href="{s}/dist/homensai-full.css">
  <link rel="stylesheet" href="{r}site/site.css">{css}
</head>"""

    def header(self, page, lang, current_base, alternates):
        t = T[lang]
        home = self.page_for("README", lang)

        def a(target, label, base, cls="nav-link"):
            cur = ' aria-current="page"' if base == current_base else ""
            return f'<a class="{cls}" href="{html.escape(rel(target, page))}"{cur}>{html.escape(label)}</a>'

        docs_bases = {b for _, b in DOCS_MENU}
        docs_links = "".join(a(self.page_for(b, lang), labels[lang], b, cls="") .replace(' class=""', "")
                             for labels, b in DOCS_MENU if self.page_for(b, lang))
        active = " data-active" if current_base in docs_bases else ""
        contact = f"site/contact.{lang}.html"
        langs = ""
        for code in LANGS:
            target = alternates.get(code)
            if not target:
                continue
            cur = ' aria-current="page"' if code == lang else ""
            langs += f'<a href="{html.escape(rel(target, page))}" hreflang="{code}" lang="{code}"{cur}>{LANG_NAMES[code]}</a>'
        lang_menu = (f'<li><details class="nav-group lang-switch"><summary aria-label="{t["lang"]}: {LANG_NAMES[lang]}">'
                     f'{lang.upper()}</summary><div class="nav-menu right">{langs}</div></details></li>') if langs.count("<a") > 1 else ""
        return f"""<body>
  <a class="skip-link" href="#main">{t["skip"]}</a>
  <header class="topbar">
    <a class="brand" href="{html.escape(rel(home, page))}" aria-label="HomenS.AI Local AI Lab">{BRAND_SVG}<span class="brand-word">HomenS<span class="ai">.AI</span> <span class="sub">{t["brand_sub"]}</span></span></a>
    <nav id="nav" aria-label="{t["nav"]}">
      <ul class="nav-main">
        <li>{a(home, t["home"], "README")}</li>
        <li>{a(self.page_for("docs/INSTALL", lang), t["install"], "docs/INSTALL")}</li>
        <li><details class="nav-group"{active}><summary>{t["docs"]}</summary><div class="nav-menu">{docs_links}</div></details></li>
        <li>{a(self.page_for("results-public/RESULTS", lang), t["results"], "results-public/RESULTS")}</li>
        <li><a class="nav-link" href="{REPO_URL}" rel="noopener">GitHub ↗</a></li>
        <li>{a(contact, t["contact"], "site/contact", cls="nav-link nav-contact")}</li>
      </ul>
      <ul class="nav-tools" id="tools">{lang_menu}</ul>
    </nav>
  </header>"""

    def bottom(self, page, lang, current_base, source_md=None):
        t = T[lang]

        def a(target, label, base):
            cur = ' aria-current="page"' if base == current_base else ""
            return f'<a href="{html.escape(rel(target, page))}"{cur}>{html.escape(label)}</a>'

        docs = "".join(f'<a href="{html.escape(rel(self.page_for(b, lang), page))}">{html.escape(labels[lang])}</a>'
                       for labels, b in DOCS_MENU if self.page_for(b, lang))
        source = (f'<p class="page-source"><a href="{REPO_URL}/blob/main/{source_md}" rel="noopener">{t["edit"]}</a></p>'
                  if source_md else "")
        lic_res = rel(self.page_for("legal/LICENSE-RESULTS-CC-BY-NC-4.0", lang), page)
        third = rel(self.page_for("legal/NOTICE-THIRD-PARTY", lang), page)
        return f"""  <nav class="bottomnav" aria-label="{t["nav"]}">
    {a(self.page_for("README", lang), t["home"], "README")}
    {a(self.page_for("docs/INSTALL", lang), t["install"], "docs/INSTALL")}
    <button type="button" class="more-toggle" aria-expanded="false" aria-controls="more-sheet">{t["more"]}</button>
    {a(f"site/contact.{lang}.html", t["contact"], "site/contact")}
  </nav>
  <div class="more-sheet" id="more-sheet" hidden>
    <h2>{t["docs"]}</h2>
    <a href="{html.escape(rel(self.page_for("results-public/RESULTS", lang), page))}">{t["results"]}</a>{docs}
    <a href="{REPO_URL}" rel="noopener">GitHub ↗</a>
  </div>
  <footer class="site-footer">
    {source}
    <p class="license-line">{t["license"]} · {t["author"]}: <a href="https://homensai.com/" rel="noopener author">homensai.com</a> · Local AI Lab <b>v{self.version}</b> · <a href="{REPO_URL}" rel="noopener">GitHub</a> ·
    {t["lic_results"]}: <a href="{html.escape(lic_res)}" rel="license">CC BY-NC 4.0</a> · {t["lic_code"]}: <a href="{REPO_URL}/blob/main/legal/LICENSE-CODE-POLYFORM-NC.txt" rel="license noopener">PolyForm Noncommercial 1.0.0</a> ·
    <a href="{html.escape(third)}">{t["third"]}</a></p>
    <div id="footer"></div>
  </footer>
  <noscript><p class="noscript">{t["noscript"]}</p></noscript>"""

    def scripts(self, page, extra=()):
        r = rel(".", page)
        r = "" if r == "." else r + "/"
        names = [f"{STYLE}/js/brand.js", f"{STYLE}/js/ui.js", f"{STYLE}/js/brand-ui.js", *extra, "site/site.js"]
        return "\n".join(f'  <script src="{r}{n}"></script>' for n in names) + "\n</body>\n</html>\n"

    # ---------------------------------------------------------------- pages
    def doc_page(self, md):
        text, lang = self.texts[md], self.langs[md]
        page, base = out_path(md), base_of(md)
        conv = Markdown(lambda href: self.link(href, md))
        body = conv.render(text)
        h1 = next((h for h in conv.headings if h[0] == 1), None)
        title = h1[2] if h1 else posixpath.basename(base).replace("_", " ")
        first_p = re.search(r"<p>(.*?)</p>", body, re.S)
        description = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", first_p.group(1)))).strip()[:200] if first_p else title
        h2 = [h for h in conv.headings if h[0] == 2]
        toc = ""
        if len(h2) >= 3 and not any(h[2].strip().lower() in CONTENTS_HEADINGS for h in conv.headings):
            items = "".join(f'<li><a href="#{h[1]}">{html.escape(h[2])}</a></li>' for h in h2)
            toc = f'\n    <nav class="card help-toc doc-toc" aria-label="{T[lang]["toc"]}"><h2>{T[lang]["toc"]}</h2><ol>{items}</ol></nav>'
        if h1:                                          # the title stands above the table of contents and the text card
            body = re.sub(r"<h1 id=\"[^\"]*\">.*?</h1>\n?", "", body, count=1, flags=re.S)
            heading = f'<h1 id="{h1[1]}">{h1[3]}</h1>'
        else:
            heading = f"<h1>{html.escape(title)}</h1>"
        alternates = {code: out_path(m) for code, m in (self.alt.get(base) or {}).items()}
        return (self.head(page, lang, title, description) + "\n" + self.header(page, lang, base, alternates) + f"""
  <main id="main" tabindex="-1">
    <p class="eyebrow">Local AI Lab · v{self.version}</p>
    {heading}{toc}
    <article class="card lesson-body doc-body">
{body}
    </article>
  </main>
""" + self.bottom(page, lang, base, md) + "\n" + self.scripts(page))

    def contact_page(self, lang):
        page = f"site/contact.{lang}.html"
        alternates = {code: f"site/contact.{code}.html" for code in LANGS}
        return (self.head(page, lang, T[lang]["contact_title"], T[lang]["contact_title"] + " · HomenS.AI") + "\n"
                + self.header(page, lang, "site/contact", alternates) + """
  <main id="main" tabindex="-1">
    <section id="contact" data-heading="h1"></section>
  </main>
""" + self.bottom(page, lang, "site/contact") + "\n"
                + self.scripts(page, (f"{STYLE}/js/robot.js", f"{STYLE}/js/motion.js", f"{STYLE}/js/logo-word.js", "site/contact.js")))

    def pages(self):
        result = {out_path(md): self.doc_page(md) for md in self.files}
        for lang in LANGS:
            result[f"site/contact.{lang}.html"] = self.contact_page(lang)
        result[".nojekyll"] = ""
        return result


def main(argv):
    check = "--check" in argv
    pages = Site().pages()
    stale = []
    for name, content in sorted(pages.items()):
        path = os.path.join(ROOT, name)
        try:
            old = open(path, encoding="utf-8").read()
        except OSError:
            old = None
        if old == content:
            continue
        stale.append(name)
        if not check:
            os.makedirs(os.path.dirname(path) or ROOT, exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
    if check:
        for name in stale:
            print("out of date:", name)
        print(f"{len(pages)} pages, {len(stale)} out of date" + (": run python scripts/build_site.py" if stale else ""))
        return 1 if stale else 0
    print(f"{len(pages)} pages, {len(stale)} written")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
