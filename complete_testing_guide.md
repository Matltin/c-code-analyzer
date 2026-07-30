# راهنمای کامل دستورها و تست‌های `c-code-analyzer`

این راهنما برای نسخه‌ی کامل فاز سوم نوشته شده و فرض می‌کند ترمینال در ریشه‌ی
پروژه است؛ یعنی همان پوشه‌ای که `pyproject.toml` و `Makefile` در آن قرار دارند.

وضعیت فعلی مجموعه‌ی تست:

```text
244 tests collected
244 passed
0 failed
0 skipped
```

## تفاوت «صورت پروژه» و «تست‌های افزوده‌شده»

برای جلوگیری از ابهام، در این سند از این برچسب‌ها استفاده می‌شود:

- **[پروژه]**: سناریو صریحاً در صورت پروژه، فازها یا Phase Gateها خواسته شده است.
- **[افزوده]**: سناریوی سخت‌گیرانه‌ای است که من برای Regression، ایمنی یا
  Determinism اضافه کرده‌ام و الزام مستقلی در صورت پروژه نداشته است.
- **[هر دو]**: اصل قابلیت در صورت پروژه خواسته شده و من حالت‌های مرزی بیشتری
  برای آن نوشته‌ام.

نکته‌ی دقیق: کد تمام ۲۴۴ تست خودکار فعلی در جریان پیاده‌سازی پروژه توسط من
نوشته شده است. برچسب بالا مشخص می‌کند «سناریوی تست» از صورت پروژه آمده یا
برای اطمینان بیشتر توسط من اضافه شده است.

## ۱. شروع سریع روی Ubuntu

اگر پروژه را تازه Extract کرده‌ای:

```bash
cd c-code-analyzer
make doctor
make setup
make test
```

نتیجه‌ی مورد انتظار دستور آخر:

```text
244 passed
```

برای بررسی کامل‌تر کد، تست‌ها و CLI:

```bash
make verify
```

برای اجرای دقیق Phase Gate نهایی:

```bash
make gate3
```

## ۲. نصب بدون Make

همان عملیات `make setup` به‌صورت مستقیم:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

پروژه به‌صورت Editable نصب می‌شود؛ بنابراین بعد از تغییر فایل‌های `src` نیاز
به نصب دوباره نیست.

## ۳. راهنمای Makefile

### ۳.۱. دیدن همه‌ی هدف‌ها

```bash
make
make help
```

هر دو، Help دسته‌بندی‌شده‌ی Makefile را نمایش می‌دهند.

### ۳.۲. نصب و بررسی محیط

| دستور | کارکرد | منبع |
|---|---|---|
| `make doctor` | Python 3.10+، GNU Make و ریشه‌ی پروژه را بررسی می‌کند. | [افزوده] |
| `make setup` | `.venv` را می‌سازد و پروژه و pytest را نصب می‌کند. | [پروژه] |
| `make install` | پروژه را در محیط مجازی موجود دوباره Editable نصب می‌کند. | [پروژه] |
| `make compile` | تمام فایل‌های `src` را با `compileall` بررسی می‌کند. | [پروژه] |
| `make collect-tests` | نام تمام ۲۴۴ تست را بدون اجرای آن‌ها نشان می‌دهد. | [افزوده] |
| `make clean` | فقط Cacheها و `output/` تولیدشده را پاک می‌کند. | [افزوده] |

### ۳.۳. اجرای تست‌ها

| دستور | کارکرد |
|---|---|
| `make test` یا `make test-all` | اجرای همه‌ی ۲۴۴ تست با خروجی کوتاه |
| `make test-verbose` | اجرای همه‌ی تست‌ها با نام کامل هر تست |
| `make test-first-failure` | توقف روی اولین Failure |
| `make test-last-failed` | اجرای دوباره‌ی تست‌هایی که دفعه‌ی قبل Fail شدند |
| `make test-k K=rename` | اجرای تست‌هایی که نامشان شامل `rename` است |
| `make test-file FILE=...` | اجرای یک فایل تست |
| `make test-node NODE=...` | اجرای دقیق یک Test Node |

