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

##########################################
## New Docker deployment process

### connect to SSH in dev container (dev)
```console
$ ssh -i <absolute path of ssh key file> root@dev.energie360.de -L localhost:5434:localhost:5432
```

```console
$ ssh -i C:/Users/v.riemer/.ssh/id_rsa_vladi_prointra root@dev.energie360.de -L localhost:5434:localhost:5432
```

### connect to SSH in web3 container (master/live)
```console
$ ssh -i <absolute path of ssh key file> root@web3.energie360.de -L localhost:5434:localhost:5432
```

```console
$ ssh -i C:/Users/v.riemer/.ssh/id_rsa_vladi_prointra root@web3.energie360.de -L localhost:5434:localhost:5432
```