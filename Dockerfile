# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS builder

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

# Build tooling for wheels (safe default for scientific deps)
RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential \
  && rm -rf /var/lib/apt/lists/*

# Install build backend
RUN python -m pip install --upgrade pip build

# Copy only build inputs first (better layer cache)
COPY pyproject.toml README.md ./
COPY src ./src

# Build a wheel
RUN python -m build --wheel --outdir /wheels


FROM python:3.12-slim AS runtime

# Use uid 1000 to play nicely with Hugging Face Docker Spaces
ARG APP_USER=app
ARG APP_UID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create non-root user
RUN useradd -m -u ${APP_UID} ${APP_USER}

WORKDIR /app

# Install the built wheel
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --upgrade pip \
  && python -m pip install --no-cache-dir /wheels/*.whl \
  && rm -rf /wheels

USER ${APP_USER}

# Expose default ports (API + UI)
EXPOSE 8000 8501

# Default shows help; compose overrides commands.
ENTRYPOINT ["cashsim"]
CMD ["--help"]
