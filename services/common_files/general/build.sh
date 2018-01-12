#!/bin/bash

MISSFIRE_FILE="MiSSFire.py"
MODSECURITY_WRAPPER_FILE="/opt/modsecurity_wrapper"
GAME_ENGINE_CLIENT_FILE="gameengineclient.py"
GUNICORN_CONFIG_FILE="gunicorn_config.py"


#export MTLS="True"
if [[ "$MTLS" == "True" ]]; then
	if [[ -f $MISSFIRE_FILE ]]; then
		echo Applying security configurations.
		python $MISSFIRE_FILE
	else
		echo $MISSFIRE_FILE not found. Terminating.
		echo Reset 'MTLS' environment variable to proceed without $MISSFIRE_FILE
		exit
	fi
fi


if [[ "$ISGAME" == "True" ]]; then
	if [[ -f $MODSECURITY_WRAPPER_FILE ]]; then
		echo Starting the ModSecurity wrapper.
		$MODSECURITY_WRAPPER_FILE &
	else
		echo $MODSECURITY_WRAPPER_FILE not found. Terminating.
		echo Reset 'ISGAME' environment variable to proceed without $MODSECURITY_WRAPPER_FILE
		exit
	fi
	if [[ -f $GAME_ENGINE_CLIENT_FILE ]]; then
		echo Starting the game engine client.
		$GAME_ENGINE_CLIENT_FILE &
	else
		echo $GAME_ENGINE_CLIENT_FILE not found. Terminating.
		echo Reset 'ISGAME' environment variable to proceed without $GAME_ENGINE_CLIENT_FILE
		exit
	fi
fi


if [[ -f $GUNICORN_CONFIG_FILE ]]; then
	echo Starting Gunicorn.
	gunicorn -c $GUNICORN_CONFIG_FILE api:app
else
	echo $GUNICORN_CONFIG_FILE not found. Terminating.
	exit
fi

echo Done!
