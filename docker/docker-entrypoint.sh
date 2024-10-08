#!/bin/sh

HOSTNAME=$(hostname)

STORAGE_PATH="/mnt/storage/$HOSTNAME"

mkdir -p "$STORAGE_PATH/storage"
mkdir -p "$STORAGE_PATH/dump"
mkdir -p "$STORAGE_PATH/log"

ln -s "$STORAGE_PATH" /storage
ln -s /storage/log log

#echo "Loading files"
#python3 load_files.py
#sleep 3
# Starting background jobs and gunicorn server

echo "Starting server"
gunicorn \
 --worker-class gevent \
  -w 1 \
  -b 0.0.0.0:5000 \
  --timeout 600 \
  --access-logfile /storage/log/access.log \
  --log-file /storage/log/error.log \
  --log-level debug \
  'wsgi:main()' &

sleep 10

echo "Starting dump worker"
python3 start_dump_worker.py &
echo "Starting scenario worker"
python3 start_scenario_job.py &
echo "Starting transaction verifier worker"
python3 start_transaction_verifier_job.py &
echo "Starting worker set random validators"
python3 work_set_random_validators.py &
echo "Starting worker create block"
python3 work_create_block.py &
echo "Starting worker agreement"
python3 work_start_agreement.py &
echo "Starting worker validate agreement"
python3 work_validate_agreement.py &

touch log/app.log

tail -f log/app.log