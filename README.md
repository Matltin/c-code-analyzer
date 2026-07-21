# c-code-analyzer

`c-code-analyzer` یک پروژه‌ی آموزشی طراحی کامپایلر است که در پایان، یک
زیرمجموعه‌ی مستندشده از زبان C را تحلیل خواهد کرد. زبان پیاده‌سازی Python و
رابط اصلی CLI است.

نسخه‌ی فعلی **Phase 0** و مشخصات بخش **1.1** را پوشش می‌دهد:

- ساختار نصب‌پذیر Python با روش `src`
- CLI پایه با Help و Version
- مدل‌های مشترک Source، Token و Diagnostic
- `TokenKind`های زیرمجموعه‌ی مستندشده‌ی C
- جدول‌های read-only مربوط به Keyword، Operator و Delimiter
- ترتیب قطعی Longest Match برای Operatorها
- تست‌های خودکار Phase 0 و بخش 1.1

در این نسخه هنوز Lexer، Tokenization، Parser یا Semantic Analyzer وجود ندارد.

## پیش‌نیاز

- Linux
- Python 3.10 یا جدیدتر
- `pip`

برای دیدن نسخه‌ی Python:

```bash
python3 --version
```

## ساخت محیط و نصب

از داخل پوشه‌ی پروژه اجرا کنید:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install pytest
```

راه کوتاه‌تر برای نصب پروژه همراه dependencyهای توسعه:

```bash
python -m pip install -e ".[dev]"
```

نصب `-e` یا Editable باعث می‌شود تغییرات پوشه‌ی `src` بدون نصب مجدد در محیط
قابل‌استفاده باشند.

## اجرای CLI

نمایش Help:

```bash
python -m c_analyzer --help
```

نمایش Version:

```bash
python -m c_analyzer --version
```

پس از نصب، Entry Point کوتاه نیز قابل استفاده است:

```bash
c-analyzer --help
```

CLI فعلی عمداً هیچ command مربوط به Lexer یا Parser ندارد.

## اجرای تست‌ها

ابتدا Virtual Environment را فعال کنید و سپس:

```bash
python -m pytest
```

برای خروجی جزئی‌تر:

```bash
python -m pytest -vv
```

## نمونه‌ی استفاده از مدل‌های Core

```python
from c_analyzer import SourcePosition, SourceSpan

start = SourcePosition(file="example.c", line=1, column=1, offset=0)
end = SourcePosition(file="example.c", line=1, column=4, offset=3)
span = SourceSpan(start=start, end=end)

print(span.length)
```

در این مثال Span بازه‌ی `[0, 3)` را نشان می‌دهد؛ یعنی Offset انتهایی عضو Span
نیست.

## مستندات

- Scope زبان: `docs/supported_c_subset.md`
- مشخصات Tokenها: `docs/token_specification.md`
- محدودیت‌ها: `docs/limitations.md`
- وضعیت مراحل: `PROJECT_CHECKLIST.md`

## وضعیت توسعه

Phase 0 تأیید شده و بخش 1.1 برای تست کاربر آماده است. پیاده‌سازی Lexer در بخش
1.2 فقط پس از تأیید صریح بخش 1.1 انجام خواهد شد.
