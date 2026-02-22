FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias primero (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# arq espera la clase WorkerSettings en el módulo scheduler
CMD ["python", "-m", "arq", "scheduler.WorkerSettings"]
