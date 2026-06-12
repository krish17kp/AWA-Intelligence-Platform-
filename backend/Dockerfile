FROM mcr.microsoft.com/playwright/python:v1.60.0-noble

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
