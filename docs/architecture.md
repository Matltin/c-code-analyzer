# معماری فاز اول

```text
Source
  -> Lexer
  -> Token Stream + Lexer Diagnostics
  -> Parser
  -> AST + Parser Diagnostics
  -> AST-aware Highlighter
  -> ANSI یا HTML
```

وابستگی‌ها یک‌طرفه‌اند:

```text
core <- lexer <- parser + ast <- rendering <- cli
```

- Core مدل‌های Source، Token و Diagnostic را نگه می‌دارد.
- Lexer Source را به Token تبدیل می‌کند.
- Parser Trivia را در نمای خودش حذف و AST تولید می‌کند.
- AST نام‌ها و Nodeها را با Span دقیق نگه می‌دارد.
- Rendering نقش Identifierها را از AST و بقیه‌ی دسته‌ها را از Token می‌گیرد.
- CLI فقط این اجزا را هماهنگ می‌کند.

هیچ Semantic Analyzer یا Type Checker در فاز اول وجود ندارد.

