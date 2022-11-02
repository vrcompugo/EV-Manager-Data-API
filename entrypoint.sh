#!/bin/sh

cd /usr/src/app

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