FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Aplica migraciones antes de levantar el server -- así un `docker compose up`
# limpio deja la BD lista sin pasos manuales (además de las migraciones, el
# admin seed sigue siendo manual, ver ../base-datos/README.md).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
