# GitHub Actions CI/CD (B3)

## وضعیت

Workflowها از نظر ساختار و تست‌های Repository آماده‌اند، اما چون این محیط Git
Remote ندارد، اجرای واقعی GitHub Actions هنوز `[?]` است. موفقیت نهایی فقط بعد
از Push و سبزشدن Run در GitHub ثبت می‌شود.

## Workflow مربوط به CI

فایل `.github/workflows/ci.yml` روی رویدادهای `push`، `pull_request` و اجرای
دستی فعال است و دو Job دارد:

1. اجرای Compile و تمام تست‌ها روی Python `3.10` و `3.12` در Ubuntu.
2. اجرای Gate پوشش روی Python `3.12` و ذخیرهٔ گزارش Coverage و نمونهٔ HTML
   Highlighter به‌عنوان Artifact.

دسترسی پیش‌فرض Workflow فقط `contents: read` است. هیچ Token، Password، Secret
یا آدرس Repository داخل فایل Hard-code نشده است.

## روش بررسی در GitHub

```bash
git add .
git commit -m "ci: add coverage docker actions and pages infrastructure"
git push
```

سپس در Tab به نام **Actions**، Workflow به نام **CI** را باز کن. هر سه اجرای
زیر باید سبز باشند:

- Python 3.10
- Python 3.12
- Coverage and HTML artifact

در صفحهٔ Run، Artifactهای `coverage-report` و `syntax-highlight-sample` نیز
باید قابل دانلود باشند.

## Badge

تا قبل از نخستین Run موفق Badge داخل README اضافه نشده است. بعد از موفقیت، از
منوی Workflow گزینهٔ **Create status badge** را بزن یا قالب زیر را با Owner و
نام واقعی Repository جایگزین کن:

```text
https://github.com/OWNER/REPOSITORY/actions/workflows/ci.yml/badge.svg
```

## نسخه‌های Action

Workflow از نسخه‌های Major فعلی `actions/checkout@v6`،
`actions/setup-python@v6` و `actions/upload-artifact@v6` استفاده می‌کند.
Pin شدن روی Major خوانایی را حفظ می‌کند و Patchهای سازگار را دریافت می‌کند.

## Rollback

برای حذف CI، فایل `.github/workflows/ci.yml` را در یک Commit جدا حذف کن. این
کار Source Analyzer را تغییر نمی‌دهد.
