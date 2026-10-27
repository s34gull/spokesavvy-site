"""Render a legal page from the app repo's docs/legal/ into this site.

Usage:
  python3 tools/render_policy.py <path to privacy-policy.md> privacy/index.html
  python3 tools/render_policy.py <path to terms-of-use.md> terms/index.html

Handles only the subset the documents use: #/##/### headings, paragraphs,
- and 1. lists, one pipe table, **bold**, *em*, `code`, [text](url), and the
bold header lines at the top. Fails loudly on anything else, on a horizontal
rule (the builder notes must never be published), and on an unfilled
"OWNER:" blank.
"""
import html
import os
import re
import sys

# Each publishable document: its page title, meta description, and the nav
# links shown under it (every legal page links to the other one).
PAGES = {
    "privacy-policy.md": (
        "Privacy Policy",
        "What Spoke Savvy collects, why, where it goes, how long it is kept, and how to delete it.",
        [("/", "Home"), ("/support/", "Support"), ("/terms/", "Terms of Use")],
    ),
    "terms-of-use.md": (
        "Terms of Use",
        "The agreement for using Spoke Savvy: who can use it, what it is and is not, and the rules.",
        [("/", "Home"), ("/support/", "Support"), ("/privacy/", "Privacy Policy")],
    ),
}

src, out = sys.argv[1], sys.argv[2]
name = os.path.basename(src)
if name not in PAGES:
    raise SystemExit(f"unknown document {name}: add it to PAGES")
page_title, description, nav = PAGES[name]
text = open(src, encoding="utf-8").read()
if "OWNER:" in text:
    raise SystemExit("unfilled OWNER: blank: fill it in the source before publishing")
lines = text.split("\n")
BLOCK = re.compile(r"(#{1,3} |- |\d+\. |\|)")


def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![*\w])\*([^*]+)\*(?![*\w])", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', text)
    if re.search(r"[*`]|\]\(", re.sub(r"<[^>]+>", "", text)):
        raise SystemExit(f"unrendered markdown in: {text}")
    return text


def items(i, pattern):
    out_items = []
    while i < len(lines) and re.match(pattern, lines[i]):
        out_items.append(f"<li>{inline(re.sub(pattern, '', lines[i], count=1))}</li>")
        i += 1
    return i, "".join(out_items)


body, i, title = [], 0, None
while i < len(lines):
    line = lines[i]
    if not line.strip():
        i += 1
    elif line.strip() == "---":
        raise SystemExit("horizontal rule found: builder notes must not be in the published policy")
    elif line.startswith("# "):
        title = line[2:].strip()
        body.append(f"<h1>{inline(title)}</h1>")
        i += 1
    elif line.startswith("### "):
        body.append(f"<h3>{inline(line[4:])}</h3>")
        i += 1
    elif line.startswith("## "):
        body.append(f"<h2>{inline(line[3:])}</h2>")
        i += 1
    elif line.startswith("- "):
        i, li = items(i, r"- ")
        body.append(f"<ul>{li}</ul>")
    elif re.match(r"\d+\. ", line):
        i, li = items(i, r"\d+\. ")
        body.append(f"<ol>{li}</ol>")
    elif line.startswith("|"):
        rows = []
        while i < len(lines) and lines[i].startswith("|"):
            rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
            i += 1
        head, sep, data = rows[0], rows[1], rows[2:]
        if not all(set(c) <= set("-:") for c in sep):
            raise SystemExit("table separator row expected")
        t = "<thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
        t += "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in data) + "</tbody>"
        body.append(f'<div class="table"><table>{t}</table></div>')
    else:
        para = []
        while i < len(lines) and lines[i].strip() and not BLOCK.match(lines[i]):
            para.append(lines[i])
            i += 1
        # The header block is several **Label:** lines with no blank between: keep them as lines.
        joiner = "<br>\n" if len(para) > 1 and all(p.startswith("**") for p in para) else " "
        body.append("<p>" + joiner.join(inline(p) for p in para) + "</p>")

if title is None:
    raise SystemExit("no title")

page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{page_title} · Spoke Savvy</title>
  <meta name="description" content="{html.escape(description)}">
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  <main>
    <!-- Rendered by tools/render_policy.py from docs/legal/{name} in s34gull/spoke-savvy. Edit that file, then re-render. -->
{chr(10).join('    ' + b for b in body)}

    <nav>
{chr(10).join(f'      <a href="{href}">{label}</a>' for href, label in nav)}
    </nav>
  </main>
</body>
</html>
"""
open(out, "w", encoding="utf-8").write(page)
print(f"wrote {out}: {len(body)} blocks")
