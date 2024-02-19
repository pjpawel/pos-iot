#!/bin/bash

TIME=$(date +%s)
mkdir -p ../storage-archive/"$TIME"
mv ../storage/* ../storage-archive/"$TIME"

NODE_NUMBER=$((3 + 11))

# docker compose up --build

docker build -t pot-iot .

docker run -d \
  --name node_genesis \
  -p "5010:5000" \
  --mount type=bind,source=/home/pp/programs/magisterka/storage,dst=/mnt/storage \
  --env SECRET_KEY=07f83cd2a279a2edc6b7ae1ced2ced8b77610efb2d2194813d7b446155d0b567 \
  --env NODE_TYPE=VALIDATOR \
  --env START_ROLE=genesis \
  --env GENESIS_NODE=node_genesis \
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
      --network pos-iot_blockchain \
      pot-iot
done

#
#docker run -d \
#  --name node_validator \
#  -p "5011:5000" \
#  --mount type=bind,source=/home/pp/programs/magisterka/storage,dst=/mnt/storage \
#  --env SECRET_KEY=07f83cd2a279a2edc6b7ae1ced2ced8b77610efb2d2194813d7b446155d0b567 \
#  --env NODE_TYPE=VALIDATOR \
#  --env GENESIS_NODE=node_genesis \
#  --network pos-iot_blockchain \
#  pot-iot

#sleep 10
#
#docker run -d \
#  --name node_normal \
#  -p "5012:5000" \
#  --mount type=bind,source=/home/pp/programs/magisterka/storage,dst=/mnt/storage \
#  --env SECRET_KEY=07f83cd2a279a2edc6b7ae1ced2ced8b77610efb2d2194813d7b446155d0b567 \
#  --env NODE_TYPE=VALIDATOR \
#  --env GENESIS_NODE=node_genesis \
#  --network pos-iot_blockchain \
#  pot-iot

