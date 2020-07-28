FROM python:3.6-jessie
WORKDIR /front
ADD kubernetes/front/ /front
RUN pip install -r /front/requirements.txt
ADD kubeflow/components/model/queries/lambdamart0/es_query.json /front/es_query.json
ENV PORT 8088
CMD ["gunicorn", "app:app", "--config=config.py"]
