# الگوریتم‌های فاز اول تا سوم

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

## Two-pass Resolution

در Pass اول Functionها، Prototypeها، Global Variableها، Struct Tagها و
Built-inها جمع‌آوری می‌شوند. در Pass دوم Bodyها از Scope داخلی به والد Resolve
می‌شوند. این ترتیب Forward Function Call را ممکن می‌کند. هر Reference با
`symbol_id` و `AccessKind` ثبت می‌شود.

## Type Checking

Type Expressionها در Side Table ذخیره می‌شوند. تبدیل عددی با ترتیب
`char -> int -> float -> double` بررسی می‌شود. `ErrorType` و `UnknownType`
از تولید خطاهای زنجیره‌ای جلوگیری می‌کنند.

## Initialization Tracking

هشدار ساختاری Phase 2 حفظ شده و Phase 3 State قطعی را از CFG محاسبه می‌کند.

## Completion Ranking

ابتدا Scope داخلی و سپس والدها پیمایش می‌شوند. نام Shadowشده فقط یک بار دیده
می‌شود. Prefix Match قبل از Fuzzy Subsequence، Type سازگار قبل از ناسازگار و
Scope نزدیک‌تر قبل از Scope دورتر مرتب می‌شود. کلید نهایی شامل نام و Symbol ID
است تا نتیجه قطعی باشد.

## Project Index

فایل‌ها پس از Normalization با Path مرتب تحلیل می‌شوند. Function Prototype
و Definition سازگار بر اساس Namespace، نام و Function Type به یک Project
Symbol متصل می‌شوند. بقیه‌ی Symbolها شناسه‌ی مجزای Scope-aware دارند.

## CFG

Builder ساختاری از انتهای Sequence به ابتدا حرکت می‌کند. این روش Target بعدی
هر Statement را مشخص نگه می‌دارد و کد پس از Jump را به‌صورت Block جدا ولی
Unreachable حفظ می‌کند. ENTRY و EXIT یکتا هستند.

## Worklist و Data-flow

Worklist ترتیب ثابت Blockها را تا Fixed Point تکرار می‌کند:

```text
Definite IN[B]  = intersection(OUT[P] for P in predecessors(B))
Definite OUT[B] = IN[B] union DEF[B]

Live OUT[B] = union(IN[S] for S in successors(B))
Live IN[B]  = USE[B] union (Live OUT[B] - DEF[B])
```

Definite Assignment یک Forward Must-analysis و Liveness یک Backward
May-analysis است. Stateها فقط Symbol ID هستند.

## Call Graph

Reachability با BFS قطعی و Callerهای Transitive با Reverse Graph محاسبه
می‌شوند. برای Cycle و Recursion از Tarjan استفاده شده؛ هر Node و Edge فقط
Function Call مستقیم Resolveشده را نشان می‌دهد.

## Safe Rename

Editها از Offset بزرگ به کوچک اعمال می‌شوند. ابتدا نام و Conflict/Capture
بررسی، سپس Sourceهای جدید در حافظه ساخته و Project دوباره تحلیل می‌شود. CLI
همه‌ی فایل‌های موقت را پیش از `os.replace` آماده می‌کند و در خطای میانی از
Backupهای کنار فایل برای Rollback استفاده می‌کند.
