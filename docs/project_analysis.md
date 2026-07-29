# تحلیل Project چندفایلی

`analyze_project` یک Mapping از `file_path` به `source_text` می‌گیرد. Pathها
به `/` تبدیل، نسبی و مرتب می‌شوند. برای هر فایل همان Pipeline تک‌فایلی
Lexer، Parser و Semantic اجرا می‌شود و مدل آن فایل مستقل باقی می‌ماند.

Project Index یک `ProjectSymbol` قطعی برای هر Symbol دارد. Function Prototype
و Definition سازگار در فایل‌های مختلف به یک ID متصل می‌شوند. Duplicate
Definition و Declaration ناسازگار Diagnostic فاز Analysis تولید می‌کنند.
Built-inهای `printf` و `puts` Node مشترک دارند، ولی Definition ساختگی فایل
ندارند.

هر Project Reference شامل File، Line، Column، Length و AccessKind است.
Comment و String از Semantic Referenceها نیستند. Documentation Comment فقط
وقتی متصل می‌شود که آخرین Comment بدون متن غیرخالی و بدون خط خالی بلافاصله
پیش از Declaration باشد.

محدودیت اصلی: `static`، `extern`، Header inclusion، Macro expansion و Linkage
کامل C خارج از Scope هستند.