مثال اجرای یک فایل:

```bash
make test-file FILE=tests/test_flow/test_cfg.py
```

مثال اجرای فقط یک تست:

```bash
make test-node NODE=tests/test_flow/test_cfg.py::test_empty_function_connects_entry_directly_to_exit
```

### ۳.۴. تست هر فاز

```bash
make test-phase0
make test-phase1
make test-phase2
make test-phase3
```

- `test-phase0`: مدل‌های Core و CLI اولیه.
- `test-phase1`: Token Rules، Lexer، AST، Parser، Highlight و CLI فاز اول.
- `test-phase2`: Symbol، Resolution، Type، Diagnostic، Intellisense و Integration.
- `test-phase3`: Project، CFG، Data-flow، Call Graph، Rename، CLI و Integration.

این تقسیم‌بندی برای اجرای سریع فازهاست. معیار نهایی همیشه `make test` است.

### ۳.۵. تست هر زیرسیستم

```bash
make test-core
make test-token-rules
make test-lexer
make test-ast
make test-parser
make test-rendering
make test-semantic
make test-symbols
make test-resolution
make test-types
make test-diagnostics
make test-intellisense
make test-project
make test-cfg
make test-dataflow
make test-callgraph
make test-rename
make test-cli
make test-integration
make test-docs
```

تست‌های متمرکز اضافه:

```bash
make test-error-recovery
make test-determinism
make test-rename-atomic
make test-json
```

این چهار هدف **[افزوده]** هستند و برای پیدا کردن سریع خطاهای Recovery، نشت
State، خروجی ناپایدار، Rollback و JSON ساخته شده‌اند.

## ۴. مرجع کامل CLI

تمام فرمان‌ها را می‌توان با یکی از این دو فرم اجرا کرد:

```bash
python -m c_analyzer COMMAND ...
c-analyzer COMMAND ...
```

در Makefile از Python داخل `.venv` استفاده می‌شود.

### ۴.۱. Help و Version

```bash
make cli-help
make cli-version
```

فرم مستقیم:

```bash
python -m c_analyzer --help
python -m c_analyzer --version
```

کارکرد: فهرست Commandها و نسخه‌ی Package. **[پروژه]**

### ۴.۲. Token Stream

```bash
make tokens
```

فرم کلی:

```bash
python -m c_analyzer tokens FILE.c
```

نمونه:

```bash
python -m c_analyzer tokens examples/valid/basic.c
```

هر خط شامل TokenKind، Lexeme و `line:column` است. Comment و Directive نیز
مطابق Scope به Token تبدیل می‌شوند. **[پروژه]**

### ۴.۳. AST

```bash
make ast
```

فرم کلی:

```bash
python -m c_analyzer ast FILE.c
```

AST Printer ساختار قطعی درخت را نشان می‌دهد و Diagnosticها را در `stderr`
می‌نویسد. **[پروژه]**

### ۴.۴. بررسی Diagnostic

```bash
make check-valid
make check-invalid
make check-json
```

فرم کلی:

```bash
python -m c_analyzer check FILE.c
python -m c_analyzer check FILE.c --json
```

نمونه‌ها:

```bash
python -m c_analyzer check examples/valid/basic.c
python -m c_analyzer check examples/invalid/multiple_errors.c
python -m c_analyzer check examples/semantic/invalid/type_errors.c --json
```

- فایل معتبر: Exit Code صفر.
- Error Diagnostic: Exit Code یک.
- مشکل فایل یا Argument: Exit Code دو.

هدف‌های `check-invalid` و `check-json` در Makefile، Exit Code یک را نتیجه‌ی
صحیح می‌دانند و به همین دلیل خود Make Fail نمی‌شود. **[هر دو]**

