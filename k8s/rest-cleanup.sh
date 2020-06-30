#!/bin/bash
kubectl delete -f initDeployments/init-rest-statefulSet.yaml
kubectl delete -f replicaDeployments/mysql/mysql-replica-rest-statefulSet.yaml
for pvc in $(kubectl get pvc | grep pyql-rest | awk '{print $1}'); do 
    kubectl delete pvc $pvc
done
for pv in $(kubectl get pv | grep pyql-rest | awk '{print $1}'); do 
    kubectl delete pv $pv
done