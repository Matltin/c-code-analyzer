# PROJECT CHECKLIST — c-code-analyzer

## راهنمای وضعیت‌ها

- `[ ]` شروع نشده
- `[~]` در حال پیاده‌سازی
- `[?]` آماده‌ی بررسی
- `[x]` تأییدشده توسط کاربر
- `[!]` مسدود یا دارای اشکال

هیچ بخش `[?]` بدون تأیید صریح کاربر به `[x]` تغییر نمی‌کند.

## قوانین مشترک Definition of Done

هر بخش باید:

- کد یا مستندات مرتبط و محدود به همان بخش داشته باشد.
- تست خودکار رفتاری داشته باشد؛ اگر بخش فقط مستندات است، اعتبارسنجی قابل‌تکرار
  برای فایل‌ها داشته باشد.
- همه‌ی تست‌های قبلی و جدید را Pass کند.
- در صورت مرتبط بودن، Happy Path و Error Path داشته باشد.
- Source Location را در تمام داده‌های مهم حفظ کند.
- روی ورودی نامعتبر Crash نکند.
- مستندات و محدودیت‌های شناخته‌شده را به‌روز کند.
- خروجی واقعی دستورهای اجراشده را گزارش کند.
- یک Commit کوچک و معنادار پیشنهاد دهد.
- ابتدا `[?]` شود و فقط پس از تأیید کاربر `[x]` شود.

## Phase 0 — آماده‌سازی اجباری

### [x] 0.1 — تثبیت Scope

- تعریف نام و هدف پروژه
- تعریف ورودی‌ها و خروجی‌های نهایی
- تعریف دقیق زیرمجموعه‌ی پشتیبانی‌شده‌ی C
- تعریف موارد پشتیبانی‌نشده
- تعریف قراردادهای ساده‌کننده برای declaration، array، pointer و struct
- ثبت ریسک‌های Scope
- ساخت `docs/supported_c_subset.md`
- ساخت Checklist اولیه
- دریافت تأیید کاربر پیش از تغییر وضعیت به `[x]`

### [x] 0.2 — محیط Python و Repository

- ساخت ساختار اولیه‌ی پروژه بدون فایل خالی غیرضروری
- ساخت Virtual Environment
- ساخت `pyproject.toml`
- تنظیم `pytest`
- ساخت Package اولیه
- ساخت CLI اولیه با `--help`
- ساخت اولین تست
- ساخت `README.md` اولیه
- اجرای واقعی تست‌ها

### [x] 0.3 — مدل‌های Core

- `SourcePosition`
- `SourceSpan`
- `Token`
- `Diagnostic`
- `Severity`
- Type Hint و dataclass
- تست line، column و offset
- تست Span انتهای exclusive

### [x] Phase Gate 0

- Scope تأییدشده
- محیط قابل‌نصب
- CLI اولیه قابل‌اجرا
- Core modelها تست‌شده
- تأیید صریح کاربر برای ورود به Phase 1

## Phase 1 — Lexer، Parser و Syntax Highlighting

### [x] 1.1 — مشخصات Tokenها و قوانین Lexer

- توسعه‌ی تنها تعریف مرکزی `TokenKind`
- Tokenهای عمومی، Literal، Comment و Preprocessor Directive
- `KEYWORDS` و TokenKind مستقل هر Keyword
- `TYPE_KEYWORDS`
- `OPERATORS` و `DELIMITERS`
- جدول‌های read-only
- ترتیب قطعی Longest Match
- مستند `docs/token_specification.md`
- حفظ تمام تست‌های Phase 0
- تست `<=`، `==`، `++` و `->`
- بدون کلاس Lexer یا Tokenization واقعی
- تأییدشده با تست محلی کاربر

### [x] 1.2 — پیاده‌سازی Lexer و Error Recovery

- خواندن Source
- نگهداری line، column و offset
- تولید Tokenها
- Integer ده‌دهی، شانزده‌شانزدهی و دودویی
- Float
- String و Character
- Operator و Delimiter
- Comment
- Preprocessor Directive
- EOF
- Invalid Character
- Unterminated String
- Unterminated Character
- Unterminated Block Comment
- ادامه‌ی تحلیل بعد از خطا
- گزارش چند خطا در یک فایل
- جلوگیری از Loop بی‌نهایت
- تست ورودی معتبر و نامعتبر

### [x] 1.3 — Grammar و AST

- EBNF کامل در `grammar/c_subset.ebnf`
- Grammar بدون Left Recursion
- تقدم و Associativity Operatorها
- AST Nodeهای Declaration
- AST Nodeهای Statement
- AST Nodeهای Expression
- Literal و Identifier
- SourceSpan و type annotation اولیه
- AST Printer
- تست AST برای `1 + 2 * 3`

