# طراحی Lexer

## API

```python
result = tokenize(source_text, file_name)
result.tokens
result.diagnostics
```

`LexerResult` شامل دو `tuple` است تا نتیجه‌ی یک اجرا پس از تولید تغییر نکند.

## تعریف رسمی Token Classها

| Class | تعریف |
| --- | --- |
| Identifier | `[A-Za-z_][A-Za-z0-9_]*` |
| Decimal Integer | `[0-9]+` |
| Hex Integer | `0[xX][0-9A-Fa-f]+` |
| Binary Integer | `0[bB][01]+` |
| Float | `([0-9]+\.[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?[fF]?` |
| Exponent Float | `[0-9]+[eE][+-]?[0-9]+[fF]?` |
| String | `"([^"\\\n]|\\E)*"` |
| Character | `'([^'\\\n]|\\E)'` |
| Line Comment | `//[^\n]*` |
| Block Comment | `/\* ... \*/`، بدون nesting |
| Preprocessor | `#` در ابتدای منطقی خط تا قبل از Newline |

در جدول بالا `E` یکی از Escapeهای زیر است:

```text
n t r 0 \ ' "
```

## روش Scanner

Lexer یک Scanner دست‌نویس و تک‌گذر است. در هر موقعیت:

1. Whitespace مصرف و موقعیت به‌روز می‌شود.
2. Comment پیش از Operator `/` بررسی می‌شود.
3. `.5` پیش از Operator `.` بررسی می‌شود.
4. Identifier خوانده و سپس با جدول `KEYWORDS` مقایسه می‌شود.
5. Operatorها طبق `OPERATOR_LEXEMES_LONGEST_FIRST` بررسی می‌شوند.
6. اگر هیچ Rule منطبق نبود، یک کاراکتر مصرف و `INVALID` تولید می‌شود.

این ترتیب Keyword Priority و Longest Match را تضمین می‌کند.

## موقعیت Source

- Line و Column از ۱ شروع می‌شوند.
- Offset از صفر شروع می‌شود.
- انتهای Span exclusive است.
- Newline خط را یکی زیاد و Column را روی ۱ قرار می‌دهد.
- Tab دقیقاً یک Source Character و یک Column حساب می‌شود.
- EOF در Offset انتهای Source یک Span صفرطول دارد.

## Comment و Preprocessor

Commentها در Token Stream باقی می‌مانند. Parser آن‌ها را به‌عنوان Trivia
فیلتر می‌کند، اما Highlighter از Span و Lexeme آن‌ها استفاده خواهد کرد.

Preprocessor Directive اجرا یا Expand نمی‌شود. فقط از `#` ابتدای منطقی خط تا
پایان همان خط یک Token تولید می‌شود.

## Error Recovery

برای کاراکتر ناشناخته، Literal بسته‌نشده، Character نامعتبر، Escape نامعتبر،
Comment بسته‌نشده و عدد ناقص:

- حداقل یک کاراکتر مصرف می‌شود.
- `INVALID` Token با Lexeme دقیق ساخته می‌شود.
- یک یا چند Diagnostic با Span همان بخش ساخته می‌شود.
- تحلیل تا EOF یا Token بعدی ادامه پیدا می‌کند.

این قرارداد مانع Loop بی‌نهایت می‌شود و اجازه می‌دهد چند خطا در یک فایل
گزارش شوند.

## ارتباط نظری با DFA

هر Token Class یک زبان منظم است و می‌تواند به NFA و سپس DFA تبدیل شود. ترکیب
Ruleها از اجتماع زبان‌ها ساخته می‌شود؛ حالت پذیرش هر Rule نوع Token را تعیین
می‌کند. در تعارض‌ها ابتدا طول بیشتر و سپس Priority Rule انتخاب می‌شود.

این پروژه جدول DFA تولید نمی‌کند، اما Scanner دست‌نویس همان تصمیم‌ها را
مستقیم در شاخه‌های کوچک پیاده‌سازی می‌کند: وضعیت فعلی Source نقش State را
دارد و `_advance` انتقال روی کاراکتر بعدی است.

## محدودیت‌ها

- Unicode Identifier پشتیبانی نمی‌شود.
- Hex Float و Integer suffixها پشتیبانی نمی‌شوند.
- Comment تو در تو نیست.
- Line continuation داخل String پشتیبانی نمی‌شود.
- Preprocessor اجرا نمی‌شود.

