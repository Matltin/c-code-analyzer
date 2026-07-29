# c-code-analyzer

`c-code-analyzer` یک پروژه‌ی آموزشی طراحی کامپایلر است که در پایان، یک
زیرمجموعه‌ی مستندشده از زبان C را تحلیل خواهد کرد. زبان پیاده‌سازی Python و
رابط اصلی CLI است.

نسخه‌ی فعلی تمام قابلیت‌های الزامی **Phase 3** را برای بررسی Ubuntu پوشش می‌دهد:

- ساختار نصب‌پذیر Python با روش `src`
- مدل‌های مشترک Source، Token و Diagnostic
- Lexer دست‌نویس همراه Error Recovery
- Grammar رسمی EBNF
- AST دارای SourceSpan و Printer
- Recursive Descent Parser همراه Panic-mode
- Syntax Highlighting مبتنی بر Token و AST
- Scope Tree و Symbol Table با Namespaceهای جدا
- Two-pass Name Resolution و Reference Tracking
- Type Checking و Initialization Tracking محافظه‌کارانه
- Diagnosticهای متنی و JSON
- Completion عمومی، Member و Argument-aware
- Hover و Semantic Highlighting
- خروجی ANSI و HTML مستقل
- CLI برای Token، AST، Diagnostic، Symbol، Completion، Hover و Highlight
- Project Index چندفایلی، Navigation و Documentation Comment
- CFG با خروجی text، JSON و DOT و Validator داخلی
- Definite Assignment، Liveness، Dead Code و Missing Return
- Call Graph، Reachability، Recursion و Tarjan SCC
- Safe Rename مبتنی بر Symbol ID با Preview، بازتحلیل و Apply اتمیک
- CLI نهایی و REPL قابل‌آزمایش با Stream تزریقی
- تست‌های Regression از Phase 0 تا Phase 3

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

Commandهای فاز اول:

```bash
python -m c_analyzer tokens examples/valid/basic.c
python -m c_analyzer ast examples/valid/basic.c
python -m c_analyzer check examples/invalid/multiple_errors.c
python -m c_analyzer highlight examples/valid/basic.c --format ansi
python -m c_analyzer highlight examples/valid/basic.c --format html
python -m c_analyzer highlight examples/valid/basic.c --format html --output output.html
```

Commandهای فاز دوم:

```bash
python -m c_analyzer symbols examples/semantic/valid/scopes.c
python -m c_analyzer check examples/semantic/invalid/type_errors.c
python -m c_analyzer check examples/semantic/invalid/type_errors.c --json
python -m c_analyzer complete examples/semantic/valid/completion.c 11 27
python -m c_analyzer hover examples/semantic/valid/hover.c 6 18
```

Commandهای فاز سوم روی Project نمونه:

```bash
python -m c_analyzer project-check examples/project
python -m c_analyzer goto-def examples/project/main.c 6 17 --project examples/project
python -m c_analyzer find-refs examples/project/main.c 6 17 --project examples/project
python -m c_analyzer show-cfg examples/project/main.c main --project examples/project --format text
python -m c_analyzer callgraph examples/project --entry main --format text
python -m c_analyzer dead-code examples/project
python -m c_analyzer rename examples/project/main.c 6 9 result --project examples/project
python -m c_analyzer repl examples/project
```

Rename پیش‌فرض Dry-run است. فقط افزودن `--apply` فایل‌ها را پس از Conflict
Check و بازتحلیل کامل، به‌صورت اتمیک تغییر می‌دهد.

فرم کوتاه `c-analyzer ...` نیز پس از نصب Editable قابل استفاده است.

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
- طراحی Lexer: `docs/lexer.md`
- Grammar و AST: `docs/ast.md`
- طراحی Parser: `docs/parser.md`
- تحلیل Semantic و Symbolها: `docs/semantic_analysis.md`
- Type System: `docs/type_system.md`
- Completion و Hover: `docs/intellisense.md`
- Diagnosticها: `docs/diagnostics.md`
- معماری: `docs/architecture.md`
- الگوریتم‌ها: `docs/algorithms.md`
- راهنمای CLI: `docs/usage.md`
- تحلیل Project: `docs/project_analysis.md`
- Navigation: `docs/navigation.md`
- CFG: `docs/cfg.md`
- Data-flow: `docs/dataflow.md`
- Call Graph: `docs/callgraph.md`
- Safe Rename: `docs/refactoring.md`
- REPL: `docs/repl.md`
- محدودیت‌ها: `docs/limitations.md`
- وضعیت مراحل: `PROJECT_CHECKLIST.md`

## وضعیت توسعه

Phase 0، Phase 1 و Phase 2 توسط کاربر تأیید شده‌اند. بخش‌های 3.1 تا 3.5 و
Phase Gate 3 با وضعیت `[?]` برای تست نهایی روی Ubuntu کاربر آماده‌اند. Bonus
شروع نشده است.
