# راهنمای استفاده

## نصب روی Ubuntu

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install pytest
```

## Commandها

```bash
python -m c_analyzer tokens examples/valid/basic.c
python -m c_analyzer ast examples/valid/basic.c
python -m c_analyzer check examples/invalid/multiple_errors.c
python -m c_analyzer highlight examples/valid/basic.c --format ansi
python -m c_analyzer highlight examples/valid/basic.c --format html
python -m c_analyzer highlight examples/valid/basic.c --format html --output output.html
```

همین Commandها پس از نصب با نام کوتاه `c-analyzer` نیز قابل اجرا هستند.

وجود Error Diagnostic باعث Exit Code برابر ۱ می‌شود. خطای خواندن یا نوشتن
فایل Exit Code برابر ۲ دارد. کد معتبر Exit Code صفر دارد.

## ورودی‌های نمونه

- `examples/valid/basic.c`: Function، فراخوانی و Expression
- `examples/valid/control_flow.c`: شرط و Loop
- `examples/valid/structs.c`: Struct و Member Access
- `examples/valid/pointers_arrays.c`: Pointer، Array و Initializer
- `examples/invalid/lexical_error.c`: خطای Lexical
- `examples/invalid/syntax_error.c`: خطای Syntax
- `examples/invalid/multiple_errors.c`: چند خطا همراه ادامه‌ی تحلیل

## تست

```bash
python -m pytest -q
```
