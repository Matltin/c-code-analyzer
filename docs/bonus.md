# Bonus زیرساختی

## محدودهٔ مجاز

این مرحله فقط سه بهبود زیرساختی تأییدشده را اضافه می‌کند:

- B1: پوشش Line و Branch با Gate حداقل ۸۰٪
- B2: Docker چندمرحله‌ای با Runtime غیرـRoot و Test Stage مستقل
- B3: GitHub Actions برای CI و Artifact، به‌علاوهٔ GitHub Pages

این تغییرها رفتار Lexer، Parser، Semantic Analyzer، Project Analysis، CFG،
Data-flow، Call Graph یا Rename را توسعه نمی‌دهند.

## وضعیت

- Phase 0 تا Phase 3: `[x]` تأییدشده توسط کاربر روی Ubuntu
- B1 Coverage: `[?]` آمادهٔ بررسی
- B2 Docker: `[?]` نیازمند اجرای Docker روی Ubuntu کاربر
- B3 GitHub Actions: `[?]` نیازمند Push و Run واقعی
- GitHub Pages: `[?]` نیازمند انتشار واقعی

## دستور Gate

```bash
make bonus-gate
```

این Target Compile، همهٔ تست‌ها، Coverage، Site و تست‌های زیرساخت را اجرا
می‌کند. اگر Docker نصب باشد، Image و Test Stage را هم اجرا می‌کند؛ در غیر این
صورت با پیام `PENDING` اعلام می‌کند که بررسی Docker باقی مانده است.

## قابلیت‌های عمداً پیاده‌سازی‌نشده

Multi-language، تشخیص خودکار زبان، اجرای Preprocessor، Incremental Parsing،
Dominator، Dominance Frontier و SSA خارج از محدوده باقی مانده‌اند. هیچ
Dependency مربوط به این قابلیت‌ها افزوده نشده است.

## بازگشت تغییرات

Bonus زیرساختی از کد اصلی جدا نگه داشته شده است. برای Rollback می‌توان فایل‌های
Workflow، Docker، Site Builder و مستندات Bonus را در یک Commit برگرداند و
تنظیمات Coverage/Makefile را حذف کرد؛ مدل‌های Phaseهای اصلی دست‌نخورده
می‌مانند.
