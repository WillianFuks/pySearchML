FROM python:3.7.7-alpine3.12 as python

COPY kubeflow/components/prepare_env /prepare_env
WORKDIR /prepare_env
COPY ./key.json .

ENV GOOGLE_APPLICATION_CREDENTIALS=./key.json

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "run.py"]
