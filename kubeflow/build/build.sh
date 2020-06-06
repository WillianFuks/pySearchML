#!/bin/bash
set -e

SUBSTITUTIONS=\
_COMPUTE_ZONE='us-central1-a',\
_CLUSTER_NAME='pysearchml',\
_RANKER='lambdamart',\
_VERSION='0.0.0'

gcloud builds submit --no-source --config kubeflow/build/cloudbuild.yaml --substitutions $SUBSTITUTIONS
