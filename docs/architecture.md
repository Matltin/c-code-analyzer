# معماری تا پایان فاز سوم

```text
Source
  -> Lexer
  -> Token Stream + Lexer Diagnostics
  -> Parser
  -> AST + Parser Diagnostics
  -> Symbol Table + Scope Tree
  -> Name Resolution + Reference Tracking
  -> Type Checking + Semantic Diagnostics
  -> Completion / Hover / Semantic Highlighter
  -> Project Index / Navigation
  -> CFG / Data-flow / Dead Code
  -> Call Graph
  -> Safe Rename Preview / Atomic Apply
  -> CLI، ANSI، HTML یا JSON
```

وابستگی‌ها یک‌طرفه‌اند:

```text
core <- lexer <- parser + ast <- semantic <- project
                                     |       |
                                     v       v
                                   flow   callgraph
                                     \       /
                                      refactor
                                         |
                                        cli / repl
```

- Core مدل‌های Source، Token و Diagnostic را نگه می‌دارد.
- Lexer Source را به Token تبدیل می‌کند.
- Parser Trivia را در نمای خودش حذف و AST تولید می‌کند.
- AST نام‌ها و Nodeها را با Span دقیق نگه می‌دارد.
- Semantic Model بدون تغییر AST، Bindingها و Typeها را در Side Table نگه
  می‌دارد.
- Rendering نقش Identifierها را از Semantic Model می‌گیرد و در صورت ناقص
  بودن تحلیل به اطلاعات AST و Token برمی‌گردد.
- CLI فقط این اجزا را هماهنگ می‌کند.
- Project Index مدل‌های مستقل هر فایل را به Symbol ID مشترک چندفایلی متصل
  می‌کند.
- Flow به AST و Semantic Model فقط برای خواندن وابسته است و آن‌ها را تغییر
  نمی‌دهد.
- Call Graph از Referenceهای `CALL` قطعی استفاده می‌کند و Indirect Call
  حدس نمی‌زند.
- Refactor فقط از Span و Symbol ID استفاده می‌کند و نتیجه‌ی API اصلی
  `Mapping` جدید Sourceها است.

هر اجرای `analyze_source` تمام Stateهای Scope، Symbol، Reference و Type را از
نو می‌سازد؛ بنابراین Mutable Global State یا نشت اطلاعات میان فایل‌ها وجود
ندارد.

تمام خروجی‌های Graph و Index بر اساس Path، Symbol ID و Block ID مرتب می‌شوند.
هر تحلیل Project State تازه می‌سازد و REPL نیز در هر Command Project را از
دیسک بارگذاری می‌کند؛ در نتیجه State میان Projectها نشت نمی‌کند.
