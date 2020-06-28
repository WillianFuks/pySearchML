FROM python:3.7.7-slim as python

COPY kubeflow/components/data/train/ /train
WORKDIR /train
COPY ./key.json .

ENV GOOGLE_APPLICATION_CREDENTIALS=./key.json

RUN pip install -r requirements.txt

CMD ["python", "run.py"]
