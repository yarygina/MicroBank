#!/bin/bash

MISSFIRE_FILE="MiSSFire.py"
GUNICORN_CONFIG_FILE="gunicorn_config.py"

echo "Applying security configurations."
#export MTLS="True"
if [[ "$MTLS" == "True" ]]; then
	if [[ -f $MISSFIRE_FILE ]]; then
		python $MISSFIRE_FILE
	else
		echo $MISSFIRE_FILE not found. Terminating.
		echo Reset MTLS environment variable to proceed without $MISSFIRE_FILE
		exit
	fi
fi

echo "Starting Gunicorn."
if [[ -f $GUNICORN_CONFIG_FILE ]]; then
	gunicorn -c $GUNICORN_CONFIG_FILE api:app
else
	echo $GUNICORN_CONFIG_FILE not found. Terminating.
	exit
fi

echo "Done!"
