FROM python:3.12-slim
WORKDIR /srv/backend
COPY backend/requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY backend .
# Specs are included by COPY backend .
RUN useradd --create-home app && chown -R app:app /srv
USER app
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
