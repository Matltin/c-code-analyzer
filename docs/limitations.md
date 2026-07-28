# محدودیت‌های پروژه

## وضعیت

این سند محدودیت‌های تأییدشده‌ی `c-code-analyzer` را ثبت می‌کند. جزئیات کامل
زیرمجموعه‌ی زبان در `supported_c_subset.md` قرار دارد.

## محدودیت‌های وضعیت فعلی

نسخه‌ی فعلی Phase 0 تا Phase 3 را پوشش می‌دهد:

- ساختار Package و CLI پایه
- مدل‌های مشترک Source، Token و Diagnostic
- Lexer و Error Recovery
- Grammar، AST و AST Printer
- Parser و Panic-mode Recovery
- Highlighter مبتنی بر Token و AST
- Scope، Symbol Table و Name Resolution
- Type Checking و Initialization Tracking
- Completion، Hover و Semantic Highlighting
- Diagnostic متنی و JSON
- CLI و مثال‌های معتبر و نامعتبر
- Project Index، Navigation و Hover چندفایلی
- CFG، Data-flow، Dead Code و Missing Return
- Call Graph، SCC، Recursion و Dead Function
- Safe Rename، CLI نهایی و REPL

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
- Function، Parameter، Variable، Struct، Field، Built-in و Undefined Identifier
  با Semantic Model دسته‌بندی می‌شوند.
- HTML فقط یک فایل مستقل و بدون JavaScript است و ویرایشگر تعاملی نیست.

## محدودیت‌های Type System

- Type System یک مدل آموزشی و ساده‌شده از C است.
- Pointer arithmetic و alias analysis انجام نمی‌شود.
- Array چندبعدی و Variable Length Array وجود ندارد.
- Qualifier و storage class مانند `const`، `volatile`، `static` و `extern`
  پشتیبانی نمی‌شوند.
- `typedef`، `enum`، `union` و bit-field پشتیبانی نمی‌شوند.
- Struct assignment فقط بین Structهای هم‌نام مجاز است.
- Null Pointer Constant فقط Integer Literal برابر صفر است.
- Pointer arithmetic خارج از Scope است.
- Alias Analysis انجام نمی‌شود؛ بنابراین Assignment غیرمستقیم محافظه‌کارانه
  است.
- Assignment غیرمستقیم از طریق Pointer، مقداردهی قطعی Variable مقصد را اثبات
  نمی‌کند.

## استثناهای `printf` و `puts`

هدرهای استاندارد اجرا نمی‌شوند، اما Phase 2 دو Symbol خارجی محدود دارد:

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

Prototype سازگار برای این نام‌ها به همان Built-in Symbol متصل می‌شود و
Prototype ناسازگار Diagnostic می‌دهد. این استثنا به معنی اجرای کتابخانه‌ی
استاندارد نیست.

## محدودیت‌های Completion و Hover

- Completion روی یک فایل و Semantic Model همان فایل کار می‌کند.
- Fuzzy Match فقط Subsequence قطعی است و مدل آماری ندارد.
- Member Completion برای Receiver ساده و Type قابل‌تشخیص طراحی شده است.
- Argument Completion از Signature و Index آرگومان استفاده می‌کند، ولی
  Overload وجود ندارد.
- Hover اطلاعات Definition را نمایش می‌دهد، اما Navigation یا بازکردن فایل
  انجام نمی‌دهد.

## محدودیت‌های تحلیل برنامه

- Call Graph فقط Function Call مستقیم را تحلیل می‌کند.
- Function Pointer در Call Graph وجود ندارد.
- Dynamic Dispatch و OOP خارج از Scope هستند.
- `static`، `extern` و Linkage کامل C خارج از Scope هستند؛ Globalهای هم‌نام
  در Index پروژه مشترک در نظر گرفته می‌شوند.
- Preprocessor اجرا نمی‌شود، پس فایل Header و Macro وارد Project Index
  نمی‌شوند.
- تحلیل Unreachable شرط‌های ثابت را Fold نمی‌کند.
- Dead Assignment مقدار نوشته‌شده را گزارش می‌کند، اما اگر RHS فراخوانی
  Function داشته باشد Side Effect باید حفظ شود.
- Rename Conflict/Capture را محافظه‌کارانه رد می‌کند و ممکن است Rename
  بی‌خطرِ پیچیده‌ای را نپذیرد.
- Entry پیش‌فرض Dead Function، `main` است و از CLI قابل‌تغییر است.
- Apply اتمیک در سطح فایل‌ها با Stage/Backup انجام می‌شود؛ Transaction
  فایل‌سیستم توزیع‌شده نیست.

## موارد خارج از هدف پروژه

- اجرای برنامه‌ی C
- تولید Assembly، Machine Code، Object File یا Executable
- Optimization
- Linker کامل
- LSP، GUI و Web UI تعاملی
- قابلیت‌های Bonus صورت پروژه
