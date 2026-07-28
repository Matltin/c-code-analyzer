# Completion، Hover و Semantic Highlighting

## Completion

API، Source و Cursor یک‌مبنایی می‌گیرد و هر Item شامل `label`، `kind`,
`detail`، `sort_order`، `insert_text` و `symbol_id` است.

ترتیب Ranking:

1. Prefix Match
2. Fuzzy Subsequence Match
3. Type سازگار با Argument
4. Scope نزدیک‌تر
5. نام و Symbol ID برای قطعیت

نام Shadowشده از Scope بیرونی دوباره نمایش داده نمی‌شود و Local Variable قبل
از Declaration پیشنهاد نمی‌شود.

## Member و Argument Completion

بعد از `.`، Receiver باید Struct و بعد از `->` باید Pointer-to-Struct باشد.
Fieldها از Field Namespace همان Struct می‌آیند. داخل Argument List، Index
آرگومان و Parameter Type متناظر برای Ranking استفاده می‌شود.

روی کد ناقص مانند `point.` یا `add(val` از Token Context و Partial AST استفاده
می‌شود؛ خطا باعث Exception نمی‌شود.

## Hover

Hover با Span Definition و Reference، نام، Kind، Type، Signature، Scope و
Definition Location را می‌دهد. برای Built-in مقدار Definition برابر
`built-in` است. جای بدون Symbol نتیجه‌ی خالی کنترل‌شده دارد.

## Semantic Highlighting

Function، Call، Variable، Parameter، Struct، Field، Built-in و Undefined
Identifier از Semantic Model مشخص می‌شوند. در صورت ناقص بودن مدل، دسته‌بندی
AST و Token فاز اول حفظ می‌شود. ANSI و HTML همچنان Source را دقیق نگه
می‌دارند.

