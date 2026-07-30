# پوشش تست (B1)

## وضعیت

زیرساخت Coverage با وضعیت `[?]` آمادهٔ اجرای Ubuntu کاربر است. Gate روی پوشش
ترکیبی Line و Branch برابر `80%` تنظیم شده و هر نتیجهٔ کمتر باعث شکست دستور
می‌شود.

## ابزار و تنظیمات

Dependency توسعهٔ `pytest-cov` در Extra به نام `dev` ثبت شده است. تنظیمات
Coverage در `pyproject.toml` قرار دارند تا اجرای محلی و CI قرارداد یکسانی
داشته باشند:

- Source فقط `src/c_analyzer` است.
- Branch Coverage فعال است.
- حداقل Coverage برابر `80%` است.
- گزارش Terminal، XML و HTML قابل تولید است.

اجرای کامل:

```bash
make coverage
```

فقط گزارش HTML:

```bash
make coverage-html
xdg-open htmlcov/index.html
```

فایل‌های `coverage.xml`، `.coverage` و پوشهٔ `htmlcov/` خروجی تولیدشده‌اند و
نباید Commit شوند.

## نتیجهٔ مرجع محیط آماده‌سازی

در اجرای B1، هر ۲۴۴ تست موجود Pass شدند. نتیجهٔ گزارش:

- Line Coverage: `91.01%` (`3595/3950`)
- Branch Coverage: `79.81%` (`1194/1496`)
- Coverage ترکیبی Gate: `87.94%`
- حداقل لازم: `80%`

این اعداد نتیجهٔ واقعی همان اجرا هستند؛ اجرای بعدی ممکن است با افزوده‌شدن تست
یا کد کمی تغییر کند. معیار قبولی، عبور از Gate و نبود تست Fail است.

## جلوگیری از بالا بردن مصنوعی عدد

کد Production از محاسبه حذف نشده و تست‌ها برای عبور صوری ضعیف نشده‌اند.
خطوطی که به‌دلیل Error Path یا تعامل محیطی پوشش ندارند در گزارش
`term-missing` دیده می‌شوند و می‌توان بعداً با تست رفتاری واقعی پوشششان داد.

## Rollback

برای بازگرداندن B1، Extra مربوط به `pytest-cov` و بخش‌های `tool.coverage` در
`pyproject.toml` و Targetهای Coverage در `Makefile` را از Commit زیرساخت حذف
کن. هیچ کد Analyzer برای B1 تغییر نکرده است.
