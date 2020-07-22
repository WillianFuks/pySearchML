FROM google/cloud-sdk:alpine as gcloud
FROM python:3.7.7-alpine3.12 as python

COPY ./key.json /key.json

ENV GOOGLE_APPLICATION_CREDENTIALS=/key.json
ENV PATH=/google-cloud-sdk/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

RUN pip install kfp --upgrade
RUN pip install fire

COPY --from=gcloud /google-cloud-sdk /google-cloud-sdk

ENTRYPOINT ["sh"]