### ۴.۵. Syntax و Semantic Highlight

```bash
make highlight-ansi
make highlight-html
```

فرم کلی:

```bash
python -m c_analyzer highlight FILE.c --format ansi
python -m c_analyzer highlight FILE.c --format html
python -m c_analyzer highlight FILE.c --format html --output OUTPUT.html
```

`highlight-html` فایل زیر را می‌سازد:

```text
output/highlight.html
```

HTML مستقل است و در مرورگر باز می‌شود. Whitespace و Escapeهای HTML باید حفظ
شوند. **[پروژه]**

### ۴.۶. Symbol Table

```bash
make symbols
```

فرم کلی:

```bash
python -m c_analyzer symbols FILE.c
```

Scope Tree، Namespace، Symbol ID، Kind و Type را نمایش می‌دهد. **[پروژه]**

### ۴.۷. Completion

```bash
make complete
```

فرم کلی:

```bash
python -m c_analyzer complete FILE.c LINE COLUMN
python -m c_analyzer complete FILE.c LINE COLUMN --json
```

نمونه‌ی معتبر پروژه:

```bash
python -m c_analyzer complete examples/semantic/valid/completion.c 11 27
```

Line و Column از یک شروع می‌شوند. نتیجه بر اساس Scope، Prefix/Fuzzy Match و
Type مرتب می‌شود. **[پروژه]**

### ۴.۸. Hover

```bash
make hover
```

فرم کلی:

```bash
python -m c_analyzer hover FILE.c LINE COLUMN
python -m c_analyzer hover FILE.c LINE COLUMN --json
```

نمونه:

```bash
python -m c_analyzer hover examples/semantic/valid/hover.c 6 18
```

نام، Kind، Type، Signature، Scope و Definition را نشان می‌دهد. **[پروژه]**

### ۴.۹. Project Check

```bash
make project-check
make project-check-json
```

فرم کلی:

```bash
python -m c_analyzer project-check PROJECT_DIR
python -m c_analyzer project-check PROJECT_DIR --json
```

تمام فایل‌های `.c` را با ترتیب Path تحلیل می‌کند و Project Symbolها، فایل‌ها
و Diagnosticها را نمایش می‌دهد. **[پروژه]**

### ۴.۱۰. Go-to-Definition

```bash
make goto-def
make goto-def-json
```

فرم کلی:

```bash
python -m c_analyzer goto-def FILE LINE COLUMN --project PROJECT_DIR
python -m c_analyzer goto-def FILE LINE COLUMN --project PROJECT_DIR --json
```

موقعیت پیش‌فرض Makefile روی فراخوانی `add` است:

```text
examples/project/main.c:6:17
```

Definition مورد انتظار:

```text
math_utils.c:2:5
```

**[پروژه]**

### ۴.۱۱. Find References

```bash
make find-refs
make find-refs-json
```

فرم کلی:

```bash
python -m c_analyzer find-refs FILE LINE COLUMN --project PROJECT_DIR
python -m c_analyzer find-refs FILE LINE COLUMN --project PROJECT_DIR --json
```

Definition، Declaration و Referenceها را همراه `READ`، `WRITE`،
`READ_WRITE`، `CALL`، `TYPE_REFERENCE` یا `MEMBER_ACCESS` نشان می‌دهد.
**[پروژه]**

### ۴.۱۲. CFG

```bash
make cfg-text
make cfg-json
make cfg-dot
```

فرم کلی:

```bash
python -m c_analyzer show-cfg FILE FUNCTION --project PROJECT_DIR --format text
python -m c_analyzer show-cfg FILE FUNCTION --project PROJECT_DIR --format json
python -m c_analyzer show-cfg FILE FUNCTION --project PROJECT_DIR --format dot
```

برای دیدن CFG تابع Recursive نمونه:

