# الگوریتم‌های فاز اول

## Lexer

Scanner دست‌نویس، تک‌گذر و مبتنی بر Maximal Munch است. جدول مرتب‌شده‌ی
Operatorها، Longest Match را تضمین می‌کند. هر خطا حداقل یک کاراکتر مصرف
می‌کند.

## Parser

Recursive Descent از Grammar بدون left recursion استفاده می‌کند. هر سطح تقدم
تابع جدا دارد. Assignment با recursion راست‌گرا و سایر Binary Operatorها با
حلقه چپ‌گرا ساخته می‌شوند.

## Panic-mode

Synchronization روی `;`، `}`، `if`، `while`، `for`، `return`، `break` و
`continue` انجام می‌شود. انتظار نرم delimiterها اجازه می‌دهد Node ناقص ساخته
و Statement سالم بعدی Parse شود.

## Highlighter

ابتدا AST محل Function، Parameter، Struct و Field را مشخص می‌کند. سپس
TokenKind دسته‌های lexical را تعیین می‌کند. Renderer میان Spanها را مستقیماً
از Source اصلی برمی‌دارد؛ به همین دلیل Whitespace تغییر نمی‌کند.

