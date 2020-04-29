#!/bin/sh

set -eu

CLUSTER_NAME=pysearchml
ZONE=us-central1-a

gcloud config set project $PROJECT_ID
gcloud config set compute/zone $ZONE

gcloud beta container clusters create $CLUSTER_NAME \
    --enable-autoupgrade \
    --scopes cloud-platform \
    --machine-type n1-standard-2 \
    --zone=$ZONE

gcloud components install kubectl

gcloud container clusters get-credentials pysearchml --zone=$ZONE

# Main reference for deploying ES on k8: https://www.digitalocean.com/community/tutorials/how-to-set-up-an-elasticsearch-fluentd-and-kibana-efk-logging-stack-on-kubernetes#step-3-%E2%80%94-creating-the-kibana-deployment-and-service
kubectl apply -f kubernetes/es/deploy_elasticsearch.yaml

# Main reference for installing Kubeflow: https://www.kubeflow.org/docs/pipelines/installation/standalone-deployment/
export PIPELINE_VERSION=0.2.2
kubectl apply -k github.com/kubeflow/pipelines/manifests/kustomize/base/crds?ref=$PIPELINE_VERSION
kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io
kubectl apply -k github.com/kubeflow/pipelines//manifests/kustomize/env/dev?ref=$PIPELINE_VERSION
