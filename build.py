#!/usr/bin/env python3
"""Build the site.

    python build.py            # content/*.yml + templates/index.html -> dist/
    python build.py --serve    # ...then serve dist/ at http://localhost:8000

Everything the page says lives in content/*.yml. This script only turns that
data into one HTML file and copies static/ next to it.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

try:
    import markdown as md_lib
    import yaml
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from markupsafe import Markup, escape
except ImportError as exc:  # pragma: no cover
    sys.exit(f"Missing dependency: {exc.name}\nRun: pip install -r requirements.txt")

ROOT = Path(__file__).parent.resolve()
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

MISSING: list[str] = []


# --------------------------------------------------------------------------
# content
# --------------------------------------------------------------------------
def load(name: str, default):
    """Read content/<name>.yml. Missing or empty is not an error."""
    path = CONTENT / f"{name}.yml"
    if not path.exists():
        return default
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f" (line {mark.line + 1})" if mark else ""
        sys.exit(
            f"! content/{name}.yml has a YAML error{where}: {getattr(exc, 'problem', exc)}\n"
            "  Tip: a value containing ': ' must be quoted, or written as a block with '>'."
        )
    return default if data is None else data


def check_asset(path: str | None, where: str) -> None:
    """Warn when YAML points at a file that is not in static/."""
    path = (path or "").strip()
    if not path or "://" in path:
        return
    if not (STATIC / path).exists():
        MISSING.append(f"{where}: static/{path}")


def year_key(text: str) -> int:
    """'2024' -> 2024, '2023-24' -> 2023, 'Present' -> 9999, '' -> -1."""
    if re.search(r"present|current|now|ongoing", text, re.I):
        return 9999
    match = re.search(r"\d{4}", text)
    return int(match.group()) if match else -1


def video_embed(url: str) -> str | None:
    """YouTube / Vimeo page URL -> iframe-embeddable URL. Anything else -> None."""
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host in {"youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            vid = parse_qs(parsed.query).get("v", [""])[0]
            return f"https://www.youtube-nocookie.com/embed/{vid}" if vid else None
        if parsed.path.startswith(("/embed/", "/shorts/")):
            return f"https://www.youtube-nocookie.com/embed/{parsed.path.split('/')[2]}"
    if host == "youtu.be" and len(parsed.path) > 1:
        return f"https://www.youtube-nocookie.com/embed/{parsed.path.lstrip('/')}"
    if host in {"vimeo.com", "player.vimeo.com"}:
        match = re.search(r"(\d+)", parsed.path)
        return f"https://player.vimeo.com/video/{match.group(1)}" if match else None
    return None


def group_by_year(items: list[dict]) -> list[tuple[str, list[dict]]]:
    """Publications grouped by `year`, newest first, file order inside a year."""
    groups: dict[str, list[dict]] = {}
    for item in items:
        groups.setdefault(str(item.get("year") or "").strip(), []).append(item)
    years = sorted(groups, key=year_key, reverse=True)
    return [(year, groups[year]) for year in years]


# --------------------------------------------------------------------------
# template filters
# --------------------------------------------------------------------------
def markdown(text: str | None) -> Markup:
    if not text:
        return Markup("")
    return Markup(md_lib.markdown(str(text).strip(), extensions=["smarty"]))


def inline(text: str | None) -> Markup:
    """Markdown for one-liners, without the wrapping <p>."""
    html = str(markdown(text))
    if html.startswith("<p>") and html.endswith("</p>") and html.count("<p>") == 1:
        html = html[3:-4]
    return Markup(html)


def make_authors_filter(name: str):
    """Author list: `**x**` becomes bold, and your own name is bolded for you.

    Deliberately not full Markdown, because author lists are full of `*`
    (equal-contribution marks) that Markdown would read as italics.
    """
    def authors(text: str | None) -> Markup:
        html = str(escape(str(text or "").strip()))
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        if name and "<strong>" not in html:
            html = html.replace(str(escape(name)), f"<strong>{escape(name)}</strong>")
        return Markup(html)
    return authors


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------
def gather() -> dict:
    site = load("site", {}) or {}
    if not site.get("name"):
        print("! content/site.yml has no `name` - the page will look empty")

    experience = load("experience", {}) or {}
    education = experience.get("education") or []
    work = experience.get("work") or []
    projects = [p for p in (load("projects", []) or []) if p.get("featured", True)]
    publications = load("publications", []) or []
    news = site.get("news") or []
    awards = site.get("awards") or []
    certificates = site.get("certificates") or []

    check_asset(site.get("photo"), "site.photo")
    check_asset(site.get("cv"), "site.cv")
    # Newest first by `year`; entries with the same year keep file order.
    projects.sort(key=lambda p: year_key(str(p.get("year") or "")), reverse=True)

    for project in projects:
        label = f"project '{project.get('title', '?')}'"
        check_asset(project.get("image"), f"{label} image")

        # Gallery: a list of "img/x.png" strings or {src, caption} dicts.
        images = []
        for item in project.get("images") or []:
            item = {"src": item} if isinstance(item, str) else dict(item)
            item["src"] = (item.get("src") or "").strip()
            if item["src"]:
                check_asset(item["src"], f"{label} image")
                images.append(item)
        project["images"] = images

        # Videos: `videos:` list of {src, poster, caption}, or the shorthand
        # `video:` + `poster:` for a single clip. src is a file under static/
        # or a YouTube/Vimeo URL.
        raw = list(project.get("videos") or [])
        if project.get("video"):
            raw.insert(0, {"src": project["video"], "poster": project.get("poster", "")})
        videos = []
        for item in raw:
            item = {"src": item} if isinstance(item, str) else dict(item)
            src = (item.get("src") or "").strip()
            if not src:
                continue
            item["src"] = src
            item["embed"] = video_embed(src) if "://" in src else None
            if "://" in src and not item["embed"]:
                print(f"  ! {label}: unrecognised video URL '{src}' (only YouTube/Vimeo embed), ignoring")
                continue
            if not item["embed"]:
                check_asset(src, f"{label} video")
            check_asset(item.get("poster"), f"{label} poster")
            videos.append(item)
        project["videos"] = videos

    # Only sections with content get a nav link, so there is never a dead one.
    nav = [
        {"id": key, "label": label}
        for key, label, has_content in (
            ("about", "About", site.get("about")),
            ("news", "News", news),
            ("education", "Education", education),
            ("experience", "Experience", work),
            ("projects", "Projects", projects),
            ("publications", "Publications", publications),
            ("certificates", "Certificates", certificates),
            ("awards", "Awards", awards),
        )
        if has_content
    ]

    return {
        "site": site,
        "nav": nav,
        "education": education,
        "work": work,
        "projects": projects,
        "publications": group_by_year(publications),
        "news": news,
        "awards": awards,
        "certificates": certificates,
    }


def build() -> None:
    data = gather()

    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["markdown"] = markdown
    env.filters["inline"] = inline
    env.filters["authors"] = make_authors_filter(data["site"].get("name", ""))

    # A browser tab that is playing a demo clip from dist/ keeps that file
    # locked on Windows. Don't let one locked file abort the whole build.
    if DIST.exists():
        shutil.rmtree(DIST, ignore_errors=True)
    DIST.mkdir(parents=True, exist_ok=True)

    # Short hash of the stylesheet, appended as ?v=... so browsers never keep a
    # stale copy after a deploy.
    import hashlib
    css_file = STATIC / "css" / "style.css"
    data["css_version"] = hashlib.md5(css_file.read_bytes()).hexdigest()[:8] if css_file.exists() else "1"

    html = env.get_template("index.html").render(**data)
    (DIST / "index.html").write_text(html, encoding="utf-8")

    def copy_or_warn(src, dst):
        try:
            shutil.copy2(src, dst)
        except PermissionError:
            print(f"  ! {Path(dst).relative_to(ROOT)} is in use (open in a browser?), kept the old copy")

    if STATIC.exists():
        shutil.copytree(STATIC, DIST / "static", dirs_exist_ok=True, copy_function=copy_or_warn)

    # Tells GitHub Pages not to run the output through Jekyll.
    (DIST / ".nojekyll").write_text("", encoding="utf-8")

    n_pubs = sum(len(items) for _, items in data["publications"])
    print(f"Built dist/  ({len(data['projects'])} projects, {n_pubs} publications)")
    for item in MISSING:
        print(f"  ! missing file - {item}")


def serve(port: int = 8000) -> None:
    import functools
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(DIST))
    print(f"Serving dist/ at http://localhost:{port}  (Ctrl+C to stop)")
    try:
        ThreadingHTTPServer(("", port), handler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true", help="serve dist/ after building")
    # The desktop app's preview picks a free port and passes it as $PORT.
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    args = parser.parse_args()

    build()
    if args.serve:
        serve(args.port)
