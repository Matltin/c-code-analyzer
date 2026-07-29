# REPL فاز سوم

اجرا:

```bash
python -m c_analyzer repl examples/project
```

Commandها:

```text
help
project-check
goto-def FILE LINE COLUMN
find-refs FILE LINE COLUMN
show-cfg FILE FUNCTION
callgraph
dead-code
rename FILE LINE COLUMN NEW_NAME
quit
exit
```

Rename در REPL فقط Preview است و Apply ناخواسته ندارد. برای Apply باید از
CLI با `--apply` استفاده شود. ورودی با `shlex` جدا می‌شود؛ خطای Quote،
Command ناشناخته یا Argument نامعتبر Loop را نمی‌بندد. EOF مانند Exit
کنترل‌شده است.

`run_repl` Input و Output Stream تزریقی می‌پذیرد، پس تست‌ها بدون ورودی
تعاملی واقعی اجرا می‌شوند. خطاهای Command به متن قابل‌فهم تبدیل می‌شوند و
Traceback خام نمایش داده نمی‌شود.

