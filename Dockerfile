FROM python:3.12-slim

WORKDIR /app

# System deps kept minimal; sqlite ships with Python.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ollama runs on the host / another container; point the bot at it.
ENV OLLAMA_HOST=http://host.docker.internal:11434
ENV LOG_JSON=1

CMD ["python", "-m", "bot.main"]
