FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    # psycopg2 build deps
    libpq-dev \
    gcc \
    # pdftk wrapper
    pdftk \
    # Pillow
    libjpeg-dev \
    zlib1g-dev \
    # gettext for compilemessages
    gettext \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements/base.txt requirements/base.txt
COPY requirements/local.txt requirements/local.txt
RUN pip install -r requirements/local.txt

COPY . .

WORKDIR /app/sportfac

ENV PYTHONPATH=/app/sportfac/sportfac
ENV DJANGO_SETTINGS_MODULE=sportfac.settings.docker

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
