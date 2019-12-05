# Usage

## Create enviroment for the first time
```console
$ kubectl create namespace schoen
$ kubectl create secret generic gitlab-credentials --namespace schoen --from-file=.dockerconfigjson=$HOME/.docker/config.json --type=kubernetes.io/dockerconfigjson
$ kubectl apply -f pvc.yaml
```

## Start deployment and telepresence
```console
$ ./run
```

## Tear down deployment after finished development
```console
$ kubectl delete -f deployment.yaml
```

### Tear down cluster development data
```console
$ kubectl delete -f pvc.yaml
```
