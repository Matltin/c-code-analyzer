# زیرمجموعه‌ی پشتیبانی‌شده‌ی C

## وضعیت سند

- پروژه: `c-code-analyzer`
- مرحله: `0.1 — تثبیت Scope`
- وضعیت: `[x] تأییدشده`
- زبان پیاده‌سازی: Python
- زبان هدف: یک زیرمجموعه‌ی آموزشی و مستندشده از C

این ابزار کامپایلر کامل C نیست و ادعا نمی‌کند با یکی از استانداردهای کامل
زبان C سازگار است. هدف پروژه، پیاده‌سازی Front-End کامپایلر و چند قابلیت پایه‌ی
IDE برای مجموعه‌ای کنترل‌شده از ساختارهای C است.

## هدف پروژه

ورودی پروژه یک یا چند فایل متنی C است. ابزار باید کد را بدون اجراکردن آن:

1. به Token تبدیل کند.
2. طبق Grammar پروژه Parse کند و AST بسازد.
3. Scope، Symbol و Type را تحلیل کند.
4. خطاهای lexical، syntactic و semantic را گزارش کند.
5. خروجی رنگی ANSI و HTML تولید کند.
6. قابلیت‌های Completion، Hover، Navigation و Safe Rename را ارائه دهد.
7. CFG، تحلیل Data-flow و Call Graph بسازد.

تولید Assembly، Machine Code، فایل Object یا اجرای برنامه‌ی C جزو هدف نیست.

## قرارداد موقعیت در Source

تمام Tokenها، Nodeهای AST، Diagnosticها، Symbolها و Referenceها باید
`SourceSpan` داشته باشند.

- `line`: یک‌مبنا؛ اولین خط شماره‌ی `1` است.
- `column`: یک‌مبنا؛ اولین ستون شماره‌ی `1` است.
- `offset`: صفرمبنا؛ اولین کاراکتر Offset برابر `0` دارد.
- `end`: انتهای Span به‌صورت exclusive ذخیره می‌شود.
- `file`: مسیر یا نام فایل ورودی را نگه می‌دارد.

این قرارداد در تمام Pipeline ثابت می‌ماند.

## ورودی‌های نهایی

- یک فایل متنی با پسوند `.c`
- چند فایل `.c` برای قابلیت‌های Phase 3
- متن Source به‌همراه نام مجازی فایل در تست‌های واحد
- موقعیت Cursor به‌شکل `file + line + column` برای قابلیت‌های IDE
- نام جدید برای عملیات Rename

Encoding ورودی `UTF-8` است، اما Identifierهای زبان هدف فقط ASCII هستند.

## خروجی‌های نهایی

- Token Stream قابل‌خواندن و JSON
- AST متنی و JSON
- Diagnostic متنی و JSON
- Source رنگی در Terminal با ANSI
- فایل HTML/CSS مستقل و بدون JavaScript
- Symbol Table، Completion List و Hover Information
- نتیجه‌ی Go-to-Definition و Find-All-References
- CFG و Call Graph در قالب JSON یا DOT
- گزارش Dead Code و Data-flow
- Unified Diff برای Rename و امکان اعمال اتمیک آن

## Tokenهای پشتیبانی‌شده

نام رسمی `TokenKind`ها، جدول‌های ثابت و تصمیم‌های طراحی Lexer در
`docs/token_specification.md` ثبت شده‌اند.

### Keywordها

Keywordهای زیر رزروشده‌اند:

```text
int float double char void
struct
if else while for
return break continue
```

کلمه‌ی رزروشده هرگز به‌صورت Identifier تولید نمی‌شود.

### Identifier

```regex
[a-zA-Z_][a-zA-Z0-9_]*
```

Identifier یونیکد پشتیبانی نمی‌شود.

### Literalها

- Integer ده‌دهی: `0`, `42`, `123`
- Integer شانزده‌شانزدهی: `0x2A`, `0XFF`
- Integer دودویی: `0b1010`, `0B11`
- Float ساده یا نمایی: `3.14`, `.5`, `.5f`, `1.`, `1.0e-5`, `2E3`
- Character: `'a'`, `'\n'`, `'\''`
- String: `"hello"`, `"line\n"`

