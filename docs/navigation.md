# Navigation چندفایلی

سه API اصلی عبارت‌اند از:

- `goto_definition(project, file, line, column)`
- `find_references(project, file, line, column)`
- `hover_project(project, file, line, column)`

انتخاب Symbol با Position و Binding مدل Semantic انجام می‌شود، نه جست‌وجوی
متن. Variable، Parameter، Function، Struct و Field پشتیبانی می‌شوند.
Go-to-Definition برای Function، Definition را بر Prototype ترجیح می‌دهد؛ اگر
Definition نباشد Declarationها را برمی‌گرداند. Built-in صریحاً Built-in است.

Find References می‌تواند از Declaration یا Usage آغاز شود. Declaration،
Definition و AccessKindهای `READ`، `WRITE`، `READ_WRITE`، `CALL`،
`TYPE_REFERENCE` و `MEMBER_ACCESS` قابل‌تفکیک و بر اساس File/Offset مرتب‌اند.

Hover علاوه بر نوع و Scope، Signature، Definition، Declarationهای مرتبط و
Documentation Comment بلافاصله پیشین را نمایش می‌دهد.