```bash
make cfg-text MAIN_FILE=examples/project/math_utils.c MAIN_FUNCTION=factorial
```

DOT فقط متن تولید می‌کند و نصب Graphviz لازم نیست. **[پروژه]**

### ۴.۱۳. Call Graph

```bash
make callgraph-text
make callgraph-json
make callgraph-dot
```

فرم کلی:

```bash
python -m c_analyzer callgraph PROJECT_DIR --entry main --format text
python -m c_analyzer callgraph PROJECT_DIR --entry main --format json
python -m c_analyzer callgraph PROJECT_DIR --entry main --format dot
```

خروجی نمونه باید Recursive بودن `factorial` و Dead بودن `point_sum` و
`unused_helper` نسبت به `main` را نشان دهد. Entry سفارشی نیز مجاز است.
**[پروژه]**

### ۴.۱۴. Dead Code

```bash
make dead-code
make dead-code-json
```

فرم کلی:

```bash
python -m c_analyzer dead-code PROJECT_DIR
python -m c_analyzer dead-code PROJECT_DIR --entry FUNCTION --json
```

گزارش شامل Unreachable Block، Statement پس از Jump، Unused Variable، Dead
Assignment، Missing Return و Dead Function است. **[پروژه]**

### ۴.۱۵. Safe Rename

Preview امن و بدون تغییر فایل:

```bash
make rename-preview
make rename-preview-json
```

فرم کلی:

```bash
python -m c_analyzer rename FILE LINE COLUMN NEW_NAME --project PROJECT_DIR
python -m c_analyzer rename FILE LINE COLUMN NEW_NAME --project PROJECT_DIR --json
```

نوشتن واقعی فقط با Flag صریح:

```bash
python -m c_analyzer rename FILE LINE COLUMN NEW_NAME --project PROJECT_DIR --apply
```

Makefile عمداً Targetی که Example اصلی را Apply کند ندارد. تست Apply، Stage
Failure و Rollback با این دستور و در Temporary Directory انجام می‌شود:

```bash
make test-rename-atomic
```

**[هر دو]** — Preview، Conflict، بازتحلیل، Apply اتمیک و Rollback الزام پروژه
بودند؛ جداسازی Staging Failure و Cross-file Capture تست‌های سخت‌گیرانه‌ی
افزوده هستند.

### ۴.۱۶. REPL

```bash
make repl
```

فرم مستقیم:

```bash
python -m c_analyzer repl examples/project
```

Commandهای داخل REPL:

```text
help
project-check
goto-def FILE LINE COLUMN
find-refs FILE LINE COLUMN
show-cfg FILE FUNCTION
callgraph
dead-code
rename FILE LINE COLUMN NEW_NAME
quit
exit
```

Rename در REPL فقط Preview است. EOF، ورودی نامعتبر و Command ناشناخته نباید
Traceback خام ایجاد کنند. **[پروژه]**

## ۵. تغییر ورودی‌های پیش‌فرض Makefile

متغیرهای قابل Override:

```text
PROJECT_DIR
MAIN_FILE
MAIN_FUNCTION
GOTO_LINE
GOTO_COLUMN
RENAME_LINE
RENAME_COLUMN
RENAME_TO
PYTHON
VENV
```

مثال‌ها:

```bash
make project-check PROJECT_DIR=/path/to/my/project
make cfg-json PROJECT_DIR=/path/to/my/project MAIN_FILE=/path/to/my/project/file.c MAIN_FUNCTION=calculate
make goto-def PROJECT_DIR=/path/to/my/project MAIN_FILE=/path/to/my/project/file.c GOTO_LINE=10 GOTO_COLUMN=8
make rename-preview RENAME_TO=answer
```

## ۶. موجودی دقیق تست‌های خودکار

### فاز صفر تا دوم — ۱۵۴ تست Regression