پشتیبانی `0b` یک افزونه‌ی آموزشی این پروژه است و به معنی پشتیبانی از کل C23
نیست. پسوند `f` یا `F` برای Float پشتیبانی می‌شود؛ پسوندهای Integer مانند
`U`، `L` و `LL` در نسخه‌ی پایه پشتیبانی نمی‌شوند.

Escapeهای پایه:

```text
\n \t \r \0 \\ \' \"
```

Stringهای چندبخشی مجاور، Stringهای wide و universal escapeها پشتیبانی
نمی‌شوند.

### Operatorها

Operatorهای پایه:

```text
=  +=  -=  *=  /=  %=
||  &&
==  !=
<  <=  >  >=
++  --
+  -  *  /  %
!  &
.  ->
```

نکته: `+`، `-`، `*` و `&` با توجه به جایگاه می‌توانند نقش متفاوت داشته
باشند. Parser نقش unary یا binary آن‌ها را مشخص می‌کند.

### Delimiterها

```text
( ) { } [ ] ; ,
```

### Commentها

- تک‌خطی از `//` تا قبل از Newline
- چندخطی از `/*` تا اولین `*/`
- Comment چندخطی تو در تو پشتیبانی نمی‌شود، چون در C استاندارد نیز مجاز نیست.
- Comment به‌صورت Token نگه داشته می‌شود تا Highlighter بتواند Source را دقیق
  بازسازی کند، ولی Parser آن را نادیده می‌گیرد.

### Preprocessor Directive

اگر پس از Whitespace ابتدای خط، اولین کاراکتر `#` باشد، متن تا انتهای همان خط
یک `PREPROCESSOR` Token است؛ مانند:

```c
#include <stdio.h>
#define MAX 10
```

Directive فقط تشخیص و Highlight می‌شود. فایل include خوانده نمی‌شود و Macro
تعریف یا Expand نمی‌شود.

### Whitespace، INVALID و EOF

- Whitespace Token عمومی تولید نمی‌کند؛ Lexer موقعیت‌ها را به‌روز می‌کند و
  Renderer با استفاده از Spanها و Source اصلی فاصله‌ها را حفظ می‌کند.
- کاراکتر ناشناخته یک `INVALID` Token و یک Diagnostic ایجاد می‌کند.
- پایان ورودی همیشه یک `EOF` Token دارد.
- Lexer در ورودی نامعتبر Crash نمی‌کند و بعد از خطا ادامه می‌دهد.
- Longest Match الزامی است؛ برای نمونه `<=`، `==`، `++` و `->` هرکدام یک
  Token هستند.

## Grammar سطح بالا

Grammar دقیق Phase 1 در `grammar/c_subset.ebnf` قرار دارد. این بخش مرزهای
قطعی Scope را توضیح می‌دهد و فایل EBNF مرجع نحوی Parser است.

### Typeها

Typeهای پایه:

```text
int
float
double
char
void
struct Name
```

Typeهای ترکیبی پایه:

- Pointer با حداکثر یک سطح، مانند `int *p` یا `struct Point *next`
- Array یک‌بعدی، مانند `int values[10]`
- Function Type شامل Return Type و فهرست Parameterها

`void` برای Variable یا Field مجاز نیست و فقط برای Return Type، فهرست
Parameter خالی به‌شکل `void` و Pointer نوع `void *` قابل استفاده است.

### Declaration متغیر

نمونه‌های مجاز:

```c
int count;
double price = 2.5;
char *message = "hello";
int values[3] = {1, 2, 3};
struct Point p = {1, 2};
```

محدودیت‌های ساده‌کننده:

- در هر Declaration فقط یک نام تعریف می‌شود؛ `int a, b;` پشتیبانی نمی‌شود.
- Declaration می‌تواند global، local یا field باشد.
- Array فقط یک‌بعدی است.
- اندازه‌ی Array باید Integer Literal مثبت باشد؛ expression عمومی مجاز نیست.
- Initializer لیستی فقط یک‌سطحی است و designatorهایی مثل `.x = 1` ندارد.
- Variable Length Array پشتیبانی نمی‌شود.

### Function

Prototype و Definition مستقیم پشتیبانی می‌شوند:

```c
int add(int left, int right);

int add(int left, int right) {
    return left + right;
}
```

محدودیت‌ها:

