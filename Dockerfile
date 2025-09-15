FROM python:3.12-slim

WORKDIR /app/sneaker_check_price_bot
# ENV PYTHONPATH=/app/sneaker_check_price_bot/

RUN pip install --upgrade pip

COPY . /app/sneaker_check_price_bot/

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction

RUN python -m pip freeze

