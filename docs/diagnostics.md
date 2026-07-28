# Diagnostic System

Pipeline مشترک، خروجی Lexer، Parser و Semantic را جمع می‌کند. هر Diagnostic
شامل این Fieldهاست:

```text
phase
severity
message
file
line
column
length
```

Severityها `ERROR`، `WARNING` و `INFO` هستند. خروجی ابتدا با File و Offset و
سپس با کلیدهای قطعی مرتب می‌شود. Diagnostic کاملاً تکراری حذف می‌شود، اما
پیام‌های متفاوت دو Phase در یک Span باقی می‌مانند.

`ErrorType` و `UnknownType` از خطاهای زنجیره‌ای بی‌فایده جلوگیری می‌کنند.
Lexer یا Parser Error مانع تحلیل بخش سالم AST نمی‌شود.

## JSON

```bash
python -m c_analyzer check FILE --json
```

خروجی یک Object شامل `diagnostics`، `error_count`، `warning_count` و
`info_count` است. JSON با `ensure_ascii=False` ساخته می‌شود و Unicode-safe
است.

Exit Code در صورت وجود Error برابر ۱ است. Warning یا Info به‌تنهایی Exit Code
صفر دارند. خطای File یا Cursor Exit Code برابر ۲ دارد.