| فایل | تعداد | پوشش | منبع سناریو |
|---|---:|---|---|
| `tests/test_core/test_source.py` | 12 | Position، Span، ورودی نامعتبر، End-exclusive | [هر دو] |
| `tests/test_core/test_diagnostic.py` | 2 | Diagnostic و نمایش متنی | [پروژه] |
| `tests/test_core/test_package_imports.py` | 1 | Import عمومی مدل‌ها | [پروژه] |
| `tests/test_core/test_token.py` | 1 | Token، Lexeme و Span | [پروژه] |
| `tests/test_cli.py` | 2 | Help و Version | [پروژه] |
| `tests/test_lexer/test_rules.py` | 9 | Keyword/Operator/Delimiter، Longest Match، Read-only | [هر دو] |
| `tests/test_lexer/test_lexer.py` | 16 | Tokenization، Location، Literal، Comment، Recovery | [هر دو] |
| `tests/test_ast/test_grammar.py` | 3 | Nonterminal، Associativity و Scope Grammar | [پروژه] |
| `tests/test_ast/test_nodes.py` | 4 | Declaration، Statement و Expression Nodeها | [پروژه] |
| `tests/test_ast/test_printer.py` | 1 | Printer قطعی | [هر دو] |
| `tests/test_parser/test_parser.py` | 13 | Syntax، Precedence، Postfix و Panic-mode | [هر دو] |
| `tests/test_rendering/test_highlighting.py` | 4 | ANSI، HTML، Escape و Invalid Token | [پروژه] |
| `tests/test_rendering/test_semantic_highlighting.py` | 2 | نقش Semantic و حفظ Source | [پروژه] |
| `tests/test_semantic/test_symbols.py` | 12 | Scope، Namespace، Symbol ID و Built-in | [هر دو] |
| `tests/test_semantic/test_resolution.py` | 13 | Resolution، Shadowing، Prototype و AccessKind | [هر دو] |
| `tests/test_semantic/test_type_checker.py` | 17 | Type، Conversion، Call، Return و Initializer | [هر دو] |
| `tests/test_semantic/test_diagnostics_pipeline.py` | 9 | Merge، Sort، Dedup، JSON و Exit Code | [هر دو] |
| `tests/test_semantic/test_intellisense.py` | 11 | Completion، Hover، Ranking و ورودی ناقص | [هر دو] |
| `tests/test_semantic/test_phase2_docs.py` | 4 | مستندات و مرز Checklist | [افزوده] |
| `tests/test_cli_phase1.py` | 6 | CLI Lexer/Parser/Highlight و Error Path | [هر دو] |
| `tests/test_cli_phase2.py` | 4 | Symbols، Completion، Hover و Position نامعتبر | [هر دو] |
| `tests/test_integration/test_phase2_pipeline.py` | 8 | Pipeline کامل، چند خطا، State Leak و Determinism | [هر دو] |

جمع این بخش: `154` تست.

### فاز سوم — ۹۰ تست جدید

| فایل | تعداد | پوشش | منبع سناریو |
|---|---:|---|---|
| `tests/test_project/test_project_index.py` | 15 | Multi-file، Navigation، Hover، Docs، State Leak | [هر دو] |
| `tests/test_flow/test_cfg.py` | 13 | Branch، Loop، Jump، Validator، JSON/DOT | [هر دو] |
| `tests/test_flow/test_dataflow.py` | 17 | Fixed Point، Definite Assignment، Liveness، Dead Code | [هر دو] |
| `tests/test_callgraph/test_callgraph.py` | 12 | Caller/Callee، Reachability، SCC، Recursion، Dead | [هر دو] |
| `tests/test_refactor/test_rename.py` | 18 | Rename Scope-aware، Diff، Apply، Conflict، Rollback | [هر دو] |
| `tests/test_cli_phase3.py` | 6 | تمام CLIهای فاز سوم، JSON و REPL | [هر دو] |
| `tests/test_integration/test_phase3_pipeline.py` | 6 | End-to-End، خطاها، Determinism و Path قابل‌حمل | [هر دو] |
| `tests/test_integration/test_phase3_docs.py` | 3 | مستندات، Example و Checklist | [افزوده] |

