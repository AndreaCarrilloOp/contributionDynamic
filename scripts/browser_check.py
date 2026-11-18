"""Check SVG animation and responsive embedding using real browser engines."""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

from contribution_dynamic.publish import build_assets

from benchmark import calendars


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", choices=("chromium", "firefox", "webkit"), required=True)
    parser.add_argument("--output", type=Path, default=Path("visual-report"))
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    assets = []
    for name in ("sparse", "demo"):
        assets.extend(build_assets(calendars()[name], output / name))
    with sync_playwright() as pw:
        browser = getattr(pw, args.browser).launch()
        page = browser.new_page(viewport={"width": 900, "height": 300})
        for path in assets:
            page.goto(path.as_uri())
            svg = page.locator("svg").first
            assert svg.count() == 1, path
            svg.evaluate("(el) => { el.pauseAnimations(); el.setCurrentTime(0); }")
            first = svg.screenshot(animations="allow")
            svg.evaluate("(el) => el.setCurrentTime(1.1)")
            second = svg.screenshot(animations="allow")
            assert first != second, f"No visual change: {path}"
            stem = f"{path.parent.name}-{path.stem}"
            (output / f"{stem}-frame.png").write_bytes(second)
            # A separate image document mirrors the README's external SVG embedding.
            html = path.with_suffix(".html")
            html.write_text(
                '<html><body style="margin:0"><img style="width:100%;height:auto" '
                f'src="{path.name}"></body></html>', encoding="utf-8",
            )
            page.set_viewport_size({"width": 390, "height": 300})
            page.goto(html.as_uri())
            image = page.locator("img")
            image.wait_for()
            assert image.evaluate("(el) => el.complete && el.naturalWidth > 0"), path
            assert image.bounding_box()["width"] <= 390, path
            page.set_viewport_size({"width": 900, "height": 300})
            print(f"{args.browser}: {stem} OK")
        browser.close()


if __name__ == "__main__":
    main()
