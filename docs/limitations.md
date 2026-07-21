# محدودیت‌های پروژه

## وضعیت

این سند محدودیت‌های تأییدشده‌ی `c-code-analyzer` را ثبت می‌کند. جزئیات کامل
زیرمجموعه‌ی زبان در `supported_c_subset.md` قرار دارد.

## محدودیت‌های وضعیت فعلی

نسخه‌ی فعلی Phase 0 و Phase 1 را پوشش می‌دهد:

- ساختار Package و CLI پایه
- مدل‌های مشترک Source، Token و Diagnostic
- Lexer و Error Recovery
- Grammar، AST و AST Printer
- Parser و Panic-mode Recovery
- Highlighter مبتنی بر Token و AST
- CLI و مثال‌های معتبر و نامعتبر

Semantic Analyzer، Type Checker، Symbol Table، Completion، CFG و Call Graph
هنوز پیاده‌سازی نشده‌اند.

## محدودیت‌های Lexer

- Identifier فقط ASCII است.
- Comment چندخطی تو در تو پشتیبانی نمی‌شود.
- پسوندهای Integer مانند `U`، `L` و `LL` پشتیبانی نمی‌شوند.
- Stringهای wide، Unicode escape و String literalهای مجاور پشتیبانی نمی‌شوند.
- Preprocessor Directive فقط Token می‌شود و اجرا نمی‌شود.
- Macro Expansion و پردازش واقعی `#include` وجود ندارد.

## محدودیت‌های Grammar و Parser

- در هر Declaration فقط یک نام مجاز است.
- Declaratorهای پیچیده‌ی C پشتیبانی نمی‌شوند.
- Array فقط یک‌بعدی و با اندازه‌ی ثابت است.
- Pointer فقط یک‌سطحی است.
- Initializer آرایه و Struct فقط flat و ترتیبی است.
- Function Pointer، Function تو در تو و Variadic Function عمومی وجود ندارد.
- `switch`، `do/while` و `goto` خارج از Scope هستند.
- Cast، `sizeof`، Operator سه‌تایی و Comma Operator پشتیبانی نمی‌شوند.
- Bitwise binary operatorها و shiftها پشتیبانی نمی‌شوند.
- Parser فقط Syntax را بررسی می‌کند و lvalue یا Type را اعتبارسنجی نمی‌کند.
- بازیابی خطا AST جزئی با `ErrorExpr` یا `ErrorStmt` تولید می‌کند.

## محدودیت‌های Highlighter

- تشخیص Function Declaration و Function Call مبتنی بر AST است.
- Parameter فقط در محل Declaration به‌طور قطعی شناخته می‌شود؛ تشخیص Reference
  همان Parameter به Symbol Table فاز دوم نیاز دارد.
- HTML فقط یک فایل مستقل و بدون JavaScript است و ویرایشگر تعاملی نیست.

## محدودیت‌های Type System هدف

- Type System یک مدل آموزشی و ساده‌شده از C است.
- Pointer arithmetic و alias analysis انجام نمی‌شود.
- Array چندبعدی و Variable Length Array وجود ندارد.
- Qualifier و storage class مانند `const`، `volatile`، `static` و `extern`
  پشتیبانی نمی‌شوند.
- `typedef`، `enum`، `union` و bit-field پشتیبانی نمی‌شوند.
- Struct assignment فقط بین Structهای هم‌نام مجاز است.
- Null Pointer Constant فقط Integer Literal برابر صفر است.

## استثناهای `printf` و `puts`

هدرهای استاندارد اجرا نمی‌شوند، اما Phase 2 دو Symbol خارجی محدود خواهد داشت:

```c
int puts(char *text);
int printf(char *format, ...);
```

- `puts` دقیقاً یک Argument از نوع `char *` می‌پذیرد.
- `printf` حداقل یک Argument از نوع `char *` می‌پذیرد.
- Argumentهای اضافی `printf` پذیرفته می‌شوند، ولی Format String تحلیل نمی‌شود.
- `...` وارد Grammar عمومی Prototypeها نمی‌شود.
- هیچ Function استاندارد دیگری بدون Prototype یا Definition صریح شناخته
  نمی‌شود.

این استثنا فقط در Semantic Analyzer آینده اعمال می‌شود و به معنی اجرای
کتابخانه‌ی استاندارد نیست.

## محدودیت‌های تحلیل برنامه

- Call Graph فقط Function Call مستقیم را تحلیل می‌کند.
- Function Pointer در Call Graph وجود ندارد.
- Dynamic Dispatch و OOP خارج از Scope هستند.
- Rename باید بر اساس Symbol ID باشد؛ جایگزینی متنی ساده مجاز نیست.
- Entry Point تشخیص Dead Function، تابعی با نام `main` است.

## موارد خارج از هدف پروژه

- اجرای برنامه‌ی C
- تولید Assembly، Machine Code، Object File یا Executable
- Optimization
- Linker کامل
- LSP، GUI و Web UI تعاملی
- قابلیت‌های Bonus صورت پروژه