جمع این بخش: `90` تست.

جمع کل: `154 + 90 = 244` تست.

## ۷. تست‌هایی که صریحاً صورت پروژه خواسته است

### Phase 0

- نصب Editable، Help و Version.
- Position و Span معتبر/نامعتبر.
- End-exclusive بودن Span.
- Token و Diagnostic و Import عمومی.

فرمان:

```bash
make gate0
```

### Phase 1

- Token Specification و Longest Match.
- Lexer برای Tokenها، Literalها، Comment و Directive.
- Lexer Error Recovery و چند خطا.
- AST و تقدم Operator.
- Parser و Panic-mode Recovery.
- ANSI و HTML Highlighter.

فرمان:

```bash
make gate1
```

### Phase 2

- Scope، Symbol Table، Namespace و Built-in.
- Resolution و تمام AccessKindها.
- Type System، Return، Call و Initializer.
- Diagnostic متنی/JSON، Sort و Dedup.
- Completion، Hover و Semantic Highlight.
- Pipeline معتبر، Syntax Error، Semantic Error و چند خطا.

فرمان:

```bash
make gate2
```

### Phase 3

- Project چندفایلی و Navigation.
- CFG برای خطی، Branch، Loop، Jump و Nested Flow.
- Fixed-point، Definite Assignment و Liveness.
- Unreachable، Dead Assignment و Missing Return.
- Call Graph، Reachability، SCC، Recursion و Dead Function.
- Rename Variable/Parameter/Function/Struct/Field.
- Dry-run، Diff، Conflict، Apply اتمیک و Rollback.
- تمام CLIها، REPL و End-to-End Pipeline.

فرمان:

```bash
make gate3
```

## ۸. کنترل‌های اضافه‌ای که من نوشته‌ام

این موارد نسبت به حداقل صورت پروژه سخت‌گیرانه‌ترند:

- Read-only بودن جدول‌های Lexer در Runtime.
- جلوگیری از Lexeme تکراری میان جدول‌ها.
- رد Span با Display Position معکوس، حتی اگر Offset ظاهراً معتبر باشد.
- حفظ کامل AST و Semantic Model بعد از ساخت CFG.
- Validator روی Edge و Neighbor خراب بدون Crash.
- نشت‌نکردن Parameter یک Function به State Function دیگر.
- ثابت‌بودن Output در تحلیل‌های مستقل و با ترتیب ورودی متفاوت.
- گروه‌بندی چند Call Site در یک Call Graph Edge.
- Entry سفارشی و Entry ناموجود به‌شکل کنترل‌شده.
- Capture چندفایلی هنگام Rename Function.
- Staging Failure قبل از Apply و Failure وسط Replace.
- بازتحلیل Sourceهای Renameشده پیش از Success.
- Normalize شدن Path با `\\` برای خروجی قابل‌حمل Ubuntu.
- وجود دقیق مستندات، Example Project و وضعیت Checklist.
- هدف‌های متمرکز `test-error-recovery`، `test-determinism`،
  `test-rename-atomic` و `test-json` در Makefile.

## ۹. تست دستی Happy Path

این مسیر تمام قابلیت‌های اصلی را بدون تغییر Source اصلی نشان می‌دهد:

```bash
make cli-help
make cli-version
make tokens
make ast
make check-valid
make highlight-ansi
make highlight-html
make symbols
make complete
make hover
make project-check
make goto-def
make find-refs
make cfg-text
make cfg-json
make cfg-dot
make callgraph-text
make callgraph-json
make callgraph-dot
make dead-code
make rename-preview
```

نسخه‌ی کوتاه‌تر:

```bash
make smoke
```

## ۱۰. تست دستی Error Path

### Lexical، Syntax و چند خطا

