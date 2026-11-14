# The SkillBoost API in a container, served by gunicorn (a production web server).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

# Install dependencies first, so code changes don't reinstall everything.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY migrations ./migrations

# Never run the app as root inside the container.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Bring the database up to date, then serve. One worker keeps the in-memory
# login rate limit accurate; threads handle requests in parallel.
CMD ["sh", "-c", "flask --app app db upgrade && exec gunicorn --bind 0.0.0.0:8000 --workers 1 --threads 4 'app:create_app()'"]
