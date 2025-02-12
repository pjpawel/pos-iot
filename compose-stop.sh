#!/bin/bash

#docker stop -s 15 -t 10 node_normal node_validator node_genesis
#docker rm node_normal node_validator node_genesis

docker stop -s 15 -t 10 $(docker ps -a -q)
docker rm $(docker ps -a -q)