### [x] 1.4 — Parser و Panic-mode Recovery

- Declaration و Function Definition
- Statement
- Expression
- Function Call
- Array Access
- Member Access با `.` و `->`
- Panic-mode recovery
- Synchronization روی `;`، `}` و Keyword مناسب
- ادامه‌ی Parse پس از Syntax Error
- تست Happy Path و Error Path

### [x] 1.5 — Syntax Highlighter و CLI

- Highlight مبتنی بر Token و AST
- تمایز Function و Variable
- خروجی ANSI
- خروجی HTML/CSS مستقل
- حفظ دقیق Whitespace
- Escape امن HTML
- نمایش Error Token

### [x] Phase Gate 1

- Lexer، Parser، Grammar و AST
- Lexer و Parser Error Recovery
- ANSI و HTML
- ورودی معتبر و نامعتبر
- Integration Test
- تأیید صریح کاربر برای ورود به Phase 2

## Phase 2 — Semantic Analysis و Intellisense

### [x] 2.1 — Symbol Table و Scope

- Global، Function، Block و Struct Scope
- Symbolهای Variable، Parameter، Function، Struct و Field
- Lookup داخلی به خارجی
- Namespaceهای Ordinary، Tag و Field
- Built-inهای `printf` و `puts`
- Scope Tree و `scope_at`
- شناسه‌های قطعی و State مستقل
- آماده‌ی تست Ubuntu کاربر

### [x] 2.2 — Name Resolution و Reference Tracking

- Two-pass Declaration Collection و Resolution
- Forward Function Call
- Duplicate، Shadowing و Undefined Symbol
- Prototype سازگار و ناسازگار
- Referenceهای READ، WRITE، READ_WRITE، CALL، TYPE_REFERENCE و MEMBER_ACCESS
- آماده‌ی تست Ubuntu کاربر

### [x] 2.3 — Type System و Semantic Analysis

- Primitive، Pointer، Array، Struct، Function، Unknown و Error Type
- Type Checking کامل Expressionهای Scope
- Function Call، Return و Initializer Checking
- Numeric Widening و Narrowing
- Initialization Tracking ساختاری
- Unused Variable و Parameter
- آماده‌ی تست Ubuntu کاربر

### [x] 2.4 — Diagnostic System

- Pipeline مشترک Lexer، Parser و Semantic
- file، line، column و length
- مرتب‌سازی و Dedup قطعی
- خروجی متنی و JSON معتبر
- Exit Code بر اساس Error
- آماده‌ی تست Ubuntu کاربر

### [x] 2.5 — Completion، Hover، Semantic Highlighting و CLI

- General، Member و Argument-aware Completion
- Prefix و Fuzzy Ranking قطعی
- Hover برای Symbolهای عادی، Field، Struct و Built-in
- Semantic Highlighting همراه Graceful Fallback
- Commandهای `symbols`، `complete`، `hover` و `check --json`
- آماده‌ی تست Ubuntu کاربر

### [x] Phase Gate 2

- Scope و Symbol Table
- Type Checking
- Diagnostics
- Completion و Hover
- تست‌های مثبت، منفی و Integration
- حفظ تست‌های Phase 0 و Phase 1
- بدون قابلیت Phase 3 یا Bonus
- آماده‌ی تست Ubuntu کاربر

## Phase 3 — Program Analysis و IDE Features

### [x] 3.1 — Project Index، Navigation و Multi-file Analysis

- API مستقل Mapping مسیر به Source
- Pathهای Normalized و ترتیب قطعی فایل‌ها
- مدل مستقل Lexer/Parser/Semantic برای هر فایل
- Project Symbol ID مشترک و قطعی
- اتصال Prototype و Definition چندفایلی
- Duplicate Definition و Conflicting Declaration
- Go-to-Definition، Find References و Hover چندفایلی
- Documentation Comment بلافاصله پیش از Declaration
- Built-in بدون Definition ساختگی
- API تک‌فایلی و عدم نشت State
- آماده‌ی تست Ubuntu کاربر

### [x] 3.2 — Control Flow Graph

- `ControlFlowGraph`، `BasicBlock` و `CFGEdge`
- ENTRY و EXIT یکتا و ID قطعی
- کد خطی، `if`، `if/else`، `while` و `for`
- `return`، `break` و `continue`
- Nested Loop و Conditional و چند Return
- حفظ کد پس از Jump برای Unreachable
- Predecessor و Successor متقارن
- Validator داخلی و Reachability محدود
- خروجی text، JSON و DOT بدون وابستگی Graphviz
- عدم تغییر AST و Semantic Model
- آماده‌ی تست Ubuntu کاربر

### [x] 3.3 — Data-flow Analysis و Dead Code

