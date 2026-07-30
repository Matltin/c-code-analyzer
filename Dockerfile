# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /workspace

FROM base AS builder

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --no-cache-dir .

FROM builder AS test

COPY . .
RUN python -m pip install --no-cache-dir -e ".[dev]"

ENTRYPOINT ["python", "-m", "pytest"]
CMD ["-q"]

FROM base AS runtime

RUN groupadd --gid 10001 analyzer \
    && useradd --uid 10001 --gid analyzer --create-home analyzer

COPY --from=builder /opt/venv /opt/venv
COPY examples ./examples

ENV PATH="/opt/venv/bin:${PATH}"

USER analyzer

ENTRYPOINT ["c-analyzer"]
CMD ["--help"]
