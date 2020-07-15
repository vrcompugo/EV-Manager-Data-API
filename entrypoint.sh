#!/bin/sh

cd /usr/src/app

echo $ENVIRONMENT
if [ $ENVIRONMENT = "dev" ]
then
  until $@; do
      echo "Debug crashed. Respawning"
      sleep 5
  done
else
  $@
fi