- Function Call فقط به یک Function نام‌دار انجام می‌شود.
- Function Pointer پشتیبانی نمی‌شود.
- Parameter باید Type مشخص داشته باشد.
- `void f(void)` و `void f()` هر دو به معنی فهرست Parameter خالی در همین
  زیرمجموعه هستند.
- تعریف Function تو در تو پشتیبانی نمی‌شود.
- Variadic Parameter مانند `...` پشتیبانی نمی‌شود.
- سبک قدیمی K&R و implicit `int` پشتیبانی نمی‌شود.

### Block و Scope

- هر `{ ... }` یک Block و یک Scope lexical می‌سازد.
- Function یک Scope برای Parameterها و Body دارد.
- `struct` یک Scope برای Fieldها دارد.
- Shadowing مجاز است ولی Warning تولید می‌کند.
- تعریف تکراری در یک Scope خطا است.

### Statementها

Statementهای پشتیبانی‌شده:

- Block
- Variable Declaration
- Expression Statement
- `if` و `if/else`
- `while`
- `for`
- `return`
- `break`
- `continue`
- Empty Statement یعنی `;`

نمونه:

```c
for (int i = 0; i < 10; i++) {
    if (i == 5) {
        continue;
    }
}
```

محدودیت‌ها:

- بخش init در `for` می‌تواند یک Declaration یا Expression باشد.
- سه بخش `for` می‌توانند در صورت معتبر بودن Grammar خالی باشند.
- `break` و `continue` فقط داخل Loop معتبرند.
- `else` به نزدیک‌ترین `if` بدون `else` متصل می‌شود.

### Expressionها و تقدم

Expressionهای پشتیبانی‌شده از تقدم کمتر به بیشتر:

| سطح | Operator / Construct | Associativity |
| --- | --- | --- |
| Assignment | `=`, `+=`, `-=`, `*=`, `/=`, `%=` | راست |
| Logical OR | `||` | چپ |
| Logical AND | `&&` | چپ |
| Equality | `==`, `!=` | چپ |
| Relational | `<`, `<=`, `>`, `>=` | چپ |
| Additive | `+`, `-` | چپ |
| Multiplicative | `*`, `/`, `%` | چپ |
| Prefix Unary | `+`, `-`, `!`, `&`, `*`, `++`, `--` | راست |
| Postfix | call، index، `.`, `->`, `++`, `--` | چپ |
| Primary | literal، identifier، `(expression)` | — |

بنابراین:

```c
int x = 1 + 2 * 3;
```

باید به‌صورت `1 + (2 * 3)` Parse شود.

سمت چپ Assignment فقط می‌تواند یک lvalue معتبر باشد: Variable، Array Index،
Dereference یا Member Access.

موارد expression که پشتیبانی نمی‌شوند:

- Operator سه‌تایی `?:`
- Comma Operator
- Cast
- `sizeof`
- Bitwise binary operators و shiftها
- Compound Literal
- Generic Selection

### Array و Indexing

موارد پایه:

```c
int values[3];
values[0] = 10;
int first = values[0];
```

- فقط Array یک‌بعدی پشتیبانی می‌شود.
- Index باید Type عدد صحیح داشته باشد.
- Array چندبعدی، slice و pointer arithmetic پشتیبانی نمی‌شود.
- Array assignment کلی مانند `a = b` مجاز نیست.

### Pointer

موارد پایه:

```c
int value = 10;
int *ptr = &value;
int copy = *ptr;
```

- حداکثر یک سطح Pointer پشتیبانی می‌شود.
- Address-of و Dereference پشتیبانی می‌شوند.
- `->` برای Pointer به Struct پشتیبانی می‌شود.
- Pointer arithmetic پشتیبانی نمی‌شود.
- Function Pointer پشتیبانی نمی‌شود.
- مقدار Integer Literal برابر `0` می‌تواند Null Pointer Constant باشد.
- Dereference واقعی اجرا نمی‌شود؛ فقط Type Checking ایستا انجام می‌شود.

### Struct

موارد پایه:

```c
struct Point {
    int x;
    int y;
};

struct Point p = {1, 2};
int x = p.x;
```

