FROM python:3.7.7-alpine3.12

ADD ./test.py /

ENTRYPOINT ["python", "test.py"]
