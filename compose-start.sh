#!/bin/bash

TIME=$(date +%s)
mkdir -p ../storage-archive/"$TIME"
mv ../storage/* ../storage-archive/"$TIME"

docker compose up --build
