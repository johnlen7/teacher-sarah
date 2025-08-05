FROM python:3.10-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Instalar Whisper
RUN pip install --no-cache-dir \
    openai-whisper \
    flask \
    flask-cors

# Copiar aplicação
COPY app.py .

# Expor porta
EXPOSE 5001

# Comando
CMD ["python", "app.py"]
