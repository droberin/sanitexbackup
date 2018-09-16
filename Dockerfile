FROM python:3-alpine

LABEL maintainer drober@gmail.com
ENV TELEGRAM_TOKEN ""

VOLUME /app/config
VOLUME /app/logs

COPY alpine-repositories /etc/apk/repositories

RUN apk add gcc linux-headers python3-dev musl-dev libffi-dev openssl-dev make
RUN apk add python3=3.6.6-r0 py3-paramiko=2.4.1-r0 py3-libvirt=4.4.0-r0 py3-yaml=3.12-r1
RUN pip3.6 install scp && \
  pip3.6 install python-telegram-bot && \
    pip3.6 install pyotp

RUN apk add openssh-client

RUN mkdir -p /app/config && rm -fr /var/cache/apk/*

WORKDIR /app
USER root

#RUN pip3.6 install py
COPY *.py LICENSE /app/
COPY config /app/config/
ADD sanitexbackup /app/sanitexbackup

CMD python3.6 /app/entrypoint.py
