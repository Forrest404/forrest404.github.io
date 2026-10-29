#!/usr/bin/env python3
"""Turn a plain text draft into a published note.

draft.txt looks like this:

    Title of the note
    One line description (shows in the feed and link previews)

    First paragraph. Blank lines start a new paragraph.

    Second paragraph. You can use <code>, <a href="..."> etc.

Lines starting with # are ignored. Run ./new-note.py. It writes notes/NNN-slug.html, adds the note to
notes/index.html, index.html, feed.xml and sitemap.xml, then deletes the draft.
Add --push to also commit and push.
"""
import html
import re
import subprocess
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = "https://forrest404.github.io"

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{desc_a}">
<meta property="og:site_name" content="Forrest404">
<meta property="og:type" content="article">
<meta property="og:title" content="{title_a}">
<meta property="og:description" content="{desc_a}">
<meta property="og:url" content="{url}">
<title>{title_h} - Forrest404</title>
<link rel="stylesheet" href="../style.css">
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="Forrest404 notes" href="../feed.xml">
</head>
<body class="note">
<a class="skip" href="#main">skip to content</a>
<div id="wrap">

<div id="banner">
<a class="name" href="../index.html">Forrest<span>404</span></a>
</div>

<ul id="tabs">
<li><a href="../index.html">home</a></li>
<li class="here"><a href="index.html">notes</a></li>
<li><a href="../projects.html">projects</a></li>
<li><a href="../working-on.html">working on</a></li>
<li><a href="../contact.html">contact</a></li>
<li><a href="../links.html">links</a></li>
</ul>

<div id="cols">

<div id="main">
<h1>{title_h}</h1>
<p class="date">{date}</p>

{body}

<p>Back to the <a href="index.html">notes</a>.</p>
</div>

</div>

</div>
</body>
</html>
"""


def edit(path, old, new, count=1):
    p = ROOT / path
    s = p.read_text()
    if old not in s:
        sys.exit(f"Could not find {old!r} in {path}; nothing was published.")
    p.write_text(s.replace(old, new, count))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    push = "--push" in sys.argv
    draft = ROOT / (args[0] if args else "draft.txt")
    if not draft.exists():
        sys.exit(f"No {draft.name}. Write one first (see the top of this script).")

    text = "\n".join(l for l in draft.read_text().split("\n") if not l.startswith("#"))
    lines = text.strip().split("\n")
    if len(lines) < 4 or lines[2].strip():
        sys.exit("Draft needs: title, description, a blank line, then the note.")
    title, desc = lines[0].strip(), lines[1].strip()
    paras = [p.strip() for p in "\n".join(lines[3:]).split("\n\n") if p.strip()]
    body = "\n\n".join(f"<p>{p}</p>" for p in paras)

    now = datetime.now(timezone.utc)
    date = f"{now.day} {now:%b}"
    iso = f"{now:%Y-%m-%d}"
    rfc = format_datetime(now.replace(microsecond=0))

    nums = [int(m.group(1)) for f in (ROOT / "notes").glob("*.html")
            if (m := re.match(r"(\d+)-", f.name))]
    slug = "-".join(re.sub(r"[^a-z0-9 ]", "", title.lower()).split()[:4])
    name = f"{max(nums, default=0) + 1:03d}-{slug}.html"
    url = f"{SITE}/notes/{name}"

    (ROOT / "notes" / name).write_text(PAGE.format(
        title_h=html.escape(title), title_a=html.escape(title, quote=True),
        desc_a=html.escape(desc, quote=True), url=url, date=date, body=body))

    top = '<ul class="notes">\n'
    edit("notes/index.html", top,
         f'{top}<li><span class="date">{date}</span> <a href="{name}">{html.escape(title)}</a></li>\n')
    edit("index.html", top,
         f'{top}<li><span class="date">{date}</span> <a href="notes/{name}">{html.escape(title)}</a></li>\n')

    edit("feed.xml", "<item>\n", f"""<item>
<title>{html.escape(title, quote=False)}</title>
<link>{url}</link>
<guid>{url}</guid>
<pubDate>{rfc}</pubDate>
<description>{html.escape(desc, quote=False)}</description>
</item>

<item>
""")
    feed = (ROOT / "feed.xml").read_text()
    (ROOT / "feed.xml").write_text(re.sub(
        r"<lastBuildDate>.*?</lastBuildDate>", f"<lastBuildDate>{rfc}</lastBuildDate>", feed))

    edit("sitemap.xml", f"<loc>{SITE}/notes/{sorted(nums)[-1]:03d}",
         f"<loc>{url}</loc><lastmod>{iso}</lastmod></url>\n<url><loc>{SITE}/notes/{sorted(nums)[-1]:03d}")
    for page in (f"{SITE}/", f"{SITE}/notes/"):
        sitemap = (ROOT / "sitemap.xml").read_text()
        (ROOT / "sitemap.xml").write_text(re.sub(
            rf"(<loc>{re.escape(page)}</loc><lastmod>).*?(</lastmod>)", rf"\g<1>{iso}\g<2>", sitemap))

    draft.unlink()
    print(f"Created notes/{name} and added it to the index, home page, feed and sitemap.")

    if push:
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-m", f"Add note: {title}"], cwd=ROOT, check=True)
        subprocess.run(["git", "push"], cwd=ROOT, check=True)
    else:
        print("Check it, then publish with:  git add -A && git commit -m 'Add note' && git push")


main()
