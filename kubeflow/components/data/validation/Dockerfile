FROM python:3.7.7-slim as python

COPY kubeflow/components/data/validation/ /validation
WORKDIR /validation
COPY ./key.json .

ENV GOOGLE_APPLICATION_CREDENTIALS=./key.json

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "run.py"]
