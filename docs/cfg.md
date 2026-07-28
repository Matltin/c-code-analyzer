# Control Flow Graph

برای هر `FunctionDecl` یک `ControlFlowGraph` با ENTRY و EXIT یکتا ساخته
می‌شود. هر `BasicBlock` ID قطعی، AST Nodeهای مرجع، SourceSpan، Predecessor و
Successor دارد.

EdgeKindها:

- `FALLTHROUGH`
- `TRUE_BRANCH` و `FALSE_BRANCH`
- `LOOP_BACK`
- `BREAK` و `CONTINUE`
- `RETURN`

Statementهای خطی تا حد ممکن در یک Block بیشینه گروه‌بندی می‌شوند. Condition
یک Block مستقل با Edgeهای True/False است. `while` و `for` Back-edge دارند.
کد پس از `return`، `break` یا `continue` حذف نمی‌شود؛ Block آن باقی می‌ماند
ولی از ENTRY Reachable نیست.

`validate_cfg` وجود ENTRY/EXIT، ID تکراری، Target خراب و تقارن
Predecessor/Successor را بررسی می‌کند. `reachable_blocks` از BFS محدود روی
Block IDها استفاده می‌کند، بنابراین Loop باعث توقف‌نکردن تحلیل نمی‌شود.

خروجی‌های text، JSON قابل `json.loads` و DOT متنی وجود دارند. DOT وابستگی
Runtime به Graphviz ندارد.

