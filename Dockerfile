ARG APP_IMAGE=python:3.9.6

FROM $APP_IMAGE AS base

FROM base as builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*
RUN ln -fs /usr/share/zoneinfo/Australia/Sydney /etc/localtime \
    && dpkg-reconfigure --frontend noninteractive tzdata

RUN mkdir /install
WORKDIR /project

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

ADD . /project

# Using IAM ECS role now
#COPY credentials /root/.aws/credentials
#COPY config /root/.aws/config

ENV FLASK_APP djmv2.py
# ENTRYPOINT ["bash"]
