#!/bin/sh

set -eu

#PROJECT_ID=$(gcloud config get-value project)
PROJECT_ID=$PROJECT_ID
NAME=pysearchml

if [ -e ./key.json ]; then
    echo File key.json already exists
else
    echo Creating service account and downloading key...

    SERVICE_ACCOUNT=$(gcloud iam service-accounts list --filter NAME=$NAME)
    if [ -z "$SERVICE_ACCOUNT" ]; then
	gcloud iam service-accounts create $NAME --project $PROJECT_ID \
	    --display-name $NAME
	for ROLE in roles/editor roles/storage.admin roles/bigquery.admin;
	do
	    gcloud projects add-iam-policy-binding $PROJECT_ID \
		    --member=serviceAccount:$NAME@$PROJECT_ID.iam.gserviceaccount.com \
		    --role=$ROLE
	done
	echo Created Service Account $NAME
    fi

    gcloud iam service-accounts keys create ./key.json \
	--iam-account $NAME@$PROJECT_ID.iam.gserviceaccount.com
    echo Finished downloading secrets key.json file
fi
