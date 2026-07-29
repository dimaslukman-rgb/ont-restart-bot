FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

# Install tini for proper signal handling
RUN apt-get update && apt-get install -y --no-install-recommends tini && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cache-friendly layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Drop privileges
RUN useradd --create-home --shell /bin/bash bot && chown -R bot:bot /app
USER bot

# Railway uses PORT env for web; for worker we just need the cmd
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-u", "bot.py"]