- Worklist Solver قطعی تا Fixed Point
- State مبتنی بر Symbol ID
- Definite Assignment به‌صورت Forward Must-analysis
- Live Variable به‌صورت Backward May-analysis
- Parameter و Global مقداردهی‌شده
- Branch، Loop، Break و Continue
- Unreachable Block و Statement پس از Jump
- Unused Variable، Dead Assignment و Missing Return
- حفظ Side Effect فراخوانی در RHS
- Dedup با Diagnosticهای Phase 2
- آماده‌ی تست Ubuntu کاربر

### [x] 3.4 — Call Graph

- Nodeهای Defined، Built-in و External
- Edge مستقیم همراه تمام Call Siteها
- Direct Callee و Caller و Reachability دوطرفه
- Direct و Mutual Recursion
- SCC قطعی با Tarjan
- Entry پیش‌فرض `main` و Entry سفارشی
- Dead Function از Entry
- خروجی text، JSON و DOT
- Function Pointer و Indirect Call خارج از Scope
- آماده‌ی تست Ubuntu کاربر

### [x] 3.5 — Safe Rename، CLI و REPL

- Rename مبتنی بر Source Location و Symbol ID
- Identifier، Keyword، Conflict و Capture/Shadowing Check
- Namespaceهای Ordinary، Tag و Field
- Rename Variable، Parameter، Function، Struct و Field
- Comment، String، Substring و Symbol هم‌نام دست‌نخورده
- Unified Diff و Dry-run پیش‌فرض
- بازتحلیل کامل پیش از Apply
- Stage، Replace اتمیک و Rollback تست‌شده
- تمام Commandهای Phase 1 و Phase 2 حفظ‌شده
- `project-check`، `goto-def`، `find-refs` و `show-cfg`
- `callgraph`، `dead-code` و `rename`
- REPL با Stream تزریقی و خروج کنترل‌شده
- Example Project چندفایلی
- آماده‌ی تست Ubuntu کاربر

### [x] Phase Gate 3

- اجرای تمام قابلیت‌های الزامی از طریق CLI
- تست چند فایل نمونه
- تست Integration کامل
- مستندات معماری، الگوریتم‌ها، محدودیت‌ها و Usage
- حفظ تمام ۱۵۴ تست قبلی
- Project Index، Navigation، CFG و Data-flow
- Call Graph، Recursion، SCC و Dead Function
- Rename Preview، Apply، Conflict و Rollback
- خروجی‌های قطعی و ورودی خراب بدون Traceback خام
- بدون قابلیت Bonus
- آماده‌ی تست Ubuntu کاربر

## Bonus زیرساختی

### [x] B1 — Coverage حداقل ۸۰٪

- `pytest-cov` در Dependencyهای توسعه
- Line و Branch Coverage
- Gate قطعی `80%` در `pyproject.toml`
- گزارش Terminal، XML و HTML
- Targetهای `coverage` و `coverage-html` در Makefile
- مستند `docs/coverage.md`
- آمادهٔ اجرای محلی کاربر

### [x] B2 — Docker

- Dockerfile چندمرحله‌ای
- Runtime غیرـRoot و بدون Dependencyهای تست
- Test Stage مستقل
- `.dockerignore` کامل
- Build، Smoke و Test Target در Makefile
- تست ساختاری و مستند `docs/docker.md`
- نیازمند اجرای واقعی Docker روی Ubuntu کاربر

### [x] B3 — GitHub Actions CI/CD

- اجرای Push، Pull Request و دستی
- Matrix روی Python 3.10 و 3.12
- Compile و تمام تست‌ها
- Coverage Gate و Artifactهای Coverage/Highlight
- Permission حداقلی و بدون Secret Hard-code
- مستند `docs/ci_cd.md`
- نیازمند Push و Run واقعی GitHub

### [x] GitHub Pages

- Site ایستای Coverage، Highlight و README
- Build محلی با Makefile
- Workflow مستقل Build و Deploy
- Permission حداقلی و Concurrency
- مستند `docs/github_pages.md`
- نیازمند انتشار واقعی GitHub

### [x] Bonus Gate

- Regression کامل Phase 0 تا Phase 3
- Coverage حداقل ۸۰٪
- تست‌های ساختاری Docker، CI و Pages
- Site محلی و لینک‌های داخلی معتبر
- Archive بدون Cache، Coverage و Site تولیدشده
- Docker و سرویس‌های GitHub تا اجرای کاربر در وضعیت بررسی می‌مانند

### [] Bonusهای پیشرفته خارج از Scope

- Multi-language و تشخیص خودکار زبان
- Preprocessor Expansion
- Incremental Parsing
- Dominator و Dominance Frontier
- SSA
