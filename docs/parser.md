# طراحی Parser

## راهبرد

Parser به‌صورت hand-written Recursive Descent پیاده‌سازی شده است. هر سطح تقدم
Expression یک تابع جدا دارد. Binary Operatorهای معمول با حلقه چپ‌گرا و
Assignment با فراخوانی بازگشتی سمت راست Parse می‌شوند.

## API

```python
parser_result = parse(tokens)
parser_result.ast
parser_result.diagnostics
```

Comment و Preprocessor Directive فقط از نمای داخلی Parser حذف می‌شوند و
Token Stream اصلی Lexer تغییر نمی‌کند.

## Error Recovery

دو روش استفاده می‌شود:

- انتظار نرم برای `)`, `]`, `}` و `;`: Diagnostic تولید می‌شود، اما Token
  بعدی مصرف نمی‌شود تا ساختار سالم بعدی قابل Parse باشد.
- Panic mode برای خطاهای Declaration: Tokenها تا `;`، `}` یا Keywordهای
  Statement جلو برده می‌شوند.

یک کنترل پیشرفت نیز وجود دارد؛ اگر یک دور Parse هیچ Tokenی مصرف نکرد، Parser
یک Token جلو می‌رود. بنابراین ورودی خراب Loop بی‌نهایت ایجاد نمی‌کند.

Parser روی `INVALID` یک `ErrorExpr` می‌سازد و ادامه می‌دهد. AST حاصل می‌تواند
Partial باشد و `ErrorExpr` یا `ErrorStmt` داشته باشد.

## محدودیت

این مرحله فقط Syntax را بررسی می‌کند. معتبر بودن lvalue، Type، Scope،
`break` خارج Loop و موارد معنایی در این Parser بررسی نمی‌شوند.

