FROM python:3.13-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY core/requirements.txt ./requirements.txt
RUN python -m pip install --prefix=/install -r requirements.txt

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y libpq5 \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /usr/src/app --no-create-home app \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY --from=builder /install/ /usr/local/
COPY --chown=app:app core/manage.py ./manage.py
COPY --chown=app:app core/core/ ./core/
COPY --chown=app:app core/apps/ ./apps/
COPY --chown=app:app core/templates/ ./templates/
COPY --chown=app:app core/staticfiles/ ./staticfiles/
COPY --chown=app:app dockerfiles/prod/entrypoint.sh ./entrypoint.sh

RUN mkdir -p static media \
    && chown -R app:app /usr/src/app

USER app
EXPOSE 8000
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
CMD ["gunicorn", "--bind=0.0.0.0:8000", "--workers=3", "--access-logfile=-", "--error-logfile=-", "core.wsgi:application"]
