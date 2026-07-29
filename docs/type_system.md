# Type System فاز دوم

## مدل‌ها

- `PrimitiveType`: `char`، `int`، `float`، `double` و `void`
- `PointerType`
- `ArrayType`
- `StructType`
- `FunctionType`
- `UnknownType`
- `ErrorType`

Typeها immutable، قابل مقایسه و دارای نمایش متنی قطعی هستند. AST فاز اول
بازنویسی نشده است؛ `SemanticModel.type_of(node)` نوع را از Side Table
برمی‌گرداند.

## Literalها و تبدیل

| Literal | Type |
|---|---|
| Integer | `int` |
| Float بدون `f` | `double` |
| Float با `f` | `float` |
| Character | `char` |
| String | `char *` |

Widening به ترتیب `char -> int -> float -> double` مجاز است. Narrowing
`WARNING` و تبدیل ناسازگار `ERROR` تولید می‌کند. Integer Literal صفر می‌تواند
Null Pointer Constant باشد.

## Expression و Lvalue

Unary، Arithmetic، Comparison، Logical، Assignment، Compound Assignment،
Call، Index، `.` و `->` بررسی می‌شوند. Variable، Array Element، Dereference و
Struct Field lvalue هستند. Assignment به Literal خطاست.

Comparison و Logical نتیجه‌ی `int` دارند. Pointer Arithmetic خارج از Scope
است.

## Function و Initializer

تعداد و Type Argumentها، Return و Signature بررسی می‌شوند. Initializer ساده،
Array یک‌بعدی و Struct flat پشتیبانی می‌شود. تعداد عنصر بیشتر از اندازه‌ی
Array یا Fieldهای Struct خطاست.

تحلیل «وجود Return در همه‌ی مسیرها» به CFG فاز سوم موکول شده است.

