ARG APP_IMAGE=python:3.9.6

FROM $APP_IMAGE AS base

FROM base as builder

RUN mkdir /install
WORKDIR /project

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

ADD . /project

# Using IAM ECS role now
# COPY credentials /root/.aws/credentials
# COPY config /root/.aws/config

ENV FLASK_APP djmv2.py
# ENTRYPOINT ["bash"]
ENTRYPOINT ["python", "djmv2.py"]

# ENTRYPOINT ["python", "-m", "flask", "run", "--host=0.0.0.0"]

# FROM base
# ENV FLASK_APP djmv2.py
# WORKDIR /project
# COPY --from=builder /install /usr/local
# ADD . /project

# ENTRYPOINT ["bash"]
# ENTRYPOINT ["python", "-m", "flask", "run", "--host=0.0.0.0"]