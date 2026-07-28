# Call Graph

هر Function Definition یک Node `defined` است. Built-inها Node `builtin` بدون
Definition فایل و Prototypeهای بدون Definition، Node `external` هستند. Edge
از Caller Symbol ID به Callee Symbol ID است و تمام Call Siteهای آن جفت را
نگه می‌دارد.

Queryها:

- Direct Callees و Direct Callers
- Calleeهای Transitively Reachable با BFS
- Functionهای قادر به رسیدن به هدف با Reverse Graph
- Direct و Mutual Recursion
- Cycle و Strongly Connected Components
- Dead Function نسبت به Entry

SCC با الگوریتم Tarjan و ترتیب Neighbor قطعی محاسبه می‌شود. Component تک‌عضوی
فقط در صورت Self-edge Recursive است. Entry پیش‌فرض `main` است و CLI
`--entry` دارد. نبود Entry یک نتیجه و Exit Code کنترل‌شده است.

Function تعریف‌شده‌ای که از Entry Reachable نیست Dead Function است.
Built-in و External هرگز Dead Function گزارش نمی‌شوند. Indirect Call و
Function Pointer خارج از Scope‌اند و حدس زده نمی‌شوند.

فرمت‌های text، JSON و DOT قطعی‌اند.

