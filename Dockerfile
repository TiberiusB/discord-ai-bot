FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV OLLAMA_HOST=http://host.docker.internal:11434
ENV LOG_JSON=1

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=3 \
  CMD ["python", "scripts/healthcheck.py"]

CMD ["python", "-m", "bot.main"]
