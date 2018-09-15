FROM python:3-alpine

LABEL maintainer drober@gmail.com
ENV TELEGRAM_TOKEN ""

VOLUME /app/config
VOLUME /app/logs


RUN apk add python3=3.6.6-r0 py3-libvirt=4.4.0-r0 py3-yaml=3.12-r1 && mkdir -p /app

WORKDIR /app
USER root

#RUN pip3.6 install py
COPY *.py /app
ADD sanitexbackup /app/sanitexbackup

ENTRYPOINT /usr/local/bin/python3.6 /app/entrypoint.py