- فقط `struct` نام‌دار پشتیبانی می‌شود.
- تعریف `struct` فقط در سطح global انجام می‌شود.
- Field می‌تواند Type پایه، Pointer یک‌سطحی یا Array یک‌بعدی داشته باشد.
- دسترسی با `.` و `->` پشتیبانی می‌شود.
- Initializer ترتیبی و یک‌سطحی پشتیبانی می‌شود.
- Anonymous struct، nested inline struct و flexible array member پشتیبانی
  نمی‌شوند.

## قواعد معنایی پایه

### Name Resolution

- Lookup از Scope داخلی به خارجی انجام می‌شود.
- Declarationهای top-level در Pass اول جمع‌آوری می‌شوند.
- Body تابع‌ها در Pass دوم تحلیل می‌شود.
- استفاده از نام تعریف‌نشده خطا است.
- Prototype اجازه‌ی فراخوانی Function خارجی یا Function تعریف‌شده در فایل
  دیگر را می‌دهد.

### Type Checking

ترتیب ساده‌ی widening عددی:

```text
char -> int -> float -> double
```

- widening مجاز است.
- narrowing مانند `double` به `int` Warning می‌دهد.
- Float Literal بدون پسوند Type برابر `double` و با پسوند `f` یا `F` Type
  برابر `float` دارد.
- Assignment میان عدد و Pointer خطا است، به‌جز Literal صفر برای Null Pointer.
- عملگرهای حسابی روی Typeهای عددی کار می‌کنند.
- `&&`، `||` و `!` Operand scalar می‌پذیرند و نتیجه‌ی `int` دارند.
- مقایسه‌های ترتیبی برای Typeهای عددی هستند.
- `==` و `!=` برای Typeهای عددی یا Pointerهای سازگار هستند.
- Function Call از نظر تعداد و Type Argumentها بررسی می‌شود.
- Return با Return Type تابع بررسی می‌شود.
- Struct assignment فقط بین دو Struct هم‌نام مجاز است.
- Type هر Expression در AST ثبت می‌شود.

این Type System عمداً ساده‌تر از Type System کامل C است.

## کتابخانه‌ی استاندارد و Functionهای خارجی

هدرها اجرا نمی‌شوند. در نسخه‌ی پایه، Function خارجی فقط زمانی شناخته می‌شود
که Prototype آن در Source موجود باشد:

```c
int puts(char *text);
```

دو استثنای تأییدشده وجود دارد:

- `puts` بدون Prototype صریح نیز با امضای ساده‌ی
  `int puts(char *text)` شناخته می‌شود.
- `printf` بدون Prototype صریح نیز شناخته می‌شود. حداقل Argument اول آن باید
  `char *` باشد و می‌تواند Argumentهای بیشتری دریافت کند. تحلیل Format String،
  تطبیق placeholderها با Argumentها و پشتیبانی عمومی از Functionهای variadic
  انجام نمی‌شود.

این دو نام در Phase 2 به‌عنوان Symbol خارجی ازپیش‌شناخته‌شده وارد Scope
می‌شوند؛ Lexer و Parser رفتار ویژه‌ای برای آن‌ها ندارند. هر Function خارجی
دیگر بدون Definition یا Prototype صریح، Diagnostic مربوط به نام تعریف‌نشده
تولید می‌کند.

## رفتار هنگام خطا

- Lexer برای کاراکتر نامعتبر و Literal یا Comment بسته‌نشده Diagnostic می‌دهد.
- Parser از panic-mode و synchronization روی `;`، `}` و Keywordهای مناسب
  استفاده می‌کند.
- Semantic Analyzer چند خطا را جمع‌آوری می‌کند.
- هیچ مرحله‌ای نباید به‌خاطر ورودی کاربر Crash کند.
- پس از خطا، تحلیل بخش‌های سالم باقی‌مانده ادامه پیدا می‌کند.
- Error Recovery نباید Loop بی‌نهایت ایجاد کند.

## قابلیت‌های IDE در Scope

- Completion برای Symbolهای قابل‌مشاهده در Scope
- Prefix matching و مرتب‌سازی ساده
- Member completion پس از `.` و `->`
- Hover شامل kind، type، signature، scope و definition location
- Go-to-Definition
- Find-All-References با تفکیک read و write
- Rename مبتنی بر `Symbol ID` با conflict و shadowing check
- Unified Diff و اعمال اتمیک Rename

