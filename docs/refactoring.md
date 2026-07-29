# Safe Rename

`plan_rename` API خالص است: Project، File، Line، Column و نام جدید را می‌گیرد
و بدون File Write، Editها، Source Mapping جدید و Unified Diff می‌دهد.

اعتبارسنجی شامل Rule شناسه ASCII پروژه، Keyword نبودن، Conflict همان
Namespace/Scope و کنترل محافظه‌کارانه Capture/Shadowing است. Namespaceهای
Ordinary، Struct Tag و Field جدا هستند. Built-in Rename نمی‌شود.

Definition، Declaration و Referenceهای دقیق همان Symbol ID با Offset/Span
تغییر می‌کنند. Comment، String، Substring و Symbol هم‌نام Scope دیگر دست‌نخورده
می‌مانند. Editهای هر فایل از Offset بزرگ به کوچک اعمال می‌شوند.

پیش از موفقیت Plan، Mapping جدید دوباره تحلیل می‌شود و Rename نباید Error
جدید بسازد. CLI پیش‌فرض Dry-run است و فقط `--apply` می‌نویسد.

Apply اتمیک:

1. همهٔ فایل‌های جدید کنار مقصد Stage می‌شوند.
2. Backup همهٔ مقصدها ساخته می‌شود.
3. Replaceهای اتمیک انجام می‌شوند.
4. در خطای میانی، مقصدهای تغییرکرده از Backup بازیابی می‌شوند.
5. فایل‌های موقت پاک می‌شوند.

Staging Failure و Mid-replace Failure با Writer/Replacer تزریقی تست شده‌اند.

