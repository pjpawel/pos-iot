#!/bin/bash

SIMULATION="${1:-1}"
BUILD=${2:-1}
NODE_NUMBER=${3:-6}

TIME=$(date +%s)
#mkdir -p ../storage-archive/"$TIME"
#mv ../storage/* ../storage-archive/"$TIME"
rm -rf ../storage/*

NODE_NUMBER=$((NODE_NUMBER + 11))

if [ "$BUILD" -eq 1 ]; then
    # docker compose up --build
    docker buildx build --no-cache -t pot-iot .
fi

docker run -d \
  --name node_genesis \
  -p "5010:5000" \
  --mount type=bind,source=/home/pp/programs/magisterka/storage,dst=/mnt/storage \
  --env SECRET_KEY=07f83cd2a279a2edc6b7ae1ced2ced8b77610efb2d2194813d7b446155d0b567 \
  --env NODE_TYPE=VALIDATOR \
  --env START_ROLE=genesis \
  --env GENESIS_NODE=node_genesis \
  --env SIMULATION=$SIMULATION \
  --network pos-iot_blockchain \
  pot-iot

sleep 5

for ((i = 11 ; i < NODE_NUMBER ; i++)); do
    sleep 5
    echo "Launching $i"
    docker run -d \
    --name "node_normal_$i" \
    -p "50$i:5000" \
    --mount type=bind,source=/home/pp/programs/magisterka/storage,dst=/mnt/storage \
    --env "SECRET_KEY=07f83cd2a279a2edc6b7ae1ced2ced8b77610efb2d2194813d7b446155d0b5$i" \
    --env NODE_TYPE=SENSOR \
    --env GENESIS_NODE=node_genesis \
    --env SIMULATION=$SIMULATION \
    --network pos-iot_blockchain \
    pot-iot
done

