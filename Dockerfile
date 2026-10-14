FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN useradd --create-home --uid 1000 moxart \
    && mkdir -p /app/instance /app/uploads \
    && chown moxart:moxart /app/instance /app/uploads

COPY --chown=moxart:moxart . .

USER moxart

EXPOSE 5000

ENTRYPOINT ["docker/entrypoint.sh"]
# one worker keeps the in-memory rate limits accurate; threads handle concurrency
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "--access-logfile", "-", "moxart:create_app()"]
