# Local AI Lab - (c) 2026 Serhii Khomenko - https://homensai.com/
"""Documentation site: the Markdown converter keeps the text, anchors and links of the repository files, and the
committed pages are up to date."""
import subprocess
import sys
import unittest

from helpers import ROOT
import build_site


def render(text, link=lambda href: href):
    md = build_site.Markdown(link)
    return md.render(text), md


class MarkdownTest(unittest.TestCase):
    def test_heading_anchors_match_github(self):
        out, md = render("## 4. Установка по шагам\n\n## 10. Linux / macOS notes\n\n## Twice\n\n## Twice\n")
        ids = [h[1] for h in md.headings]
        self.assertEqual(ids, ["4-установка-по-шагам", "10-linux--macos-notes", "twice", "twice-1"])

    def test_raw_html_and_placeholders_are_text(self):
        out, _ = render("Use <MODEL_DIR> and `<name>` & <https://homensai.com>.")
        self.assertIn("&lt;MODEL_DIR&gt;", out)
        self.assertIn("<code>&lt;name&gt;</code>", out)
        self.assertIn('<a href="https://homensai.com">https://homensai.com</a>', out)
        self.assertNotIn("<MODEL_DIR>", out)

    def test_table_with_code_and_escaped_pipe(self):
        out, _ = render("| a | b |\n|---|--:|\n| `x \\| y` | **1** |\n")
        self.assertIn('<div class="table-wrap"><table>', out)
        self.assertIn("<code>x | y</code>", out)
        self.assertIn('<td class="n"><strong>1</strong></td>', out)

    def test_list_item_keeps_code_block_and_table(self):
        text = "1. **Find files.** Each profile:\n   ```\n   grep -o x | sort\n   ```\n   | P | C |\n   |---|---|\n   | q | 8K |\n\n2. Next\n"
        out, _ = render(text)
        self.assertIn("<ol>", out)
        self.assertIn("<pre><code>grep -o x | sort</code></pre>", out)
        self.assertIn("<td>8K</td>", out)
        self.assertEqual(out.count("<li>"), 2)

    def test_snake_case_is_not_emphasis(self):
        out, _ = render("Set AI_CONSOLE_PASSWORD and *this* and **that**.")
        self.assertIn("AI_CONSOLE_PASSWORD", out)
        self.assertIn("<em>this</em>", out)
        self.assertIn("<strong>that</strong>", out)

    def test_links_go_to_pages_of_the_same_language_and_files_to_github(self):
        site = build_site.Site()
        self.assertEqual(site.link("INSTALL.ru.md#2-требования", "docs/AI_OPERATOR.ru.md", "ru"), "install.ru.html#2-требования")
        self.assertEqual(site.link("../README.md", "docs/INSTALL.en.md", "en"), "index.html")
        self.assertEqual(site.link("../README.de.md", "docs/INSTALL.de.md", "de"), "index.de.html")
        self.assertEqual(site.link("legal/", "README.ru.md", "ru"), "licences.ru.html")
        self.assertEqual(site.link("LICENSE", "README.md", "en"), build_site.REPO_URL + "/blob/main/LICENSE")
        self.assertEqual(site.link("https://homensai.com", "README.md", "en"), "https://homensai.com")


class SiteTest(unittest.TestCase):
    def test_site_is_up_to_date(self):
        done = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_site.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_every_page_in_every_language_and_no_inline_code(self):
        site = build_site.Site()
        files = site.sources()
        for page in build_site.PAGES:
            if "href" in page:
                continue
            for lang in build_site.LANGS:
                body = files[f"site/content/{page['id']}.{lang}.body.html"]
                self.assertRegex(body, r"^<!--[^>]*Serhii Khomenko[^>]*-->\s*<h1", page["id"])
                self.assertNotRegex(body, r' style="|<script|\son[a-z]+="|@homensai\.com', page["id"])

    def test_old_addresses_redirect(self):
        files = build_site.Site().redirects()
        self.assertIn("site/index.html", files["index.html"])
        self.assertIn("../site/design.ru.html", files["docs/DESIGN.ru.html"])
        self.assertIn(build_site.REPO_URL + "/blob/main/CHANGELOG.md", files["CHANGELOG.html"])


if __name__ == "__main__":
    unittest.main()
