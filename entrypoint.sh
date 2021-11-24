#!/bin/sh

cd /usr/src/app

echo "80.190.117.229 api.fakturia.de" >> /etc/hosts

echo $ENVIRONMENT
if [ $ENVIRONMENT = "dev" ]
then
  until runuser -u appuser -- $@; do
      echo "Debug crashed. Respawning"
      sleep 5
  done
else
  runuser -u appuser -- $@
fi