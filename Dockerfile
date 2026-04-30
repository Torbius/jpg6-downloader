# ── Stage 1: build deps ──────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# System deps needed for PySide6 headless (xcb libs for optional GUI via X11)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.lock .
RUN pip install --no-cache-dir --prefix=/install -r requirements.lock

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="Torbius" \
      project="jpg6-downloader" \
      description="Development snapshot image"

WORKDIR /app

# Runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy project source
COPY . .

# Downloads and config are mounted as volumes — don't bake into image
VOLUME ["/app/downloads", "/app/config"]

# Default: run backend in batch/headless mode (no display needed)
# For full Qt GUI: docker run -e DISPLAY=... --net=host ...
CMD ["python", "main.py", "--help"]
