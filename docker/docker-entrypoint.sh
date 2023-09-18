#!/bin/sh

# Script starting background jobs and flask app

rm -rf /storage/*

python3 start_scenario_job.py &
python3 start_transaction_verifier_job.py &

#python3 -m flask --app pos/start_node_flask run --host=0.0.0.0 &
gunicorn -w 1 -b 0.0.0.0:5000 'wsgi:main()'

touch log/app.log

tail -f log/app.log