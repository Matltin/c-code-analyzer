# تحلیل Semantic، Scope و Symbol

## Scope Tree

چهار Scope پشتیبانی می‌شود: `GLOBAL`، `FUNCTION`، `BLOCK` و `STRUCT`. هر Scope
شناسه، والد، فرزندان، Span و جدول Symbol مستقل دارد. `scope_at(position)`
داخلی‌ترین Scope شامل Cursor را برمی‌گرداند.

شناسه‌های `scope-0001` و `sym-0001` در هر Analysis از نو و با ترتیب AST
ساخته می‌شوند؛ Mutable Global State وجود ندارد.

## Namespaceهای C

- Ordinary: Variable، Parameter، Function و Built-in
- Tag: نام `struct`
- Field: اعضای همان Struct

بنابراین `struct Item` و Variable با نام `Item` می‌توانند هم‌زمان وجود داشته
باشند. Field فقط از طریق `.` یا `->` Resolve می‌شود.

## Two-pass Resolution

Pass اول Prototype، Function Definition، Global Variable، Struct و Built-in
را جمع می‌کند. Pass دوم Function Bodyها را تحلیل و Referenceها را به Symbol ID
متصل می‌کند. Local Variable فقط از Offset تعریف خودش به بعد دیده می‌شود.

AccessKindها عبارت‌اند از `READ`، `WRITE`، `READ_WRITE`، `CALL`،
`TYPE_REFERENCE` و `MEMBER_ACCESS`.

## Built-in Registry

```c
int puts(char *text);
int printf(char *format, ...);
```

`puts` دقیقاً یک Argument و `printf` حداقل یک Argument از نوع `char *` دارد.
Prototype سازگار به Built-in موجود متصل می‌شود. Prototype ناسازگار Diagnostic
تولید می‌کند. برای Built-inها Definition Span جعلی ساخته نمی‌شود.

## Initialization و Unused

Parameter و Global از ابتدا Initialized هستند. Local دارای Initializer یا
Variable هدف Assignment مقداردهی‌شده محسوب می‌شود. دو Branch کامل `if/else`
با Intersection ترکیب می‌شوند. مقداردهی داخل Loop بعد از Loop تضمین نمی‌شود.

Local Variable خوانده‌نشده و Parameter استفاده‌نشده `INFO` تولید می‌کنند.
Function، Struct و Global Variable در این مرحله Unused گزارش نمی‌شوند.

