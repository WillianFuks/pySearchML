#!/bin/sh

CLUSTER_EXISTS=true
CLUSTER_NAME=${CLUSTER_NAME:-"pysearchml"}
echo "cluster name: ${CLUSTER_NAME}"

gcloud config set project $PROJECT_ID 2>/dev/null
gcloud config set compute/zone $COMPUTE_ZONE 2>/dev/null

if [ -z $PROJECT_ID ] || [ -z $COMPUTE_ZONE ]; then
    echo Error: Please set properly env variables PROJECT_ID and COMPUTE_ZONE
    exit 1
fi

gcloud container clusters describe $CLUSTER_NAME 2>/dev/null || CLUSTER_EXISTS=false

if [ $CLUSTER_EXISTS = false ]; then
    gcloud container clusters create $CLUSTER_NAME \
	--enable-autoupgrade \
	--scopes cloud-platform \
	--machine-type n1-standard-2 \
	--zone=$COMPUTE_ZONE \
	--disk-size=20GB \
	--num-nodes=1

    gcloud components install kubectl
    gcloud container clusters get-credentials pysearchml --zone=$COMPUTE_ZONE

    # Main reference for deploying ES on k8: https://www.digitalocean.com/community/tutorials/how-to-set-up-an-elasticsearch-fluentd-and-kibana-efk-logging-stack-on-kubernetes#step-3-%E2%80%94-creating-the-kibana-deployment-and-service
    kubectl apply -f kubernetes/es/deploy_elasticsearch.yaml

    # Main reference for installing Kubeflow: https://www.kubeflow.org/docs/pipelines/installation/standalone-deployment/
#    export PIPELINE_VERSION=0.2.2
    #kubectl apply -k github.com/kubeflow/pipelines/manifests/kustomize/base/crds?ref=$PIPELINE_VERSION
    #kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io
    #kubectl apply -k github.com/kubeflow/pipelines/manifests/kustomize/env/dev?ref=$PIPELINE_VERSION
#    kubectl wait applications/pipeline -n kubeflow --for condition=Ready --timeout=1800s

export PIPELINE_VERSION=0.5.1
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref=$PIPELINE_VERSION"
kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/env/dev/?ref=$PIPELINE_VERSION"
#kubectl wait applications/pipeline -n kubeflow --for condition=Ready --timeout=1800s
fi
