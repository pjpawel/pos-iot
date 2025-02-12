#!/bin/bash

# Run one simulation

source env/bin/activate

DATE=$(date +"%y_%m_%d_%s")
SIMULATIONS_DIR=../monitor/simulation_"$DATE"

mkdir -p "$SIMULATIONS_DIR"

############################################
# Run simulation 1
printf "\n"
echo "************************************"
echo "Running simulation 1"
echo "************************************"
printf "\n"

./compose-start.sh
sleep 500
./compose-stop.sh

printf "\n"
echo "************************************"
echo "Simulation 1 stopped"
echo "************************************"
printf "\n"

python3 monitor.py

SIMULATION_DIR=$SIMULATIONS_DIR/simulation_1
mkdir -p "$SIMULATION_DIR"
mkdir -p "$SIMULATION_DIR"/storage
mkdir -p "$SIMULATION_DIR"/result

cp -r ../storage/* "$SIMULATION_DIR"/storage
mv ../monitor/result/* "$SIMULATION_DIR"/result

printf "\n"
echo "************************************"
echo "Simulation 1 finished"
echo "************************************"
printf "\n"