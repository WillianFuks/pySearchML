#!/bin/bash

#set -e

#PROJECT_ID=$(gcloud config get-value project)
PROJECT_ID=$PROJECT_ID
NAME=pysearchml
SECRET_NAME=pysearchml-service-account

if ! [ -z "$(gcloud secrets list | grep $SECRET_NAME)" ]; then
    gcloud secrets versions access latest --secret=$SECRET_NAME > key.json
    echo Downloaded Secret
fi

if [ -e key.json ]; then
    echo File key.json already available.
else
    echo Creating service account and downloading key...

    SERVICE_ACCOUNT=$(gcloud iam service-accounts list --filter NAME=$NAME)
    if [ -z "$SERVICE_ACCOUNT" ]; then
	gcloud iam service-accounts create $NAME --project $PROJECT_ID \
	    --display-name $NAME

	for ROLE in roles/editor roles/storage.admin roles/bigquery.admin roles/storage.objectAdmin;
	do
	    gcloud projects add-iam-policy-binding $PROJECT_ID \
	        --member=serviceAccount:$NAME@$PROJECT_ID.iam.gserviceaccount.com \
	        --role=$ROLE
	done
	echo Created Service Account $NAME
    fi

    gcloud iam service-accounts keys create ./key.json --iam-account $NAME@$PROJECT_ID.iam.gserviceaccount.com

    echo Creating Secret File
    gcloud secrets create $SECRET_NAME --data-file=key.json --replication-policy=automatic
    echo New Secret File Created

    echo Finished downloading secrets key.json file
fi
