FROM python:3.7.7

COPY . /pySearchML
WORKDIR /pySearchML
ENV GOOGLE_APPLICATION_CREDENTIALS=./key.json

RUN apt-get update && apt-get install curl -y &&\
    curl https://dl.google.com/dl/cloudsdk/release/google-cloud-sdk.tar.gz > /tmp/google-cloud-sdk.tar.gz && \
    mkdir -p /usr/local/gcloud && \
    tar -C /usr/local/gcloud -xf /tmp/google-cloud-sdk.tar.gz && \
    /usr/local/gcloud/google-cloud-sdk/install.sh && \
    ln -s /usr/local/gcloud/google-cloud-sdk/bin/* /usr/bin

RUN pip install -r requirements.txt
RUN pip install kfp --upgrade
