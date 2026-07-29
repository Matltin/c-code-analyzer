# مشخصات Tokenها و قواعد ثابت Lexer

## وضعیت

- مرحله: `1.1 — مشخصات Tokenها و قوانین Lexer`
- وضعیت: `[x] تأییدشده توسط کاربر`
- مرجع Scope: `docs/supported_c_subset.md`

این سند قرارداد Tokenهایی را تعریف می‌کند که Lexer فاز اول تولید می‌کند.
تعریف قرارداد در بخش ۱.۱ انجام و تأیید شد؛ پیاده‌سازی Scanner مطابق همین
قرارداد در بخش ۱.۲ قرار دارد.

## محل تعریف مرکزی

`TokenKind` فقط یک بار و در فایل زیر تعریف می‌شود:

```text
src/c_analyzer/core/token.py
```

Package مربوط به Lexer از Core استفاده می‌کند:

```text
core <- lexer
```

Core هیچ Import یا وابستگی به Lexer ندارد. این جهت وابستگی از Circular Import
جلوگیری می‌کند و اجازه می‌دهد Parser، Highlighter و سایر بخش‌ها یک
`TokenKind` مشترک داشته باشند.

## Tokenهای عمومی

| TokenKind | کاربرد |
| --- | --- |
| `EOF` | پایان ورودی |
| `INVALID` | بخشی از Source که هیچ Token معتبر نیست |
| `IDENTIFIER` | نام Variable، Function، Struct یا Field |
| `INTEGER_LITERAL` | Literal صحیح در مبناهای پشتیبانی‌شده |
| `FLOAT_LITERAL` | Literal اعشاری یا نمایی |
| `STRING_LITERAL` | متن داخل Double Quote |
| `CHAR_LITERAL` | کاراکتر داخل Single Quote |
| `LINE_COMMENT` | Comment از `//` تا انتهای خط |
| `BLOCK_COMMENT` | Comment از `/*` تا اولین `*/` |
| `PREPROCESSOR_DIRECTIVE` | Directive از `#` ابتدای منطقی خط تا انتهای خط |

قواعد دقیق شکل Literalها و Commentهای بسته‌نشده در `docs/lexer.md` مستند
شده‌اند.

## Keywordها

هر Keyword یک `TokenKind` مستقل دارد:

| Lexeme | TokenKind |
| --- | --- |
| `int` | `KW_INT` |
| `float` | `KW_FLOAT` |
| `double` | `KW_DOUBLE` |
| `char` | `KW_CHAR` |
| `void` | `KW_VOID` |
| `struct` | `KW_STRUCT` |
| `if` | `KW_IF` |
| `else` | `KW_ELSE` |
| `while` | `KW_WHILE` |
| `for` | `KW_FOR` |
| `return` | `KW_RETURN` |
| `break` | `KW_BREAK` |
| `continue` | `KW_CONTINUE` |

نگاشت مرکزی آن‌ها با نام `KEYWORDS` در `lexer/rules.py` قرار دارد.

### Type Keywordها

مجموعه‌ی دقیق `TYPE_KEYWORDS`:

```text
KW_INT
KW_FLOAT
KW_DOUBLE
KW_CHAR
KW_VOID
KW_STRUCT
```

`KW_STRUCT` عضو این مجموعه است، زیرا در Grammar ابتدای Type
`struct Name` را مشخص می‌کند.

### چرا هر Keyword یک TokenKind جدا دارد؟

Parser می‌تواند مستقیماً انتظار `KW_IF` یا `KW_RETURN` داشته باشد و مجبور نیست
بعد از دریافت `IDENTIFIER` دوباره متن آن را مقایسه کند. Highlighter نیز بدون
حدس‌زدن می‌تواند تمام Keywordها و Type Keywordها را دسته‌بندی کند.

Lexer ابتدا شکل Identifier را می‌خواند و سپس `KEYWORDS` تعیین می‌کند که نتیجه
Identifier است یا Keyword.

## Operatorها

هیچ Operator خارج از Scope به جدول اضافه نشده است.

| Lexeme | TokenKind |
| --- | --- |
| `+` | `PLUS` |
| `-` | `MINUS` |
| `*` | `STAR` |
| `/` | `SLASH` |
| `%` | `PERCENT` |
| `=` | `ASSIGN` |
| `+=` | `PLUS_ASSIGN` |
| `-=` | `MINUS_ASSIGN` |
| `*=` | `STAR_ASSIGN` |
| `/=` | `SLASH_ASSIGN` |
| `%=` | `PERCENT_ASSIGN` |
| `==` | `EQUAL_EQUAL` |
| `!=` | `BANG_EQUAL` |
| `<` | `LESS` |
| `<=` | `LESS_EQUAL` |
| `>` | `GREATER` |
| `>=` | `GREATER_EQUAL` |
| `&&` | `LOGICAL_AND` |
| `||` | `LOGICAL_OR` |
| `!` | `LOGICAL_NOT` |
| `++` | `INCREMENT` |
| `--` | `DECREMENT` |
| `&` | `AMPERSAND` |
| `.` | `DOT` |
| `->` | `ARROW` |

