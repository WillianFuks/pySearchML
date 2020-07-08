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
	--disk-size=30GB \
	--num-nodes=2

    gcloud components install kubectl
    gcloud container clusters get-credentials $CLUSTER_NAME --zone=$COMPUTE_ZONE

    # Install Kubeflow Pipelines
    export PIPELINE_VERSION=0.5.1
    kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref=$PIPELINE_VERSION"
    kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io
    kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic/?ref=$PIPELINE_VERSION"
    # Update namespace to contain metric collector label
    kubectl apply -f kubeflow/namespace.yaml
    kubectl apply -f kubeflow/pvc.yaml

    # Install Kustomize
    curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh"  | bash

    # Install Kabit
    git clone git@github.com:kubeflow/manifests.git
    ./kustomize build manifests/katib/katib-crds/base | kubectl apply -f -
    ./kustomize build manifests/katib/katib-controller/base | kubectl apply -f -

    # https://www.digitalocean.com/community/tutorials/how-to-set-up-an-elasticsearch-fluentd-and-kibana-efk-logging-stack-on-kubernetes#step-3-%E2%80%94-creating-the-kibana-deployment-and-service
    kubectl apply -f kubernetes/es/deploy_elasticsearch.yaml
fi
