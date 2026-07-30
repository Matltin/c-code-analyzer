"""Build the static documentation landing page used by GitHub Pages."""

from __future__ import annotations

import argparse
import html
import shutil
from pathlib import Path


STYLE = """
:root { color-scheme: light dark; font-family: system-ui, sans-serif; }
body { max-width: 880px; margin: 0 auto; padding: 2rem; line-height: 1.6; }
h1, h2 { line-height: 1.2; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; }
.card { border: 1px solid #8886; border-radius: .75rem; padding: 1rem; }
code, pre { font-family: ui-monospace, monospace; }
pre { overflow: auto; border: 1px solid #8886; border-radius: .5rem; padding: 1rem; }
a { color: #2878d0; }
""".strip()


def build_site(output: Path, coverage: Path, readme: Path) -> None:
    """Create the landing page and copy generated reports into *output*."""

    if not coverage.joinpath("index.html").is_file():
        raise FileNotFoundError(f"coverage report not found: {coverage / 'index.html'}")
    if not readme.is_file():
        raise FileNotFoundError(f"README not found: {readme}")

    output.mkdir(parents=True, exist_ok=True)
    coverage_target = output / "coverage"
    if coverage_target.exists():
        shutil.rmtree(coverage_target)
    shutil.copytree(coverage, coverage_target)

    readme_text = html.escape(readme.read_text(encoding="utf-8"))
    (output / "readme.html").write_text(
        "<!doctype html><html lang='fa' dir='rtl'><head>"
        "<meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
        f"<title>README</title><style>{STYLE}</style></head><body>"
        "<p><a href='index.html'>بازگشت به صفحهٔ اصلی</a></p>"
        f"<pre dir='auto'>{readme_text}</pre></body></html>\n",
        encoding="utf-8",
    )

    (output / "index.html").write_text(
        "<!doctype html><html lang='fa' dir='rtl'><head>"
        "<meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
        f"<title>c-code-analyzer</title><style>{STYLE}</style></head><body>"
        "<h1>c-code-analyzer</h1>"
        "<p>خروجی‌های قابل‌مرور پروژهٔ آموزشی تحلیل کد C.</p>"
        "<div class='cards'>"
        "<section class='card'><h2>نمونهٔ Highlight</h2>"
        "<p>خروجی HTML واقعی CLI برای فایل نمونه.</p>"
        "<a href='highlight.html'>مشاهدهٔ Highlight</a></section>"
        "<section class='card'><h2>گزارش Coverage</h2>"
        "<p>گزارش خط و Branch تولیدشده با pytest-cov.</p>"
        "<a href='coverage/index.html'>مشاهدهٔ Coverage</a></section>"
        "<section class='card'><h2>راهنمای پروژه</h2>"
        "<p>نصب، CLI، تست‌ها و لینک مستندات.</p>"
        "<a href='readme.html'>مشاهدهٔ README</a></section>"
        "</div><h2>اجرای سریع</h2>"
        "<pre dir='ltr'>make setup\nmake test\nmake coverage\nmake site</pre>"
        "</body></html>\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("site"))
    parser.add_argument("--coverage", type=Path, default=Path("htmlcov"))
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_site(args.output, args.coverage, args.readme)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
