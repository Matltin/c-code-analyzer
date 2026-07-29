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
python -m c_analyzer symbols examples/semantic/valid/scopes.c
python -m c_analyzer check examples/semantic/invalid/type_errors.c --json
python -m c_analyzer complete examples/semantic/valid/completion.c 11 27
python -m c_analyzer hover examples/semantic/valid/hover.c 6 18
python -m c_analyzer project-check examples/project
python -m c_analyzer goto-def examples/project/main.c 6 17 --project examples/project
python -m c_analyzer find-refs examples/project/main.c 6 17 --project examples/project
python -m c_analyzer show-cfg examples/project/main.c main --project examples/project --format text
python -m c_analyzer callgraph examples/project --entry main --format text
python -m c_analyzer dead-code examples/project
python -m c_analyzer rename examples/project/main.c 6 9 result --project examples/project
python -m c_analyzer repl examples/project
```

همین Commandها پس از نصب با نام کوتاه `c-analyzer` نیز قابل اجرا هستند.

وجود Error Diagnostic باعث Exit Code برابر ۱ می‌شود. Warning و Info به‌تنهایی
Exit Code صفر دارند. خطای فایل یا Position نامعتبر Exit Code برابر ۲ دارد.

فرمت `json` برای `project-check`، `goto-def`، `find-refs`، `show-cfg`،
`callgraph` و `dead-code` در دسترس است. CFG و Call Graph فرمت `dot` نیز
دارند و نصب Graphviz لازم نیست.

Rename بدون Flag فقط Unified Diff نشان می‌دهد. Apply صریح:

```bash
python -m c_analyzer rename examples/project/main.c 6 9 result \
  --project examples/project --apply
```

## ورودی‌های نمونه

- `examples/valid/basic.c`: Function، فراخوانی و Expression
- `examples/valid/control_flow.c`: شرط و Loop
- `examples/valid/structs.c`: Struct و Member Access
- `examples/valid/pointers_arrays.c`: Pointer، Array و Initializer
- `examples/invalid/lexical_error.c`: خطای Lexical
- `examples/invalid/syntax_error.c`: خطای Syntax
- `examples/invalid/multiple_errors.c`: چند خطا همراه ادامه‌ی تحلیل
- `examples/semantic/valid/scopes.c`: Nested Scope و Shadowing
- `examples/semantic/valid/forward_call.c`: Forward Function Call
- `examples/semantic/valid/structs.c`: Struct و Pointer-to-Struct
- `examples/semantic/valid/completion.c`: Context برای Completion
- `examples/semantic/valid/hover.c`: Context برای Hover و Built-in
- `examples/semantic/invalid/type_errors.c`: چند Type Error
- `examples/semantic/invalid/wrong_call.c`: Argument Count و Type
- `examples/semantic/invalid/initialization.c`: Use Before Initialization
- `examples/semantic/invalid/multiple_errors.c`: چند خطای Semantic

Line و Column در `complete` و `hover` از ۱ شروع می‌شوند. Position می‌تواند روی
یک Identifier یا درست بعد از `.` و `->` باشد.

## تست

```bash
python -m pytest -q
```