```bash
python -m c_analyzer check examples/invalid/lexical_error.c
python -m c_analyzer check examples/invalid/syntax_error.c
python -m c_analyzer check examples/invalid/multiple_errors.c
```

هرکدام باید Diagnostic بدهند، بدون Traceback خام، و Exit Code یک داشته باشند.

### Semantic Error

```bash
python -m c_analyzer check examples/semantic/invalid/type_errors.c
python -m c_analyzer check examples/semantic/invalid/wrong_call.c
python -m c_analyzer check examples/semantic/invalid/initialization.c
python -m c_analyzer check examples/semantic/invalid/multiple_errors.c
```

### فایل ناموجود

```bash
python -m c_analyzer check does-not-exist.c
```

انتظار: پیام کنترل‌شده و Exit Code دو، بدون Traceback.

### Project ناموجود

```bash
python -m c_analyzer project-check does-not-exist
```

انتظار: Exit Code دو.

### Position نامعتبر

```bash
python -m c_analyzer goto-def examples/project/main.c 999 1 --project examples/project
```

انتظار: پیام Position نامعتبر و Exit Code دو.

### Entry ناموجود Call Graph

```bash
python -m c_analyzer callgraph examples/project --entry missing --format text
```

انتظار: پیام `entry function not found` و Exit Code یک.

### Rename با Keyword

```bash
python -m c_analyzer rename examples/project/main.c 6 9 return --project examples/project
```

انتظار: رد نام جدید و عدم تغییر فایل.

### Rename دارای Conflict

در `main.c` نام `discarded` از قبل در همان Scope وجود دارد:

```bash
python -m c_analyzer rename examples/project/main.c 6 9 discarded --project examples/project
```

انتظار: Conflict و عدم تغییر فایل.

### Rename Built-in

```bash
python -m c_analyzer rename examples/project/main.c 9 5 write_line --project examples/project
```

انتظار: Built-in قابل Rename نیست.

## ۱۱. تست امن `--apply` روی Copy موقت

این تست Example اصلی را تغییر نمی‌دهد:

```bash
TEST_ROOT="$(mktemp -d)"
cp -R examples/project "$TEST_ROOT/project"

python -m c_analyzer rename \
  "$TEST_ROOT/project/main.c" 6 9 result \
  --project "$TEST_ROOT/project" --apply

python -m c_analyzer project-check "$TEST_ROOT/project"
grep -n result "$TEST_ROOT/project/main.c"
grep -n total "$TEST_ROOT/project/main.c"
```

انتظار:

- Rename با پیام `Applied atomically.` موفق شود.
- `result` در Definition و Referenceها دیده شود.
- `total` دیگر به‌عنوان Identifier هدف وجود نداشته باشد.
- Project جدید Error نداشته باشد.

Rollback واقعی به‌صورت خودکار و با Failure تزریقی تست می‌شود:

```bash
make test-rename-atomic
```

## ۱۲. اعتبارسنجی JSON

خروجی‌های JSON را می‌توان با Standard Library خود Python Parse کرد:

```bash
python -m c_analyzer project-check examples/project --json | python -m json.tool >/dev/null
python -m c_analyzer goto-def examples/project/main.c 6 17 --project examples/project --json | python -m json.tool >/dev/null
python -m c_analyzer find-refs examples/project/main.c 6 17 --project examples/project --json | python -m json.tool >/dev/null
python -m c_analyzer show-cfg examples/project/main.c main --project examples/project --format json | python -m json.tool >/dev/null
python -m c_analyzer callgraph examples/project --entry main --format json | python -m json.tool >/dev/null
python -m c_analyzer dead-code examples/project --json | python -m json.tool >/dev/null
```

برای اجرای تست‌های خودکار JSON:

```bash
make test-json
```

## ۱۳. تست Determinism

تست خودکار:

```bash
make test-determinism
```

تست دستی نمونه:

