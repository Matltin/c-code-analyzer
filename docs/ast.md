# طراحی Grammar و AST

## Grammar

Grammar رسمی در `grammar/c_subset.ebnf` قرار دارد. برای Recursive Descent:

- Left recursion حذف شده است.
- تکرار Binary Operatorهای چپ‌گرا با `{ ... }` نمایش داده می‌شود.
- Assignment با recursion در سمت راست، right-associative است.
- هر Declaration فقط یک نام دارد.
- Pointer فقط یک `*` و Array فقط یک suffix دارد.
- Initializer List فقط flat است.

## خانواده‌های AST

- `Program`
- `Declaration`
- `Statement`
- `Expression`

هر Node از `ASTNode` ارث می‌برد و `SourceSpan` دارد.

## نام‌های Source-aware

نام Function، Variable، Parameter، Struct و Field در `Name` ذخیره می‌شود.
`Name` علاوه بر متن، Span دقیق همان Identifier را دارد. این تصمیم برای
Highlighter، Symbol Binding، Go-to-Definition و Rename ضروری است.

## اتصال Semantic بدون بازنویسی AST

تمام Nodeها دو فیلد خالی دارند:

```text
inferred_type = None
symbol_id = None
```

این فیلدها برای سازگاری حفظ شده‌اند، اما فاز دوم برای جلوگیری از Mutate کردن
AST پایدار، Type و Binding واقعی را در `SemanticModel` و Side Tableها نگه
می‌دارد. APIهای `type_of(node)` و `symbol_of(node)` اطلاعات را برمی‌گردانند.

## AST Printer

Printer با ترتیب فیلدهای dataclass کار می‌کند و Span و فیلدهای Semantic را
برای خوانایی نمایش نمی‌دهد. خروجی آن قطعی است و در CLI و تست‌ها استفاده
خواهد شد.
