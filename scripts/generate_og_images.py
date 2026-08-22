#!/usr/bin/env python3
"""Generate branded 1200x630 OG images from Jekyll post front matter.

Reads `_posts/*.md`, uses title/tags/date/og_slug, writes:
- assets/og/<slug>.svg
- assets/og/<slug>.png when Playwright is available

The PNG is the preferred `og:image` target because social platforms are
less useless when fed PNG/JPEG instead of SVG.
"""
from __future__ import annotations

import html
import re
import subprocess
import textwrap
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "_posts"
OUT = ROOT / "assets" / "og"
WIDTH = 1200
HEIGHT = 630
BRIDAL_HEATH = "#FFF8F1"
HEAVY_METAL = "#1D1E1C"
BLAZE_ORANGE = "#FA5D00"


def parse_front_matter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    _, front, _body = text.split("---", 2)
    data: dict[str, Any] = {}
    current_key = None
    for raw in front.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("  - ") and current_key:
            data.setdefault(current_key, [])
            current_value = data[current_key]
            if not isinstance(current_value, list):
                current_value = []
                data[current_key] = current_value
            current_value.append(line[4:].strip().strip('"'))
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_key = key
            if value == "":
                data[key] = []
            else:
                data[key] = value.strip('"')
    return data


def slug_from_post(path: Path, data: dict[str, Any]) -> str:
    explicit = data.get("og_slug")
    if isinstance(explicit, str) and explicit:
        return explicit
    name = path.stem
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name)


def wrap_title(title: str) -> list[str]:
    # Character-based wrapping is deterministic and works well for the 1200px card.
    lines = textwrap.wrap(title, width=34, break_long_words=False, break_on_hyphens=False)
    if len(lines) <= 4:
        return lines
    kept = lines[:4]
    kept[-1] = kept[-1].rstrip(" .") + "…"
    return kept


def svg_for_post(title: str, tags: list[str]) -> str:
    title_lines = wrap_title(title)
    title_font_size = 52 if len(title_lines) <= 3 else 46
    title_line_height = int(title_font_size * 1.18)
    title_y = 172
    line_svg = []
    for i, line in enumerate(title_lines):
        line_svg.append(
            f'<text x="84" y="{title_y + i * title_line_height}" class="title">{html.escape(line)}</text>'
        )

    chip_svg = []
    x = 84
    y = 510
    for tag in tags[:5]:
        label = str(tag)
        chip_width = min(210, 42 + len(label) * 13)
        if x + chip_width > 1116:
            break
        chip_svg.append(
            f'<g class="chip"><rect x="{x}" y="{y}" width="{chip_width}" height="42" rx="21" />'
            f'<text x="{x + 22}" y="{y + 27}">{html.escape(label)}</text></g>'
        )
        x += chip_width + 14

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{html.escape(title)}">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&amp;display=swap');
      .label {{ font: 700 30px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; letter-spacing: 0.16em; fill: {BLAZE_ORANGE}; }}
      .title {{ font: 700 {title_font_size}px "Lora", Georgia, serif; fill: {BRIDAL_HEATH}; letter-spacing: -0.025em; }}
      .url {{ font: 600 28px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: rgba(255,248,241,0.72); }}
      .chip rect {{ fill: rgba(250,93,0,0.14); stroke: rgba(250,93,0,0.72); stroke-width: 2; }}
      .chip text {{ font: 700 21px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: {BRIDAL_HEATH}; }}
    </style>
    <radialGradient id="glow" cx="17%" cy="7%" r="80%">
      <stop offset="0%" stop-color="{BLAZE_ORANGE}" stop-opacity="0.34" />
      <stop offset="42%" stop-color="{BLAZE_ORANGE}" stop-opacity="0.08" />
      <stop offset="100%" stop-color="{HEAVY_METAL}" stop-opacity="0" />
    </radialGradient>
  </defs>
  <rect width="{WIDTH}" height="{HEIGHT}" fill="{HEAVY_METAL}" />
  <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#glow)" />
  <circle cx="1064" cy="104" r="156" fill="none" stroke="{BLAZE_ORANGE}" stroke-opacity="0.35" stroke-width="2" />
  <circle cx="1104" cy="496" r="96" fill="{BLAZE_ORANGE}" fill-opacity="0.10" />
  <text x="84" y="92" class="label">MRDTECH BLOG</text>
  {''.join(line_svg)}
  {''.join(chip_svg)}
  <text x="84" y="588" class="url">blog.mrdtech.me</text>
