#!/bin/sh

SERVICE=$(kubectl get service elasticsearch -n elastic-system | grep elasticsearch)

# Only deploy if service doesn't already exists.
if [ -z "$SERVICE" ]; then
    kubectl apply -f kubernetes/es/deploy_elasticsearch.yaml
fi