Fuzzy matching پیشرفته، LSP و اتصال مستقیم به Editor خارج از Scope پایه‌اند.

## تحلیل برنامه در Scope

- Project Index یک‌فایلی و چندفایلی
- CFG برای کد خطی، `if/else`، `while`، `for`، `return`، `break` و `continue`
- Definite Assignment
- Live Variable Analysis
- Unreachable Code، Unused Variable و Dead Assignment
- Call Graph برای Function Call مستقیم
- Direct caller/callee
- Reachability
- Direct و Mutual Recursion
- Dead Function از Entry Point به نام `main`
- SCC با Tarjan یا Kosaraju

Call Graph مربوط به Function Pointer یا dispatch پویا خارج از Scope است.

## موارد صریحاً خارج از Scope

- پشتیبانی کامل استاندارد C
- اجرای کد C
- تولید Assembly، Machine Code، Object File یا Executable
- Optimization
- Macro Expansion و اجرای `#include`
- Conditional Compilation
- `typedef`، `enum`، `union` و bit-field
- Qualifierها و storage classها مانند `const`، `volatile`، `static` و `extern`
- Function Pointer و declaratorهای پیچیده
- Variadic Function، به‌جز قرارداد محدود و ازپیش‌شناخته‌شده‌ی `printf`
- Inline Assembly
- `switch`، `case`، `do/while` و `goto`
- Operator سه‌تایی، cast، `sizeof`، comma operator و compound literal
- Bitwise binary operators و shift
- Array چندبعدی و Variable Length Array
- Pointer arithmetic و alias analysis
- کتابخانه‌ی استاندارد C ازپیش‌تعریف‌شده، به‌جز `printf` و `puts`
- Linker semantics کامل
- Generics، OOP و dynamic dispatch
- LSP، GUI و Web UI تعاملی
- تمام قابلیت‌های Bonus صورت پروژه

## CLI هدف در پایان پروژه

نام دقیق Optionها در مرحله‌ی CLI نهایی تثبیت می‌شود، اما Scope شامل commandهای
زیر است:

```text
tokens
ast
check
highlight
symbols
complete
hover
goto-def
find-refs
show-cfg
callgraph
dead-code
rename
```

## ریسک‌های Scope

### ریسک زیاد: Parser مربوط به Declaratorهای C

Declarator کامل C بسیار پیچیده است. محدودکردن هر Declaration به یک نام،
Pointer یک‌سطحی و Array یک‌بعدی، پروژه را قابل‌پیاده‌سازی و قابل‌دفاع می‌کند.

### ریسک زیاد: ترکیب Array، Pointer و Struct

هرکدام به‌تنهایی ساده‌اند، اما ترکیب کامل آن‌ها Type Checker و Grammar را بزرگ
می‌کند. این سند ترکیب‌ها را به Field ساده، Pointer یک‌سطحی و Initializer
یک‌سطحی محدود کرده است.

### ریسک متوسط: چندفایلی و Safe Rename

برای Rename ایمن باید Source Location و Symbol ID از روز اول درست نگهداری
شوند. Text Replacement ساده قابل‌قبول نیست.

### ریسک متوسط: Data-flow

Definite Assignment و Liveness باید روی CFG و با fixed-point iteration انجام
شوند. پیاده‌سازی زودهنگام آن‌ها قبل از پایدارشدن AST و Symbol Table باعث
بازنویسی زیاد می‌شود.

### ریسک زمان‌بندی

حتی این Subset نیز برای فردی که تازه Python را شروع می‌کند بزرگ است. رعایت
ترتیب Phaseها، تست خودکار و توقف بعد از هر بخش برای جلوگیری از انباشته‌شدن
خطا ضروری است.

## تصمیم‌های تأییدشده

1. هر Declaration فقط یک نام دارد.
2. Array فقط یک‌بعدی و Pointer فقط یک‌سطحی است.
3. Initializer آرایه و Struct فقط flat و ترتیبی است.
4. Function خارجی معمولاً به Prototype صریح نیاز دارد.
5. `printf` و `puts` دو استثنای محدود و ازپیش‌شناخته‌شده هستند.
6. هیچ قابلیت Bonus تا پایان سه Phase اصلی وارد Scope نمی‌شود.
