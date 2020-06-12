#!/bin/sh

HOST=$(kubectl describe configmap inverse-proxy-config -n kubeflow | grep googleusercontent.com)

# Means Proxy is still being created
if [ -z "$HOST" ]; then
    echo 'Sleeping 2 mins so Kubeflow Inverse Proxy is ready'
    sleep 2m
    HOST=$(kubectl describe configmap inverse-proxy-config -n kubeflow | grep googleusercontent.com)
fi

echo "$HOST" > k8_host.txt
