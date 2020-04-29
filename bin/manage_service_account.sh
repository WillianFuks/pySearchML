#!/bin/sh

set -eu

PROJECT_ID=$(gcloud config get-value project)

if [ -e ./key.json ]; then
    echo File key.json already exists
else
    echo Creating service account and downloading key...

    SERVICE_ACCOUNT=$(gcloud iam service-accounts list --filter NAME=pysearchml)
    if [ -z "$SERVICE_ACCOUNT" ]; then
	gcloud iam service-accounts create pysearchml --project $PROJECT_ID \
	    --display-name pysearchml
	for ROLE in roles/editor;
	do
	    gcloud projects add-iam-policy-binding $PROJECT_ID \
		    --member=serviceAccount:pysearchml@$PROJECT_ID.iam.gserviceaccount.com \
		    --role=$ROLE
	done
	echo Created Service Account pysearchml
    fi

    gcloud iam service-accounts keys create key.json \
	--iam-account pysearchml@$PROJECT_ID.iam.gserviceaccount.com
    echo Finished downloading secrets key.json file
fi