</svg>
'''


def svg_for_site() -> str:
    title = "Infrastructure notes without the ceremony."
    title_lines = textwrap.wrap(title, width=28, break_long_words=False, break_on_hyphens=False)
    title_font_size = 58
    title_line_height = int(title_font_size * 1.14)
    title_y = 202
    line_svg = []
    for i, line in enumerate(title_lines):
        line_svg.append(
            f'<text x="84" y="{title_y + i * title_line_height}" class="title">{html.escape(line)}</text>'
        )
    chips = ["Endpoint Management", "Automation", "Security"]
    chip_svg = []
    x = 84
    y = 500
    for chip in chips:
        chip_width = min(290, 42 + len(chip) * 13)
        chip_svg.append(
            f'<g class="chip"><rect x="{x}" y="{y}" width="{chip_width}" height="42" rx="21" />'
            f'<text x="{x + 22}" y="{y + 27}">{html.escape(chip)}</text></g>'
        )
        x += chip_width + 14

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="MRDTech Blog">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&amp;display=swap');
      .label {{ font: 700 30px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; letter-spacing: 0.16em; fill: {BLAZE_ORANGE}; }}
      .title {{ font: 700 {title_font_size}px "Lora", Georgia, serif; fill: {BRIDAL_HEATH}; letter-spacing: -0.025em; }}
      .url {{ font: 600 28px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: rgba(255,248,241,0.72); }}
      .chip rect {{ fill: rgba(250,93,0,0.14); stroke: rgba(250,93,0,0.72); stroke-width: 2; }}
      .chip text {{ font: 700 21px system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: {BRIDAL_HEATH}; }}
    </style>
    <radialGradient id="glow" cx="17%" cy="7%" r="80%">
      <stop offset="0%" stop-color="{BLAZE_ORANGE}" stop-opacity="0.34" />
      <stop offset="42%" stop-color="{BLAZE_ORANGE}" stop-opacity="0.08" />
      <stop offset="100%" stop-color="{HEAVY_METAL}" stop-opacity="0" />
    </radialGradient>
  </defs>
  <rect width="{WIDTH}" height="{HEIGHT}" fill="{HEAVY_METAL}" />
  <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#glow)" />
  <circle cx="1064" cy="104" r="156" fill="none" stroke="{BLAZE_ORANGE}" stroke-opacity="0.35" stroke-width="2" />
  <circle cx="1104" cy="496" r="96" fill="{BLAZE_ORANGE}" fill-opacity="0.10" />
  <text x="84" y="92" class="label">MRDTECH BLOG</text>
  {''.join(line_svg)}
  <text x="84" y="416" class="url">Infrastructure. Endpoints. Automation. Security.</text>
  {''.join(chip_svg)}
  <text x="84" y="588" class="url">blog.mrdtech.me</text>
</svg>
'''


def write_png(svg_path: Path, png_path: Path) -> bool:
    script = f"""
from playwright.sync_api import sync_playwright
from pathlib import Path
svg = Path({str(svg_path)!r}).resolve()
png = Path({str(png_path)!r}).resolve()
html = '''<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;width:{WIDTH}px;height:{HEIGHT}px;overflow:hidden;background:#1D1E1C;}}</style></head><body>''' + svg.read_text(encoding='utf-8') + '''</body></html>'''
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={{'width': {WIDTH}, 'height': {HEIGHT}}}, device_scale_factor=1)
    page.set_content(html, wait_until='domcontentloaded')
    try:
        page.wait_for_load_state('networkidle', timeout=10000)
    except Exception:
        pass
    page.screenshot(path=str(png), full_page=False, timeout=120000)
    browser.close()
"""
    try:
        subprocess.run(["/usr/bin/python3", "-c", script], check=True)
        return True
    except Exception as exc:
        print(f"PNG generation skipped for {svg_path.name}: {exc}")
        return False


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    site_svg = OUT / "mrdtech-blog-home.svg"
    site_png = OUT / "mrdtech-blog-home.png"
    site_svg.write_text(svg_for_site(), encoding="utf-8")
    site_png_ok = write_png(site_svg, site_png)
    print(f"generated {site_svg.relative_to(ROOT)}" + (f" and {site_png.relative_to(ROOT)}" if site_png_ok else ""))

    for post in sorted(POSTS.glob("*.md")):
        data = parse_front_matter(post)
        title = str(data.get("title") or post.stem)
        raw_tags = data.get("tags")
        tags = raw_tags if isinstance(raw_tags, list) else []
        slug = slug_from_post(post, data)
        svg_path = OUT / f"{slug}.svg"
        png_path = OUT / f"{slug}.png"
        svg_path.write_text(svg_for_post(title, [str(t) for t in tags]), encoding="utf-8")
        png_ok = write_png(svg_path, png_path)
        print(f"generated {svg_path.relative_to(ROOT)}" + (f" and {png_path.relative_to(ROOT)}" if png_ok else ""))


if __name__ == "__main__":
    main()
