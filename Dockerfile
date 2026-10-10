FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 halva
COPY --chown=halva:halva app ./app
COPY --chown=halva:halva alembic ./alembic
COPY --chown=halva:halva alembic.ini seed_legal_documents.py seed_site_contacts.py fill_display_names.py fill_vk_urls.py migrate_from_django.py ./
USER halva
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