```bash
python -m c_analyzer project-check examples/project > /tmp/project-index-1.txt
python -m c_analyzer project-check examples/project > /tmp/project-index-2.txt
diff -u /tmp/project-index-1.txt /tmp/project-index-2.txt
```

اگر خروجی قطعی باشد، `diff` چیزی چاپ نمی‌کند و Exit Code صفر دارد.

همین کار برای CFG و Call Graph:

```bash
python -m c_analyzer show-cfg examples/project/main.c main --project examples/project --format text > /tmp/cfg-1.txt
python -m c_analyzer show-cfg examples/project/main.c main --project examples/project --format text > /tmp/cfg-2.txt
diff -u /tmp/cfg-1.txt /tmp/cfg-2.txt

python -m c_analyzer callgraph examples/project --entry main --format text > /tmp/callgraph-1.txt
python -m c_analyzer callgraph examples/project --entry main --format text > /tmp/callgraph-2.txt
diff -u /tmp/callgraph-1.txt /tmp/callgraph-2.txt
```

## ۱۴. Phase Gateها

```bash
make gate0
make gate1
make gate2
make gate3
```

اجرای پشت سر هم همه‌ی Gateها:

```bash
make gate-all
```

`gate-all` عمداً تعدادی تست را دوباره اجرا می‌کند، چون هدف آن اثبات مستقل هر
فاز است. برای بررسی سریع‌تر روزمره از این دستور استفاده کن:

```bash
make verify
```

## ۱۵. خروجی‌های مورد انتظار Example Project

`make project-check` باید حداقل این فایل‌ها را نشان دهد:

```text
main.c
math_utils.c
structs.c
unused.c
```

`make goto-def` باید Definition تابع `add` را در این محل پیدا کند:

```text
math_utils.c:2:5
```

`make callgraph-text` باید موارد زیر را نشان دهد:

```text
factorial -> factorial
recursive: factorial
dead: point_sum
dead: unused_helper
```

شناسه‌های واقعی به‌شکل `project-sym-NNNN` نمایش داده می‌شوند.

`make dead-code` باید برای `main.c` حداقل این موارد را پیدا کند:

```text
unreachable_blocks: 1
post_jump_statements: 1
unused_variables: 1
dead_assignments: 1
missing_returns: 0
```

`make rename-preview` باید Unified Diff نشان دهد و در پایان بگوید:

```text
Preview only; no files changed.
```

## ۱۶. اگر تستی Fail شد

ابتدا فقط همان Failure را با جزئیات اجرا کن:

```bash
make test-last-failed
```

یا Test Node گزارش‌شده را مستقیماً اجرا کن:

```bash
make test-node NODE=PATH/TO/TEST.py::test_name
```

برای توقف سریع روی اولین مشکل:

```bash
make test-first-failure
```

برای دیدن تمام جزئیات:

```bash
make test-verbose
```

موارد پایه را نیز بررسی کن:

```bash
make doctor
make install
make compile
```

در گزارش خطا این اطلاعات را نگه دار:

```text
python3 --version
make --version
python -m pytest -q
نام Test Node ناموفق
خروجی کامل Failure
```

## ۱۷. معیار تأیید نهایی روی سیستم تو

برای تأیید فاز سوم، حداقل این سه دستور باید موفق باشند:

```bash
make doctor
make test
make gate3
```

معیار نتیجه:

- `244 passed`
- `0 failed`
- Compile بدون خطا
- Project Index و Navigation صحیح
- CFG و Data-flow بدون Crash
- Call Graph شامل Recursion و Dead Function
- Rename Preview بدون تغییر فایل
- Apply و Rollback در تست‌های Temporary Directory موفق
- REPL و ورودی‌های نامعتبر بدون Traceback خام

تا قبل از اجرای این موارد روی Ubuntu تو، وضعیت فاز سوم در Checklist باید `[?]`
باقی بماند.
