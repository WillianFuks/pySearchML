FROM python:3.7.7-slim as python

COPY kubeflow/components/model /model
COPY kubeflow/components/common/launch_crd.py /model/launch_crd.py
WORKDIR /model
COPY ./key.json .

ARG PROJECT_ID

ENV GOOGLE_APPLICATION_CREDENTIALS=key.json \
    PROJECT_ID=$PROJECT_ID
    #PYTHONUNBUFFERED=0

RUN pip install -r requirements.txt

ENTRYPOINT ["sh", "-c"]
