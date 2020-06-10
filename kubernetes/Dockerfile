FROM python:3.7.7

COPY . /pySearchML
WORKDIR /pySearchML
ENV GOOGLE_APPLICATION_CREDENTIALS=./key.json
RUN pip install -r requirements.txt
