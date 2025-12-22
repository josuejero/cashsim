

FROM python:3.12-slim AS builder

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1


RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential \
  && rm -rf /var/lib/apt/lists/*


RUN python -m pip install --upgrade pip build


COPY pyproject.toml README.md ./
COPY src ./src


RUN python -m build --wheel --outdir /wheels


FROM python:3.12-slim AS runtime


ARG APP_USER=app
ARG APP_UID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1


RUN useradd -m -u ${APP_UID} ${APP_USER}

WORKDIR /app


COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --upgrade pip \
  && python -m pip install --no-cache-dir /wheels/*.whl \
  && rm -rf /wheels

USER ${APP_USER}


EXPOSE 8000 8501


ENTRYPOINT ["cashsim"]
CMD ["--help"]
