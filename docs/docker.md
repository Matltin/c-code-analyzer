# اجرای پروژه با Docker

## وضعیت تأیید

فایل‌های Docker برای B2 آماده‌اند، اما در محیط تولید این Archive فرمان
`docker` نصب نبود. بنابراین Build، Smoke Test و Test Stage هنوز با وضعیت
`[?]` نیازمند اجرای واقعی روی Ubuntu کاربر هستند.

## طراحی Image

`Dockerfile` سه Stage دارد:

- `builder`: Package را داخل `/opt/venv` نصب می‌کند.
- `test`: فقط برای نصب Development Dependency و اجرای pytest است.
- `runtime`: Image نهایی کوچک، بدون pytest و با User غیرـRoot است.

Runtime از Image رسمی `python:3.12-slim` استفاده می‌کند، Working Directory آن
`/workspace` و Entry Point آن `c-analyzer` است. پس از Build، اجرای Container
به Network نیاز ندارد.

## Build و Smoke Test

```bash
make docker-build
make docker-smoke
```

معادل مستقیم:

```bash
docker build --target runtime -t c-code-analyzer:bonus .
docker run --rm c-code-analyzer:bonus --help
docker run --rm c-code-analyzer:bonus --version
docker run --rm c-code-analyzer:bonus project-check examples/project
```

Exampleها داخل Runtime Image قرار دارند تا Demo بدون Mount هم قابل اجرا باشد.

## تحلیل Project خارجی با Mount فقط‌خواندنی

```bash
docker run --rm \
  -v "$PWD/examples/project:/workspace/project:ro" \
  c-code-analyzer:bonus \
  project-check /workspace/project
```

برای تحلیل معمولی Mount باید `:ro` باشد. فقط برای Rename همراه `--apply` یک
Copy آزمایشی و Mount قابل‌نوشتن استفاده کن؛ Source اصلی Repository را Mount
قابل‌نوشتن نکن.

## اجرای Test Stage

```bash
make docker-test
```

معادل مستقیم:

```bash
docker build --target test -t c-code-analyzer:test .
docker run --rm c-code-analyzer:test
```

Test dependencyها وارد Runtime Image نمی‌شوند.

## موارد واردنشده به Build Context

`.dockerignore` محیط مجازی، Git، Cacheها، Coverage، Site، Output، IDE، ZIP و
فایل‌های موقت Rename را حذف می‌کند. هیچ Secret یا Credential در Dockerfile
وجود ندارد و این پروژه به `docker-compose.yml` نیاز ندارد.

## پاک‌کردن یا Rollback زیرساخت Docker

Docker به Production Code وابستگی معکوس ایجاد نمی‌کند. برای بازگرداندن B2،
فقط `Dockerfile`، `.dockerignore` و `docs/docker.md` و Targetهای Docker در
`Makefile` را از Commit مربوط به B2 حذف کن. Source تحلیل‌گر تغییر نمی‌کند.