یک TokenKind می‌تواند در Grammar چند نقش داشته باشد. برای مثال `STAR` در
ضرب و Dereference استفاده می‌شود و Parser با توجه به Context نقش آن را مشخص
می‌کند.

### چرا `.` Operator است؟

`.` روی Expression سمت چپ عمل می‌کند و Member یک Struct را انتخاب می‌کند.
این رفتار شبیه یک Postfix Operator است، نه یک جداکننده‌ی صرف.

## Delimiterها

| Lexeme | TokenKind |
| --- | --- |
| `(` | `LEFT_PAREN` |
| `)` | `RIGHT_PAREN` |
| `{` | `LEFT_BRACE` |
| `}` | `RIGHT_BRACE` |
| `[` | `LEFT_BRACKET` |
| `]` | `RIGHT_BRACKET` |
| `;` | `SEMICOLON` |
| `,` | `COMMA` |

### چرا `,` Delimiter است؟

Comma Operator در Scope پروژه نیست. `,` فقط آیتم‌های Parameter، Argument و
Initializer را جدا می‌کند؛ بنابراین در این زیرمجموعه Delimiter محسوب می‌شود.

## Longest Match

`OPERATOR_LEXEMES_LONGEST_FIRST` یک `tuple` قطعی است که Operatorها را با این
کلید مرتب می‌کند:

1. طول بیشتر قبل از طول کمتر
2. برای طول برابر، ترتیب الفبایی Lexeme

نمونه‌های تضمین‌شده:

```text
->  before  -
<=  before  <
>=  before  >
==  before  =
!=  before  !
++  before  +
--  before  -
+=  before  +
```

Operatorهای چندکاراکتری باید زودتر بررسی شوند؛ وگرنه برای مثال `<=` به دو
Token اشتباه `<` و `=` شکسته می‌شود. مرتب‌سازی ثانویه‌ی الفبایی باعث می‌شود
خروجی در همه‌ی اجراها Deterministic باشد.

این ترتیب در بخش ۱.۱ تعریف شد و Lexer بخش ۱.۲ مستقیماً برای Scan کردن
Operatorها از آن استفاده می‌کند.

## Whitespace و Newline

Whitespace و Newline به‌عنوان Token خروجی تولید نمی‌شوند، زیرا Parser به
آن‌ها نیاز ندارد. Lexer همچنان آن‌ها را مصرف می‌کند تا `line`،
`column` و `offset` درست محاسبه شوند.

Renderer فاز اول Source اصلی و Span Tokenها را نگه می‌دارد تا فاصله‌ها و
Newlineها بدون ساخت Whitespace Token حفظ شوند.

## Comment

Comment باید Token باشد، زیرا:

- Syntax Highlighter باید متن Comment و Span دقیق آن را رنگ‌آمیزی کند.
- بازسازی وفادار Source به محل Comment نیاز دارد.
- Parser می‌تواند Comment Tokenها را نادیده بگیرد.

## تفاوت `INVALID` و `Diagnostic`

- `INVALID` یک Token است و دقیقاً قسمت نامعتبر Source و Span آن را نگه
  می‌دارد.
- `Diagnostic` پیام، Severity، Phase و محل خطا را برای کاربر توضیح می‌دهد.

در بخش ۱.۲ یک ورودی نامعتبر می‌تواند هم `INVALID` Token و هم Diagnostic ایجاد
کند. این دو خروجی مستقل ولی دارای Span هماهنگ هستند.

## Preprocessor Directive

Preprocessor Directive فقط یک Token می‌شود تا:

- محل و متن آن برای Highlighter حفظ شود.
- Parser بتواند آن را طبق قرارداد پروژه نادیده بگیرد.
- Source Location بدون اجرای Macro ثابت بماند.

اجرای `#include`، Macro Expansion و Conditional Compilation خارج از Scope
هستند.

## جدول‌های مرکزی و مصرف‌کنندگان

| جدول | نوع read-only | مصرف‌کننده |
| --- | --- | --- |
| `KEYWORDS` | `MappingProxyType` | Lexer، Parser و Highlighter |
| `TYPE_KEYWORDS` | `frozenset` | Parser و Highlighter |
| `OPERATORS` | `MappingProxyType` | Lexer و Parser |
| `DELIMITERS` | `MappingProxyType` | Lexer و Parser |
| `OPERATOR_LEXEMES_LONGEST_FIRST` | `tuple` | Lexer |

`MappingProxyType`، `frozenset` و `tuple` مانع تغییر اتفاقی قواعد در Runtime
می‌شوند.

## وضعیت مصرف قرارداد

- Lexer و Error Recovery در بخش ۱.۲ از این قواعد استفاده می‌کنند.
- Grammar و AST در بخش ۱.۳ بر اساس همین `TokenKind`ها تعریف شده‌اند.
- Parser بخش ۱.۴ همان Token Stream مشترک را مصرف می‌کند.
- Highlighter و CLI بخش ۱.۵ برای دسته‌بندی و نمایش Tokenها از همین قرارداد
  استفاده می‌کنند.
- Semantic Analysis فاز دوم نیز همین TokenKind و Spanها را مصرف می‌کند.
