# Data-flow و Dead Code

Solverهای Forward و Backward ترتیب قطعی Blockها را تا Fixed Point اجرا
می‌کنند. State فقط `frozenset` از Symbol ID است.

## Definite Assignment

Forward Must-analysis:

```text
IN[entry] = parameters + global variables
IN[B] = intersection(OUT[P] for P in predecessors(B))
OUT[B] = IN[B] union DEF[B]
```

پارامترها مقدار اولیه دارند و Globalها طبق C صفرمقداردهی شده‌اند. مقداردهی
فقط در یک Branch یا فقط در Body حلقه برای مسیر پس از آن کافی نیست.

## Liveness

Backward May-analysis:

```text
OUT[B] = union(IN[S] for S in successors(B))
IN[B] = USE[B] union (OUT[B] - DEF[B])
```

Referenceهای هر Block برای Read/Write با Symbol ID دسته‌بندی می‌شوند.

## Dead Code Report

گزارش شامل Unreachable Block، Statement پس از Jump، Unused Variable، Dead
Assignment، Missing Return و Dead Function است. `x++` به‌عنوان READ_WRITE
Dead Assignment ساده محسوب نمی‌شود. Assignment با Function Call در RHS
می‌تواند مقدار مرده داشته باشد، اما پیام صریحاً حفظ Side Effect را لازم
می‌داند. Missing Return فقط برای Function غیرـvoid و مسیر Fallthrough تا EXIT
گزارش می‌شود.

Diagnosticهای Phase 2 در View ترکیبی تکرار نمی‌شوند. Constant Folding و Alias
Analysis در این فاز انجام نمی‌شوند.

