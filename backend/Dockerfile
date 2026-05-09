# Build stage — install dependencies (needs gcc for some C extensions)
FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime stage
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
COPY templates/ /app/templates/
RUN chmod +x entrypoint.sh
ENV PYTHONPATH=/app
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
