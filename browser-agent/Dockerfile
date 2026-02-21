# browser-agent – Dockerfile
#
# NOTE: This service is designed to run on the Linux HOST (not inside Docker)
# so Playwright can control a real display. This Dockerfile provides a
# reproducible development / CI environment only.
#
# For host execution, follow the README instead.

FROM python:3.12-slim

# System dependencies for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Playwright system deps (https://playwright.dev/python/docs/intro)
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    libx11-6 \
    libxext6 \
    # For virtual display in headless CI
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright's bundled Chromium
RUN playwright install chromium

COPY . .

# The Chromium profile is mounted as a volume so it persists between runs
VOLUME ["/app/chromium-profile"]

EXPOSE 8001

# Use BROWSER_HEADLESS=true when running inside Docker (no display available)
ENV BROWSER_HEADLESS=true
ENV BROWSER_HOST=0.0.0.0
ENV BROWSER_PORT=8001

CMD ["python", "main.py"]
