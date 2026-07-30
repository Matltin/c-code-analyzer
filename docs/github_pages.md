# GitHub Pages

## وضعیت

ساخت Site محلی قابل‌آزمایش است. انتشار واقعی GitHub Pages تا Push به یک
Repository و موفقیت Workflow با وضعیت `[?]` باقی می‌ماند؛ بنابراین هنوز URL
عمومی ادعا نمی‌شود.

## محتوای Site

دستور زیر Site ایستا را در پوشهٔ `site/` می‌سازد:

```bash
make site
```

خروجی شامل این موارد است:

- `site/index.html`: صفحهٔ اصلی با لینک‌های داخلی
- `site/highlight.html`: نمونهٔ واقعی Syntax Highlight تولیدشده توسط CLI
- `site/coverage/index.html`: گزارش HTML Coverage
- `site/readme.html`: نسخهٔ امن و Escapeشدهٔ README

برای مشاهدهٔ محلی:

```bash
make site-serve
```

سپس `http://localhost:8000` را باز کن. برای توقف Server کلید `Ctrl+C` را بزن.
پوشهٔ `site/` تولیدشده است و داخل Git یا Archive تحویل قرار نمی‌گیرد.

## انتشار در GitHub

فایل `.github/workflows/pages.yml` با Push روی Branch `main` یا اجرای دستی Site
را می‌سازد و از سازوکار رسمی GitHub Pages Artifact استفاده می‌کند.

در Repository به مسیر **Settings → Pages** برو و Source را روی **GitHub
Actions** قرار بده. سپس Workflow به نام **Pages** را از Tab مربوط به Actions
اجرا کن یا یک Commit را روی `main` Push کن.

Job مربوط به Build فقط `contents: read` دارد. Job انتشار فقط دسترسی‌های
`pages: write` و `id-token: write` را دریافت می‌کند. هیچ Secret سفارشی لازم
نیست و اجرای هم‌زمان قدیمی با `concurrency` لغو می‌شود.

## Rollback

برای حذف انتشار، فایل `.github/workflows/pages.yml` و Targetهای `site` از
`Makefile` را حذف کن. اگر Pages قبلاً فعال شده، در Settings آن را Disable کن.
