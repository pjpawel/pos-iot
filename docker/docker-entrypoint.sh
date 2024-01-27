#!/bin/sh

HOSTNAME=$(hostname)
echo "$HOSTNAME"

STORAGE_PATH="/mnt/storage/$HOSTNAME"

mkdir -p "$STORAGE_PATH/storage"
mkdir -p "$STORAGE_PATH/dump"
mkdir -p "$STORAGE_PATH/log"

ln -s "$STORAGE_PATH" /storage
ln -s /storage/log log

#Load all files
python load_files.py

# Starting background jobs and gunicorn server
gunicorn -w 2 -b 0.0.0.0:5000 'wsgi:main()' &

python3 start_dump_worker.py &
python3 start_scenario_job.py &
python3 start_transaction_verifier_job.py &

touch log/app.log

tail -f log/app.log