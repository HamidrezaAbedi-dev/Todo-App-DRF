FROM python:3.13

LABEL maintainer="hamidrezaabedi.dev@gmail.com"

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY ./requirements.txt .

RUN pip install --upgrade pip & pip install -r requirements.txt

COPY ./core .