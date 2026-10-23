
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install PostgreSQL client dependencies.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root application user.
RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup \
       --create-home --shell /usr/sbin/nologin appuser

# Copy application code with non-root ownership.
COPY --chown=appuser:appgroup . .

# Run application processes without root privileges.
USER appuser

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
