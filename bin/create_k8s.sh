#!/bin/sh

CLUSTER_EXISTS=true

gcloud config set project $PROJECT_ID
gcloud config set compute/zone $COMPUTE_ZONE

gcloud container clusters describe $CLUSTER_NAME || CLUSTER_EXISTS=false

if [ $CLUSTER_EXISTS = false ]; then
    gcloud container clusters create $CLUSTER_NAME \
	--enable-autoupgrade \
	--scopes cloud-platform \
	--machine-type n1-standard-2 \
	--zone=$COMPUTE_ZONE \
	--disk-size=10GB

    gcloud components install kubectl

    gcloud container clusters get-credentials pysearchml --zone=$COMPUTE_ZONE

    # Main reference for deploying ES on k8: https://www.digitalocean.com/community/tutorials/how-to-set-up-an-elasticsearch-fluentd-and-kibana-efk-logging-stack-on-kubernetes#step-3-%E2%80%94-creating-the-kibana-deployment-and-service
    kubectl apply -f kubernetes/es/deploy_elasticsearch.yaml

    # Main reference for installing Kubeflow: https://www.kubeflow.org/docs/pipelines/installation/standalone-deployment/
    export PIPELINE_VERSION=0.2.2
    kubectl apply -k github.com/kubeflow/pipelines/manifests/kustomize/base/crds?ref=$PIPELINE_VERSION
    kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io
    kubectl apply -k github.com/kubeflow/pipelines//manifests/kustomize/env/dev?ref=$PIPELINE_VERSION
fi
