#!/bin/bash
set -e

SUBSTITUTIONS=\
_COMPUTE_ZONE='us-central1-a',\
_CLUSTER_NAME='pysearchml',\
_VERSION='0.0.0'

./kubeflow/build/manage_service_account.sh

gcloud builds submit --no-source --config kubeflow/build/cloudbuild.yaml --substitutions $SUBSTITUTIONS --timeout=2h
